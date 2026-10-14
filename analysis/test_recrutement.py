"""
Tests du module de suivi du recrutement.

1. Transitions de statut : ce que le processus accepte et refuse.
2. Statuts, prochaines actions et alertes de délai.
3. Calculs sur les données fictives, recoupés avec SQL et le script de préparation.
4. Modèles générés : courriel de convocation, checklist d'intégration, planning, page.
5. Garde-fous : aucune décision automatisée, aucune caractéristique sensible.

Lancer depuis la racine du projet :
    python -m unittest discover -s analysis -v
"""
import sqlite3
import sys
import unittest
from datetime import date

import recrutement as rc
from commun import DATE_REFERENCE, DOSSIER_PROCESSED, DOSSIER_RAW, RACINE, en_date, lire_csv

sys.path.insert(0, str(RACINE / "recruitment"))
import generer_module_recrutement as gen  # noqa: E402

CAND = {"candidature_id": "T-1", "offre_id": "OFF-T", "prenom": "Test", "nom": "Candidat",
        "date_candidature": "2026-09-01", "autorisation_references": "Oui",
        "date_autorisation_references": "2026-09-20", "date_reponse_candidat": "",
        "date_prise_fonction_prevue": "2026-11-02"}


def evt(etape, jour, resultat="Validée", intervenant=rc.CRH, note=None):
    return {"evenement_id": f"E{etape}", "candidature_id": "T-1", "etape": etape, "date": jour,
            "resultat": resultat, "intervenant": intervenant, "note_grille_sur_20": note, "commentaire": ""}


PARCOURS_COMPLET = [
    evt(1, "2026-09-01"), evt(2, "2026-09-08", intervenant=rc.COMITE, note=15),
    evt(3, "2026-09-10"), evt(4, "2026-09-17", intervenant=rc.COMITE, note=14),
    evt(5, "2026-09-24"), evt(6, "2026-09-29", "Favorable", rc.RRH),
    evt(7, "2026-10-12", intervenant=rc.RRH), evt(8, "2026-11-02"),
]


def rejouer(evenements, candidature=CAND):
    historique = []
    for e in evenements:
        historique = rc.enregistrer_etape(historique, e, candidature)
    return historique


