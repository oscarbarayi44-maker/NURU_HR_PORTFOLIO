"""
Tests du module de suivi administratif RH.

1. Exemples fictifs miniatures : 3 collaborateurs dont on connaît le résultat à la main.
2. Minimisation : aucune donnée sensible inutile dans les sorties du module.
3. Recoupement : les calculs du module sont comparés aux données sources par
   des méthodes indépendantes (requêtes SQL, script de préparation, CSV bruts).

Lancer depuis la racine du projet :
    python -m unittest discover -s analysis -v
"""
import sqlite3
import sys
import unittest
from datetime import date
from pathlib import Path

import suivi_rh as rh
from commun import DATE_REFERENCE, DOSSIER_PROCESSED, DOSSIER_RAW, RACINE, lire_csv

sys.path.insert(0, str(RACINE / "hr_admin"))
import generer_module  # noqa: E402

CHAMPS_INTERDITS = {"date_naissance", "email_professionnel", "salaire_brut_mensuel_usd", "genre",
                    "motif_sortie", "note_evaluation_sur_20", "indemnite_mensuelle_usd", "type_absence"}


def collab(matricule, nom, dept, embauche, sortie=""):
    return {"matricule": matricule, "prenom": "Test", "nom": nom, "departement": dept,
            "poste": "Poste fictif", "bureau": "Goma", "date_embauche": embauche,
            "date_sortie": sortie, "statut": "Sorti" if sortie else "Actif"}


def contrat(cid, matricule, type_ct, debut, fin=""):
    return {"contrat_id": cid, "matricule": matricule, "type_contrat": type_ct,
            "date_debut": debut, "date_fin": fin, "motif": "Embauche initiale"}


def absence(aid, matricule, type_abs, debut, fin, jours, statut):
    return {"absence_id": aid, "matricule": matricule, "type_absence": type_abs, "date_debut": debut,
            "date_fin": fin, "nb_jours_ouvrables": jours, "statut": statut}


def stagiaire(sid, debut, fin, note=""):
    return {"stagiaire_id": sid, "prenom": "Stagiaire", "nom": sid, "filiere": "Gestion", "niveau": "L3",
            "departement": "Finance", "encadreur_matricule": "T-001", "date_debut": debut,
            "date_fin": fin, "note_evaluation_sur_20": note}


def mini_donnees():
    """Jeu miniature : T-001 en CDD jusqu'au 31/12/2026, T-002 sorti le 30/06/2026, T-003 en CDI."""
    return {
        "collaborateurs": [
            collab("T-001", "Alpha", "Finance", "2026-01-01"),
            collab("T-002", "Bravo", "Logistique", "2025-01-01", sortie="2026-06-30"),
            collab("T-003", "Charlie", "Logistique", "2020-01-01"),
        ],
        "contrats": [
            contrat("C-1", "T-001", "CDD", "2026-01-01", "2026-12-31"),
            contrat("C-2", "T-002", "CDI", "2025-01-01", "2026-06-30"),
            contrat("C-3", "T-003", "CDI", "2020-01-01"),
        ],
        "absences": [
            absence("A-1", "T-001", "Maladie", "2026-03-02", "2026-03-04", "3", "Approuvée"),  # lun -> mer
            absence("A-2", "T-003", "Congé annuel", "2026-08-03", "2026-08-07", "5", "Approuvée"),
            absence("A-3", "T-003", "Congé annuel", "2026-09-07", "2026-09-11", "5", "Refusée"),
            absence("A-4", "T-001", "Congé annuel", "2026-11-02", "2026-11-06", "5", "En attente"),
        ],
        "stagiaires": [
            stagiaire("S-1", "2026-02-01", "2026-04-30", note="15"),
            stagiaire("S-2", "2026-10-01", "2026-11-20"),
        ],
    }


