"""
Tests du classeur Excel d'analyse RH (dashboard/generer_classeur_excel.py).

1. Minimisation : aucune donnée sensible (date de naissance, e-mail, salaire, genre,
   motif de sortie, note, indemnité, nom de candidat) dans le classeur.
2. Aucun indicateur écrit en dur : les valeurs du tableau de bord sont des formules.
3. Compatibilité Excel 2010 et suivants : pas de fonctions récentes (XLOOKUP, FILTER, MAXIFS…).
4. Mention « Données fictives » sur chaque feuille.

Les valeurs calculées par Excel ont été comparées aux modules Python lors de la création
du classeur ; ces tests vérifient la structure, sans avoir besoin d'Excel.

Lancer depuis la racine du projet :
    python -m unittest discover -s analysis -v
"""
import re
import sys
import unittest

import recrutement as rc
from commun import RACINE

sys.path.insert(0, str(RACINE / "dashboard"))
import generer_classeur_excel as gce  # noqa: E402

COLONNES_INTERDITES = ("naissance", "mail", "salaire", "genre", "motif de sortie", "motif_sortie",
                       "note", "indemnit", "commentaire")
FONCTIONS_RECENTES = ("XLOOKUP", "XMATCH", "FILTER(", "SORT(", "UNIQUE(", "SEQUENCE(", "MAXIFS", "MINIFS",
                      "IFS(", "SWITCH(", "TEXTJOIN", "CONCAT(", "LET(")
SAISIES = {"D4", "D5", "D6"}  # cellules modifiables du tableau de bord


class TestClasseurExcel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wb = gce.construire()

    def cellules(self):
        for ws in self.wb.worksheets:
            for ligne in ws.iter_rows():
                for c in ligne:
                    if c.value is not None:
                        yield ws, c

    def test_feuilles_attendues(self):
        for nom in ("Lisez-moi", "Tableau de bord", "Paramètres", "Collaborateurs", "Contrats",
                    "Absences", "Stagiaires", "Candidatures", "Étapes recrutement"):
            self.assertIn(nom, self.wb.sheetnames)

    def test_mention_sur_chaque_feuille(self):
        for ws in self.wb.worksheets:
            textes = [ws[c].value for c in ("A2", "B2")]
            self.assertIn(gce.MENTION, textes, ws.title)

    def test_aucune_colonne_sensible(self):
        for ws in self.wb.worksheets:
            if ws.title in ("Lisez-moi", "Tableau de bord", "Paramètres"):
                continue
            for c in ws[3]:
                entete = str(c.value or "").lower()
                for interdit in COLONNES_INTERDITES:
                    self.assertNotIn(interdit, entete, f"{ws.title}!{c.coordinate} : {c.value}")

    def test_aucun_nom_de_candidat(self):
        noms = {f"{c['prenom']} {c['nom']}" for c in rc.charger_donnees()["candidatures"]}
        noms |= {c["nom"] for c in rc.charger_donnees()["candidatures"]}
        textes = {str(c.value) for ws, c in self.cellules() if ws.title in ("Candidatures", "Étapes recrutement",
                                                                             "Tableau de bord")}
        for nom in noms:
            self.assertFalse(any(nom in t for t in textes), nom)

    def test_indicateurs_calcules_par_formule(self):
        tb = self.wb["Tableau de bord"]
        for ws, c in self.cellules():
            if ws is tb and isinstance(c.value, (int, float)) and c.coordinate not in SAISIES:
                self.fail(f"Valeur écrite en dur : Tableau de bord!{c.coordinate} = {c.value}")
        for ref in ("B9", "D9", "F9", "H9", "B13", "D13", "F13", "H13", "B17", "D17", "F17", "H17"):
            self.assertTrue(str(tb[ref].value).startswith("="), ref)

    def test_formules_compatibles_excel_2010(self):
        for ws, c in self.cellules():
            if isinstance(c.value, str) and c.value.startswith("="):
                formule = c.value.upper()
                for f in FONCTIONS_RECENTES:
                    self.assertIsNone(re.search(r"(?<![A-Z_])" + re.escape(f), formule),
                                      f"{ws.title}!{c.coordinate} utilise {f}")

    def test_noms_definis_valides(self):
        for nom, dn in self.wb.defined_names.items():
            self.assertNotIn("#REF", dn.attr_text, nom)

    def test_saisies_avec_liste_ou_controle(self):
        tb = self.wb["Tableau de bord"]
        couvertes = {str(cellule) for dv in tb.data_validations.dataValidation for cellule in dv.sqref}
        self.assertEqual(couvertes, SAISIES)


if __name__ == "__main__":
    unittest.main()