class Transitions(unittest.TestCase):
    def test_parcours_complet_accepte(self):
        historique = rejouer(PARCOURS_COMPLET)
        self.assertEqual(rc.statut_candidature(historique), rc.STATUT_INTEGRE)

    def test_statut_a_chaque_etape(self):
        attendus = {1: rc.STATUT_EN_COURS, 6: rc.STATUT_EN_COURS, 7: rc.STATUT_RECRUTE, 8: rc.STATUT_INTEGRE}
        for n, statut in attendus.items():
            self.assertEqual(rc.statut_candidature(rejouer(PARCOURS_COMPLET[:n])), statut, f"étape {n}")

    def refuse(self, evenements, motif, candidature=CAND):
        with self.assertRaises(rc.TransitionRefusee) as ctx:
            rejouer(evenements, candidature)
        self.assertIn(motif, str(ctx.exception))

    def test_doit_commencer_a_l_etape_1(self):
        self.refuse([evt(2, "2026-09-08", intervenant=rc.COMITE, note=12)], "commencer à l'étape 1")

    def test_saut_d_etape_refuse(self):
        self.refuse([evt(1, "2026-09-01"), evt(3, "2026-09-10")], "saut d'étape")

    def test_dossier_cloture_ne_peut_plus_evoluer(self):
        self.refuse([evt(1, "2026-09-01"), evt(2, "2026-09-08", "Non retenu(e)", rc.COMITE, 8),
                     evt(3, "2026-09-10")], "déjà clôturé")

    def test_intervenant_automatique_refuse(self):
        for automate in ("Système automatique", "IA", "Algorithme de tri"):
            self.refuse([evt(1, "2026-09-01", intervenant=automate)], "non autorisé")

    def test_decision_reservee_au_responsable_rh(self):
        self.refuse(PARCOURS_COMPLET[:5] + [evt(6, "2026-09-29", "Favorable", rc.COMITE)],
                    "appartient au responsable RH")

    def test_non_selection_par_une_personne_habilitee(self):
        self.refuse([evt(1, "2026-09-01"), evt(2, "2026-09-08", "Non retenu(e)", rc.CRH, 8)],
                    "comité de recrutement ou le responsable RH")

    def test_references_sans_autorisation_refusees(self):
        sans = {**CAND, "autorisation_references": "", "date_autorisation_references": ""}
        self.refuse(PARCOURS_COMPLET[:5], "sans autorisation", sans)
        tardive = {**CAND, "date_autorisation_references": "2026-09-25"}  # après le contact du 24/09
        self.refuse(PARCOURS_COMPLET[:5], "sans autorisation", tardive)

    def test_grille_obligatoire_aux_etapes_2_et_4(self):
        self.refuse([evt(1, "2026-09-01"), evt(2, "2026-09-08", intervenant=rc.COMITE)], "grille")
        self.refuse([evt(1, "2026-09-01"), evt(2, "2026-09-08", intervenant=rc.COMITE, note=14),
                     evt(3, "2026-09-10", note=12)], "note de grille inattendue")

    def test_resultat_impossible_et_date_anterieure(self):
        self.refuse([evt(1, "2026-09-01"), evt(2, "2026-09-08", "Favorable", rc.COMITE, 14)], "impossible")
        self.refuse([evt(1, "2026-09-01"), evt(2, "2026-08-30", intervenant=rc.COMITE, note=14)], "antérieure")

    def test_desistement_possible_en_cours_de_route(self):
        historique = rejouer(PARCOURS_COMPLET[:3] + [evt(4, "2026-09-15", "Désistement")])
        self.assertEqual(rc.statut_candidature(historique), rc.STATUT_DESISTEMENT)


class ProchainesActions(unittest.TestCase):
    MOTS_DE_DECISION = ("rejeter", "écarter", "retenir le", "sélectionner le", "recruter le", "classer")

    def test_une_action_administrative_par_etape_sans_decision(self):
        for n in range(1, 9):
            historique = rejouer(PARCOURS_COMPLET[:n])
            action, responsable, _ = rc.prochaine_action(CAND, historique, None)
            self.assertTrue(action)
            for mot in self.MOTS_DE_DECISION:
                self.assertNotIn(mot, action.lower(), f"étape {n} : {action}")

    def test_actions_attendues(self):
        sans_autorisation = {**CAND, "autorisation_references": ""}
        action, resp, _ = rc.prochaine_action(sans_autorisation, rejouer(PARCOURS_COMPLET[:4]), None)
        self.assertIn("autorisation écrite", action)
        action, resp, _ = rc.prochaine_action(CAND, rejouer(PARCOURS_COMPLET[:5]), None)
        self.assertEqual((resp, "responsable RH pour décision" in action), (rc.CRH, True))
        action, resp, echeance = rc.prochaine_action(CAND, rejouer(PARCOURS_COMPLET[:7]), None)
        self.assertEqual((resp, echeance), (rc.CRH, date(2026, 11, 2)))
        creneau = {"date": "2026-09-17", "heure_debut": "08:30"}
        action, resp, echeance = rc.prochaine_action(CAND, rejouer(PARCOURS_COMPLET[:3]), creneau)
        self.assertEqual((resp, echeance), (rc.COMITE, date(2026, 9, 17)))
        self.assertIn("17/09 à 08:30", action)

    def test_reponse_au_candidat_non_retenu(self):
        histo = rejouer([evt(1, "2026-09-01"), evt(2, "2026-09-08", "Non retenu(e)", rc.COMITE, 8)])
        cand = {**CAND, "date_prise_fonction_prevue": ""}
        action, resp, echeance = rc.prochaine_action(cand, histo, None)
        self.assertEqual((resp, echeance), (rc.CRH, date(2026, 9, 15)))   # décision + 7 jours
        action, resp, _ = rc.prochaine_action({**cand, "date_reponse_candidat": "2026-09-10"}, histo, None)
        self.assertEqual(resp, "")

    def test_alerte_de_relance(self):
        donnees = {"recrutement_etapes": [evt(1, "2026-10-01")], "planning_entretiens": []}
        self.assertEqual(rc.etat_candidature(donnees, CAND, date(2026, 10, 10))["alerte"], "")
        self.assertEqual(rc.etat_candidature(donnees, CAND, date(2026, 10, 20))["alerte"],
                         "Relancer : aucune action depuis 19 jours")