class ExemplesFictifs(unittest.TestCase):
    def setUp(self):
        self.d = mini_donnees()

    def test_seuils_d_alerte(self):
        attendus = {None: rh.SANS_ECHEANCE, -1: rh.ECHU, 0: rh.URGENT, 30: rh.URGENT,
                    31: rh.A_PREPARER, 60: rh.A_PREPARER, 61: rh.A_SURVEILLER,
                    90: rh.A_SURVEILLER, 91: rh.RAS}
        for jours, niveau in attendus.items():
            self.assertEqual(rh.niveau_alerte(jours), niveau, f"{jours} jours")

    def test_echeance_du_cdd_selon_la_date_de_consultation(self):
        # Le CDD de T-001 se termine le 31/12/2026.
        cas = {date(2026, 10, 1): (91, rh.RAS), date(2026, 11, 1): (60, rh.A_PREPARER),
               date(2026, 12, 1): (30, rh.URGENT), date(2027, 1, 5): (-5, rh.ECHU)}
        for jour, (jours, niveau) in cas.items():
            ligne = next(l for l in rh.echeances(self.d, jour) if l["matricule"] == "T-001")
            self.assertEqual((ligne["jours_restants"], ligne["alerte"]), (jours, niveau), str(jour))

    def test_sortant_exclu_des_echeances_et_cdi_sans_echeance(self):
        lignes = {l["matricule"]: l for l in rh.echeances(self.d, date(2026, 10, 31))}
        self.assertNotIn("T-002", lignes)
        self.assertEqual(lignes["T-003"]["alerte"], rh.SANS_ECHEANCE)

    def test_effectifs(self):
        self.assertEqual(rh.effectifs_par_departement(self.d, date(2026, 10, 31)),
                         {"Finance": {"CDI": 0, "CDD": 1}, "Logistique": {"CDI": 1, "CDD": 0}})
        mensuel = {m["mois"]: m for m in rh.effectifs_mensuels(self.d, date(2026, 10, 31))}
        self.assertEqual((mensuel["2026-01"]["effectif_debut"], mensuel["2026-01"]["entrees"]), (2, 1))
        self.assertEqual((mensuel["2026-06"]["sorties"], mensuel["2026-06"]["effectif_fin"]), (1, 2))

    def test_absences_comptees_et_motif_de_sante_masque(self):
        par_mois = rh.jours_absence_par_mois(self.d, date(2026, 10, 31))
        # Refusée et En attente ne comptent pas : 3 + 5 = 8 jours.
        self.assertEqual(sum(par_mois.values()), 8)
        self.assertEqual(par_mois[("2026-03", rh.CONFIDENTIEL)], 3)
        # Consultation au mardi 03/03 : seuls lundi et mardi sont déjà réalisés.
        self.assertEqual(sum(rh.jours_absence_par_mois(self.d, date(2026, 3, 3)).values()), 2)
        self.assertNotIn("Maladie", {a["categorie"] for a in rh.liste_absences(self.d)})
        self.assertEqual(rh.categorie_affichee("Type inconnu"), rh.CONFIDENTIEL)

    def test_stagiaires(self):
        s = {l["stagiaire_id"]: l for l in rh.suivi_stagiaires(self.d, date(2026, 10, 31))}
        self.assertEqual((s["S-1"]["statut"], s["S-1"]["evaluation_finale"]), ("Terminé", "Réalisée"))
        self.assertEqual((s["S-2"]["statut"], s["S-2"]["jours_avant_fin"], s["S-2"]["fin_proche"]),
                         ("En cours", 20, True))


class MinimisationDesDonnees(unittest.TestCase):
    def test_aucun_champ_sensible_dans_les_sorties(self):
        d, jour = rh.charger_donnees(), DATE_REFERENCE
        sorties = (rh.registre_personnel(d, jour) + rh.tableau_contrats(d, jour) + rh.echeances(d, jour)
                   + rh.liste_absences(d) + rh.suivi_stagiaires(d, jour))
        for ligne in sorties:
            self.assertFalse(CHAMPS_INTERDITS & ligne.keys(), CHAMPS_INTERDITS & ligne.keys())

    def test_page_html_sans_donnee_sensible(self):
        page = generer_module.construire(DATE_REFERENCE)
        self.assertNotIn("Maladie", page)
        self.assertNotIn("Congé de maternité", page)
        self.assertNotIn("exemple-rh.test", page)          # aucune adresse e-mail
        self.assertIn("Données fictives", page)
        self.assertIn("pas un outil officiel de Nuru", page)
        self.assertIn("appartient au responsable RH", page)
        for c in lire_csv(DOSSIER_RAW / "collaborateurs.csv"):
            naissance = c["date_naissance"]
            self.assertNotIn(f"{naissance[8:10]}/{naissance[5:7]}/{naissance[:4]}", page)


