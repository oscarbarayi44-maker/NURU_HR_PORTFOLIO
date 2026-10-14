"""
Tests des insights RH : chaque chiffre est recalculé ici indépendamment à partir
des CSV, et l'on vérifie que les constats restent agrégés et confidentiels.

Lancer depuis la racine du projet :
    python -m unittest discover -s analysis -v
"""
import re
import sys
import unittest
from datetime import date, timedelta

import insights as ins
from commun import DATE_REFERENCE, DOSSIER_PROCESSED, DOSSIER_RAW, RACINE, en_date, lire_csv

sys.path.insert(0, str(RACINE / "dashboard"))
sys.path.insert(0, str(RACINE / "documents"))
import generer_rapport_mensuel as grm  # noqa: E402
import generer_tableau_de_bord as gen  # noqa: E402
import tableau_de_bord as tb  # noqa: E402


def jours_ouvres(debut, fin):
    return sum((debut + timedelta(days=k)).weekday() < 5 for k in range((fin - debut).days + 1)) if fin >= debut else 0


class Calculs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.liste = ins.calculer_insights(DATE_REFERENCE)
        cls.par_titre = {i["titre"]: i for i in cls.liste}
        cls.collabs = lire_csv(DOSSIER_RAW / "collaborateurs.csv")

    def insight(self, debut_titre):
        return next(i for t, i in self.par_titre.items() if t.startswith(debut_titre))

    def test_echeances_cdd(self):
        actifs = {c["matricule"] for c in self.collabs if c["statut"] == "Actif"}
        fins = {}
        for k in lire_csv(DOSSIER_RAW / "contrats.csv"):
            if k["matricule"] in actifs and k["date_debut"] <= str(DATE_REFERENCE):
                fins[k["matricule"]] = k   # dernier contrat commencé (fichier trié par date)
        cdd = [k for k in fins.values() if k["type_contrat"] == "CDD"]
        sous_30 = [k for k in cdd if 0 <= (en_date(k["date_fin"]) - DATE_REFERENCE).days <= 30]
        self.assertEqual(self.insight("Échéances de CDD")["indicateur"], f"{len(sous_30)} / {len(cdd)}")

    def test_rotation(self):
        sorties = sum(bool(c["date_sortie"]) and "2026-01-01" <= c["date_sortie"] <= str(DATE_REFERENCE)
                      for c in self.collabs)
        mensuel = lire_csv(DOSSIER_PROCESSED / "effectifs_mensuels_2026.csv")
        moyen = sum(int(m["effectif_fin"]) for m in mensuel) / len(mensuel)
        attendu = f"{100 * sorties / moyen:.1f}".replace(".", ",") + " %"
        self.assertEqual(self.insight("Rotation")["indicateur"], attendu)

    def test_absences_non_planifiees(self):
        numerateur = sum(int(a["nb_jours_ouvrables"]) for a in lire_csv(DOSSIER_RAW / "absences.csv")
                         if a["type_absence"] in ("Maladie", "Absence non justifiée")
                         and a["statut"] in ("Approuvée", "Constatée") and a["date_debut"] <= str(DATE_REFERENCE))
        denominateur = sum(jours_ouvres(max(date(2026, 1, 1), en_date(c["date_embauche"])),
                                        min(DATE_REFERENCE, en_date(c["date_sortie"]) if c["date_sortie"] else DATE_REFERENCE))
                           for c in self.collabs)
        i = self.insight("Absences non planifiées")
        self.assertIn(f"{numerateur} jours d'absence non planifiés sur {denominateur} jours travaillables", i["constat"])
        self.assertEqual(i["indicateur"], f"{100 * numerateur / denominateur:.1f}".replace(".", ",") + " %")

    def test_pic_de_conges(self):
        par_mois = {}
        for l in lire_csv(DOSSIER_PROCESSED / "absences_par_mois_2026.csv"):
            if l["type_absence"] == "Congé annuel":
                par_mois[l["mois"]] = int(l["jours_ouvrables"])
        mois_max = max(par_mois, key=par_mois.get)
        self.assertEqual(self.insight("Mois le plus chargé")["indicateur"], ins.nom_mois(mois_max))
        self.assertIn(f"{par_mois[mois_max]} jours de congé annuel", self.insight("Mois le plus chargé")["constat"])

    def test_part_cdd_par_departement(self):
        i = self.insight("Département")
        self.assertIn("Calcul limité aux départements d'au moins 3 personnes", i["constat"])
        parts = {}
        tdb = tb.donnees_tableau_de_bord(DATE_REFERENCE)
        for dep, v in tdb["effectifs_departements"].items():
            if v["CDI"] + v["CDD"] >= 3:
                parts[dep] = round(100 * v["CDD"] / (v["CDI"] + v["CDD"]))
        self.assertEqual(i["indicateur"], f"{max(parts.values())} %")

    def test_recrutement(self):
        entonnoir = {}
        for l in lire_csv(DOSSIER_PROCESSED / "recrutement_entonnoir.csv"):
            entonnoir[int(l["ordre_etape"])] = entonnoir.get(int(l["ordre_etape"]), 0) + int(l["nb_candidats"])
        i = self.insight("Efficacité du processus")
        self.assertEqual(i["indicateur"], f"{round(100 * entonnoir[3] / entonnoir[2])} %")
        self.assertIn("examinées en présélection", i["constat"])

    def test_egalites_jamais_tranchees_arbitrairement(self):
        self.assertEqual(ins.maximums({"A": 2, "B": 2, "C": 1}), ["A", "B"])
        self.assertEqual(ins.maximums({}), [])
        # Sur les données fictives, trois sources sont à égalité parmi les convocations.
        self.assertIn("Sources à égalité", self.insight("Efficacité du processus")["constat"])

    def test_les_insights_suivent_la_date(self):
        plus_tard = {i["titre"]: i for i in ins.calculer_insights(date(2026, 12, 10))}
        self.assertNotEqual(plus_tard["Échéances de CDD concentrées sur les prochaines semaines"]["constat"],
                            self.insight("Échéances de CDD")["constat"])