class CalculsSurLesDonneesFictives(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = rc.charger_donnees()
        cls.etats = {s["candidature_id"]: s for s in rc.tous_les_etats(cls.d, DATE_REFERENCE)}

    def test_donnees_conformes_au_processus(self):
        self.assertEqual(rc.verifier_donnees(self.d), [])

    def test_indicateurs(self):
        ind = rc.indicateurs(self.d, DATE_REFERENCE)
        # Délai moyen recalculé à la main depuis le journal : (29/09 - 20/08) et (29/09 - 25/08).
        attendu_delai = round(((date(2026, 9, 29) - date(2026, 8, 20)).days
                               + (date(2026, 9, 29) - date(2026, 8, 25)).days) / 2)
        self.assertEqual(ind, {"candidatures": 10, "en_cours": 3, "actions_a_mener": 5, "alertes": 1,
                               "tests_a_venir": 3, "postes_pourvus": 1,
                               "delai_moyen_decision_jours": attendu_delai})

    def test_statuts_au_31_octobre(self):
        self.assertEqual(self.etats["CAND-001"]["statut"], rc.STATUT_RECRUTE)
        self.assertEqual(self.etats["CAND-005"]["alerte"], "Échéance dépassée de 46 jours")
        self.assertEqual(self.etats["CAND-010"]["statut"], rc.STATUT_DESISTEMENT)
        self.assertEqual(self.etats["CAND-010"]["etape"], 3)   # désistement avant le test : étape 3 franchie
        self.assertEqual({k for k, s in self.etats.items() if s["statut"] == rc.STATUT_EN_COURS},
                         {"CAND-006", "CAND-007", "CAND-008"})

    def test_etat_a_une_date_anterieure(self):
        cand = next(c for c in self.d["candidatures"] if c["candidature_id"] == "CAND-001")
        au_12_09 = rc.etat_candidature(self.d, cand, date(2026, 9, 12))
        self.assertEqual((au_12_09["etape"], au_12_09["statut"]), (3, rc.STATUT_EN_COURS))
        self.assertEqual(au_12_09["echeance"], date(2026, 9, 17))
        au_09_09 = rc.etat_candidature(self.d, cand, date(2026, 9, 9))
        self.assertEqual(au_09_09["etape"], 2)

    def test_ordre_fixe_sans_classement(self):
        ids = [s["candidature_id"] for s in rc.tous_les_etats(self.d, DATE_REFERENCE)]
        self.assertEqual(ids, sorted(ids))

    def test_entonnoir_recoupe_avec_sql_et_preparation(self):
        sql = sqlite3.connect(":memory:")
        sql.executescript((RACINE / "sql" / "01_creation_tables.sql").read_text(encoding="utf-8"))
        for table in ("offres_emploi", "candidatures", "recrutement_etapes"):
            lignes = lire_csv(DOSSIER_RAW / f"{table}.csv")
            cols = list(lignes[0])
            sql.executemany(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                            [[l[c] or None for c in cols] for l in lignes])
        par_sql = dict(sql.execute("""SELECT etape, COUNT(DISTINCT candidature_id) FROM recrutement_etapes
                                      WHERE resultat <> 'Désistement' AND date <= ? GROUP BY etape""",
                                   (str(DATE_REFERENCE),)).fetchall())
        module = rc.entonnoir(self.d, DATE_REFERENCE)
        self.assertEqual({k: v for k, v in module.items() if v}, par_sql)
        prep = {}
        for l in lire_csv(DOSSIER_PROCESSED / "recrutement_entonnoir.csv"):
            prep[int(l["ordre_etape"])] = prep.get(int(l["ordre_etape"]), 0) + int(l["nb_candidats"])
        self.assertEqual(module, prep)


class ModelesGeneres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = rc.charger_donnees()
        cls.offres = {o["offre_id"]: o for o in cls.d["offres_emploi"]}

    def test_dates_en_francais_et_jours_ouvrables(self):
        self.assertEqual(rc.date_longue(date(2026, 11, 4)), "mercredi 4 novembre 2026")
        self.assertEqual(rc.decaler_jours_ouvrables(date(2026, 11, 2), -2), date(2026, 10, 29))  # lundi -> jeudi
        self.assertEqual(rc.decaler_jours_ouvrables(date(2026, 10, 30), 1), date(2026, 11, 2))   # vendredi -> lundi

    def test_courriel_de_convocation(self):
        cand = next(c for c in self.d["candidatures"] if c["candidature_id"] == "CAND-006")
        texte = rc.generer_convocation(cand, self.offres["OFF-2026-02"], rc.creneau_de(self.d, "CAND-006"))
        self.assertNotIn("{", texte)
        self.assertNotIn("}", texte)
        for attendu in ("Bonjour Trésor Bashizi", "mercredi 4 novembre 2026", "de 08h30 à 10h30",
                        "Bureau de Bukavu", "au plus tard le lundi 2 novembre 2026", "MODÈLE FICTIF"):
            self.assertIn(attendu, texte)

    def test_courriel_incomplet_refuse(self):
        cand = next(c for c in self.d["candidatures"] if c["candidature_id"] == "CAND-006")
        creneau = {k: v for k, v in rc.creneau_de(self.d, "CAND-006").items() if k != "lieu"}
        with self.assertRaises(KeyError):
            rc.generer_convocation(cand, self.offres["OFF-2026-02"], creneau)

    def test_checklist_d_integration(self):
        items = rc.generer_checklist(date(2026, 11, 2))   # lundi
        self.assertEqual(len(items), len(rc.CHECKLIST_INTEGRATION))
        self.assertEqual((items[0]["repere"], items[0]["date"]), ("J-10", date(2026, 10, 23)))
        self.assertTrue(all(i["date"].weekday() < 5 for i in items))
        self.assertEqual([i["date"] for i in items], sorted(i["date"] for i in items))
        # Prise de fonction un mercredi : J-10 et J+4 tombent un dimanche et sont décalés.
        items = {i["repere"]: i["date"] for i in rc.generer_checklist(date(2026, 11, 4))}
        self.assertEqual(items["J-10"], date(2026, 10, 23))   # dim. 25/10 -> ven. 23/10
        self.assertEqual(items["J+4"], date(2026, 11, 9))     # dim. 08/11 -> lun. 09/11

    def test_planning_et_page(self):
        planning = gen.planning_markdown(self.d, DATE_REFERENCE)
        for c in self.d["planning_entretiens"]:
            self.assertIn(c["creneau_id"], planning)
        self.assertIn("Annulé (désistement)", planning)
        page = gen.construire(self.d, DATE_REFERENCE)
        self.assertIn("Aucune décision automatisée", page)
        self.assertIn("pas un outil officiel de Nuru", page)
        self.assertNotIn("{", page.split("<script>")[0].split("</style>")[1])  # aucun champ non remplacé


class GardeFous(unittest.TestCase):
    def test_aucune_caracteristique_sensible_collectee(self):
        colonnes = set(lire_csv(DOSSIER_RAW / "candidatures.csv")[0])
        self.assertFalse(colonnes & {"genre", "date_naissance", "age", "nationalite", "situation_familiale",
                                     "religion", "sante", "photo"})

    def test_tous_les_intervenants_du_journal_sont_humains(self):
        intervenants = {e["intervenant"] for e in rc.charger_donnees()["recrutement_etapes"]}
        self.assertLessEqual(intervenants, rc.INTERVENANTS_HUMAINS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
