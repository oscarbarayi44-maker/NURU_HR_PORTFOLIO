"""
Tests du tableau de bord RH.

1. Chaque indicateur est recalculé ici DIRECTEMENT à partir des CSV (sans passer
   par les modules), à deux dates différentes : les valeurs suivent les données.
2. Actions administratives : niveaux d'urgence, tri, contenu.
3. Exports CSV et page HTML générée.

Lancer depuis la racine du projet :
    python -m unittest discover -s analysis -v
"""
import csv
import io
import re
import sys
import unittest
from datetime import date
from html import unescape

import tableau_de_bord as tb
from commun import DATE_REFERENCE, DOSSIER_PROCESSED, DOSSIER_RAW, RACINE, en_date, lire_csv

sys.path.insert(0, str(RACINE / "dashboard"))
import generer_tableau_de_bord as gen  # noqa: E402

DATES_TEST = (DATE_REFERENCE, date(2026, 12, 10))


def calcul_direct(jour):
    """Recalcul indépendant des indicateurs, à partir des seuls fichiers CSV bruts."""
    collabs = lire_csv(DOSSIER_RAW / "collaborateurs.csv")
    contrats = lire_csv(DOSSIER_RAW / "contrats.csv")
    actifs = [c for c in collabs if en_date(c["date_embauche"]) <= jour
              and (not c["date_sortie"] or en_date(c["date_sortie"]) > jour)]
    deps, cdd_30 = {}, set()
    for c in actifs:
        ct = max((k for k in contrats if k["matricule"] == c["matricule"] and en_date(k["date_debut"]) <= jour),
                 key=lambda k: k["date_debut"])
        deps.setdefault(c["departement"], {"CDI": 0, "CDD": 0})[ct["type_contrat"]] += 1
        if ct["type_contrat"] == "CDD" and 0 <= (en_date(ct["date_fin"]) - jour).days <= 30:
            cdd_30.add(c["matricule"])
    stagiaires = lire_csv(DOSSIER_RAW / "stagiaires.csv")
    absences = lire_csv(DOSSIER_RAW / "absences.csv")
    return {
        "effectif_total": len(actifs),
        "collaborateurs_enregistres": len(collabs),
        "effectifs_departements": deps,
        "contrats_30": cdd_30,
        "stagiaires": {
            "En cours": sum(en_date(s["date_debut"]) <= jour <= en_date(s["date_fin"]) for s in stagiaires),
            "À venir": sum(en_date(s["date_debut"]) > jour for s in stagiaires),
            "Terminé": sum(en_date(s["date_fin"]) < jour for s in stagiaires),
        },
        "absences_enregistrees": len(absences),
        "absences_realisees": sum(a["statut"] in ("Approuvée", "Constatée") and en_date(a["date_debut"]) <= jour
                                  for a in absences),
        "candidatures": len(lire_csv(DOSSIER_RAW / "candidatures.csv")),
    }