class RecoupementAvecLesSources(unittest.TestCase):
    """Compare le module à des calculs indépendants sur les vraies données fictives."""

    @classmethod
    def setUpClass(cls):
        cls.d = rh.charger_donnees()
        cls.jour = DATE_REFERENCE
        # Base SQLite en mémoire, construite directement depuis les CSV bruts.
        cls.sql = sqlite3.connect(":memory:")
        cls.sql.executescript((RACINE / "sql" / "01_creation_tables.sql").read_text(encoding="utf-8"))
        for table in ("collaborateurs", "contrats", "absences"):
            lignes = lire_csv(DOSSIER_RAW / f"{table}.csv")
            cols = list(lignes[0])
            cls.sql.executemany(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                                [[l[c] or None for c in cols] for l in lignes])

    def requete(self, texte):
        return self.sql.execute(texte, {"ref": str(self.jour)}).fetchall()

    def test_effectif_actif(self):
        (nb_sql,), = self.requete("SELECT COUNT(*) FROM collaborateurs WHERE statut = 'Actif'")
        self.assertEqual(rh.indicateurs(self.d, self.jour)["effectif_actif"], nb_sql)

    def test_effectifs_par_departement_et_contrat(self):
        sql = self.requete("""
            SELECT c.departement, ct.type_contrat, COUNT(*) FROM collaborateurs c
            JOIN contrats ct ON ct.matricule = c.matricule
            WHERE c.statut = 'Actif' AND ct.date_debut <= :ref AND (ct.date_fin IS NULL OR ct.date_fin >= :ref)
            GROUP BY 1, 2""")
        attendu = {}
        for dep, type_ct, nb in sql:
            attendu.setdefault(dep, {"CDI": 0, "CDD": 0})[type_ct] = nb
        self.assertEqual(rh.effectifs_par_departement(self.d, self.jour), attendu)

    def test_echeances_a_90_jours(self):
        sql = self.requete("""
            SELECT ct.matricule, CAST(julianday(ct.date_fin) - julianday(:ref) AS INTEGER)
            FROM contrats ct JOIN collaborateurs c ON c.matricule = ct.matricule
            WHERE c.statut = 'Actif' AND ct.type_contrat = 'CDD'
              AND ct.date_fin BETWEEN :ref AND date(:ref, '+90 days')""")
        module = {(l["matricule"], l["jours_restants"]) for l in rh.echeances(self.d, self.jour)
                  if l["jours_restants"] is not None and l["jours_restants"] <= 90}
        self.assertEqual(module, set(sql))
        # Et identiques au fichier produit par le script de préparation.
        prep = {l["matricule"]: (int(l["jours_restants"]) if l["jours_restants"] else None, l["niveau_alerte"])
                for l in lire_csv(DOSSIER_PROCESSED / "suivi_echeances_contrats.csv")}
        self.assertEqual({l["matricule"]: (l["jours_restants"], l["alerte"]) for l in rh.echeances(self.d, self.jour)},
                         prep)

    def test_registre_mensuel(self):
        prep = [{k: (v if k == "mois" else int(v)) for k, v in l.items()
                 if k in ("mois", "effectif_debut", "entrees", "sorties", "effectif_fin")}
                for l in lire_csv(DOSSIER_PROCESSED / "effectifs_mensuels_2026.csv")]
        self.assertEqual(rh.effectifs_mensuels(self.d, self.jour), prep)

    def test_total_des_jours_d_absence(self):
        (sql_total,), = self.requete("""
            SELECT SUM(nb_jours_ouvrables) FROM absences
            WHERE statut IN ('Approuvée', 'Constatée') AND date_debut <= :ref""")
        prep_total = sum(int(l["jours_ouvrables"]) for l in lire_csv(DOSSIER_PROCESSED / "absences_par_mois_2026.csv"))
        module_total = rh.indicateurs(self.d, self.jour)["jours_absence_realises"]
        self.assertEqual(module_total, sql_total)
        self.assertEqual(module_total, prep_total)

    def test_statut_des_stagiaires(self):
        prep = {l["stagiaire_id"]: l["statut"] for l in lire_csv(DOSSIER_PROCESSED / "stagiaires_suivi.csv")}
        self.assertEqual({s["stagiaire_id"]: s["statut"] for s in rh.suivi_stagiaires(self.d, self.jour)}, prep)


if __name__ == "__main__":
    unittest.main(verbosity=2)