class GardeFous(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.liste = ins.calculer_insights(DATE_REFERENCE)
        cls.texte = " ".join(f"{i['titre']} {i['indicateur']} {i['constat']} {i['piste']}" for i in cls.liste)

    def test_aucune_personne_identifiable(self):
        self.assertIsNone(re.search(r"\b(EMP|CAND|STG)-\d+", self.texte))
        for fichier in ("collaborateurs.csv", "candidatures.csv", "stagiaires.csv"):
            for p in lire_csv(DOSSIER_RAW / fichier):
                self.assertNotIn(f"{p['prenom']} {p['nom']}", self.texte)

    def test_aucun_detail_medical(self):
        for mot in ("Maladie", "maladie", "maternité", "diagnostic"):
            self.assertNotIn(mot, self.texte)

    def test_structure_et_ordre(self):
        niveaux = [i["niveau"] for i in self.liste]
        ordre = [ins.ATTENTION, ins.A_SUIVRE, ins.INFORMATION]
        self.assertEqual(niveaux, sorted(niveaux, key=ordre.index))
        for i in self.liste:
            self.assertTrue(i["titre"] and i["indicateur"] and i["constat"] and i["piste"])
            self.assertIn(i["niveau"], ordre)

    def test_integration_tableau_de_bord_et_rapport(self):
        page = gen.construire(tb.donnees_tableau_de_bord(DATE_REFERENCE), self.liste)
        self.assertIn("<h2>Insights RH</h2>", page)
        self.assertIn("la décision appartient au responsable RH", page)
        rapport = grm.rapport(DATE_REFERENCE)
        self.assertIn("### Points d'attention (insights)", rapport)
        for i in self.liste:
            self.assertIn(i["titre"], rapport)


if __name__ == "__main__":
    unittest.main(verbosity=2)