class IndicateursCalculesDepuisLesSources(unittest.TestCase):
    def test_indicateurs_a_deux_dates(self):
        for jour in DATES_TEST:
            with self.subTest(jour=jour):
                tdb, direct = tb.donnees_tableau_de_bord(jour), calcul_direct(jour)
                self.assertEqual(tdb["effectif_total"], direct["effectif_total"])
                self.assertEqual(tdb["collaborateurs_enregistres"], direct["collaborateurs_enregistres"])
                self.assertEqual(tdb["effectifs_departements"], direct["effectifs_departements"])
                self.assertEqual({l["matricule"] for l in tdb["contrats_30"]}, direct["contrats_30"])
                self.assertEqual(tdb["stagiaires"], direct["stagiaires"])
                self.assertEqual(tdb["absences"]["enregistrees"], direct["absences_enregistrees"])
                self.assertEqual(tdb["absences"]["realisees"], direct["absences_realisees"])
                self.assertEqual(tdb["candidatures_total"], direct["candidatures"])

    def test_les_valeurs_changent_avec_la_date(self):
        # Au 10/12/2026, le CDD de EMP-016 (fin le 04/01/2027) entre dans la fenêtre des 30 jours.
        avant, apres = (tb.donnees_tableau_de_bord(j) for j in DATES_TEST)
        self.assertNotIn("EMP-016", {l["matricule"] for l in avant["contrats_30"]})
        self.assertIn("EMP-016", {l["matricule"] for l in apres["contrats_30"]})

    def test_absences_et_recrutement_recoupes_avec_les_fichiers_prepares(self):
        tdb = tb.donnees_tableau_de_bord(DATE_REFERENCE)
        prep_abs = sum(int(l["jours_ouvrables"]) for l in lire_csv(DOSSIER_PROCESSED / "absences_par_mois_2026.csv"))
        self.assertEqual(tdb["absences"]["jours_realises"], prep_abs)
        self.assertEqual(sum(tdb["absences"]["jours_par_categorie"].values()), prep_abs)
        prep_rec = {(l["offre_id"], int(l["ordre_etape"])): int(l["nb_candidats"])
                    for l in lire_csv(DOSSIER_PROCESSED / "recrutement_entonnoir.csv")}
        module = {(o, k): n for o, etapes in tdb["entonnoir"].items() for k, n in etapes.items()}
        self.assertEqual(module, prep_rec)


class ActionsAdministratives(unittest.TestCase):
    def test_niveaux_d_urgence(self):
        j = date(2026, 10, 31)
        cas = {None: tb.SANS_DATE, date(2026, 10, 30): tb.EN_RETARD, j: tb.SOUS_7,
               date(2026, 11, 7): tb.SOUS_7, date(2026, 11, 8): tb.SOUS_30,
               date(2026, 11, 30): tb.SOUS_30, date(2026, 12, 1): tb.PLUS_TARD}
        for echeance, attendu in cas.items():
            self.assertEqual(tb.urgence(echeance, j), attendu, str(echeance))

    def test_contenu_et_tri(self):
        actions = tb.donnees_tableau_de_bord(DATE_REFERENCE)["actions"]
        rangs = [tb.ORDRE_URGENCE.index(a["urgence"]) for a in actions]
        self.assertEqual(rangs, sorted(rangs))
        self.assertTrue(all(a["responsable"] and a["action"] for a in actions))
        par_domaine = {}
        for a in actions:
            par_domaine[a["domaine"]] = par_domaine.get(a["domaine"], 0) + 1
        # Recalcul direct : CDD actifs finissant dans les 90 jours, demandes en attente,
        # stagiaires commençant sous 30 jours, candidatures ouvertes à une action.
        direct = calcul_direct(DATE_REFERENCE)
        collabs = {c["matricule"]: c for c in lire_csv(DOSSIER_RAW / "collaborateurs.csv")}
        cdd_90 = {k["matricule"] for k in lire_csv(DOSSIER_RAW / "contrats.csv")
                  if k["type_contrat"] == "CDD" and k["date_fin"] and collabs[k["matricule"]]["statut"] == "Actif"
                  and 0 <= (en_date(k["date_fin"]) - DATE_REFERENCE).days <= 90}
        attente = sum(a["statut"] == "En attente" for a in lire_csv(DOSSIER_RAW / "absences.csv"))
        self.assertEqual(par_domaine.get("Contrats", 0), len(cdd_90))
        self.assertEqual(par_domaine.get("Congés", 0), attente)
        self.assertGreaterEqual(direct["stagiaires"]["À venir"], par_domaine.get("Stagiaires", 0))
        self.assertIn("Recrutement", par_domaine)

    def test_aucun_motif_de_sante_dans_les_actions(self):
        for a in tb.donnees_tableau_de_bord(DATE_REFERENCE)["actions"]:
            self.assertNotIn("maladie", a["action"].lower())
            self.assertNotIn("maternité", a["action"].lower())


class ExportsEtPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tdb = tb.donnees_tableau_de_bord(DATE_REFERENCE)
        cls.page = gen.construire(cls.tdb)

    def lire(self, texte):
        return list(csv.reader(io.StringIO(texte), delimiter=";"))

    def test_export_des_actions(self):
        lignes = self.lire(tb.export_actions_csv(self.tdb))
        self.assertEqual(lignes[0], ["Urgence", "Échéance", "Domaine", "Objet", "Action", "Responsable"])
        self.assertEqual(len(lignes) - 1, len(self.tdb["actions"]))

    def test_export_des_indicateurs(self):
        lignes = {(l[1], l[2]): l[3] for l in self.lire(tb.export_indicateurs_csv(self.tdb))[1:]}
        self.assertEqual(int(lignes[("Effectif", "Effectif actif")]), self.tdb["effectif_total"])
        self.assertEqual(int(lignes[("Contrats", "CDD arrivant à échéance sous 30 jours")]), len(self.tdb["contrats_30"]))
        total_dep = sum(int(v) for (r, _), v in lignes.items() if r == "Effectif par département")
        self.assertEqual(total_dep, self.tdb["effectif_total"])

    def test_csv_integres_a_la_page_identiques_aux_exports(self):
        for ident, attendu in (("csv-actions", tb.export_actions_csv(self.tdb)),
                               ("csv-indicateurs", tb.export_indicateurs_csv(self.tdb))):
            integre = re.search(rf'<script type="text/plain" id="{ident}">(.*?)</script>', self.page, re.S).group(1)
            # Dans la page : fins de ligne LF uniquement (sinon lignes vides à l'export sous Windows).
            self.assertNotIn("\r", integre)
            self.assertEqual(unescape(integre).replace("\n", "\r\n"), attendu)

    def test_page_complete_et_coherente(self):
        p = self.page
        for attendu in ("Données fictives", "pas un outil officiel de Nuru", "Tableau de bord RH",
                        "Exporter les indicateurs (CSV)", "Exporter les actions (CSV)", "Imprimer / PDF",
                        "appartient au responsable RH", 'name="viewport"', "@media (max-width: 560px)"):
            self.assertIn(attendu, p)
        nb_barres = (len(self.tdb["effectifs_departements"]) + 8 + len(self.tdb["absences"]["jours_par_categorie"]))
        self.assertEqual(p.count('class="barre"'), nb_barres)
        self.assertEqual(p.count('<ul class="legende">'), 3)          # contrats, offres, urgences
        largeurs = [float(x) for x in re.findall(r"width:([\d.]+)%", p)]
        self.assertTrue(largeurs and max(largeurs) <= 100.0 and min(largeurs) > 0)
        corps = p.split("</style>")[1].split("<script")[0]
        self.assertNotIn("{", corps)                                   # aucun champ non remplacé
        self.assertIsNone(re.search(r"\bnan\b", corps, flags=re.I))    # valeur numérique invalide
        self.assertEqual(p.count("<section"), p.count("</section>"))
        self.assertIn(f">{self.tdb['effectif_total']}<", p)

    def test_fichiers_d_export_ecrits(self):
        dossier = RACINE / "dashboard" / "exports"
        for nom in (f"indicateurs_rh_{DATE_REFERENCE}.csv", f"actions_rh_{DATE_REFERENCE}.csv"):
            contenu = (dossier / nom).read_bytes()
            self.assertTrue(contenu.startswith(b"\xef\xbb\xbf"), f"{nom} : BOM UTF-8 attendu pour Excel")
            self.assertNotIn(b"\r\r", contenu)
        # Page réellement écrite sur disque : aucun CR doublé (sinon lignes vides dans l'export du navigateur).
        page = (RACINE / "dashboard" / "tableau_de_bord_rh.html").read_bytes()
        self.assertNotIn(b"\r\r", page)


if __name__ == "__main__":
    unittest.main(verbosity=2)
