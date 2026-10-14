"""
Tests du portfolio : convertisseur Markdown, rapport mensuel, procédures,
page d'accueil (profil modifiable, aucune information inventée) et liens.

Lancer depuis la racine du projet :
    python -m unittest discover -s analysis -v
"""
import json
import sys
import unittest

import recrutement as rc
import suivi_rh as rh
import tableau_de_bord as tb
from commun import DATE_REFERENCE, RACINE

sys.path.insert(0, str(RACINE / "portfolio"))
sys.path.insert(0, str(RACINE / "documents"))
import generer_portfolio as gp  # noqa: E402
import generer_rapport_mensuel as grm  # noqa: E402
import markdown_simple as md  # noqa: E402
import verifier_portfolio as vp  # noqa: E402


class ConvertisseurMarkdown(unittest.TestCase):
    def test_elements_courants(self):
        html = md.convertir("# Titre\n\nTexte **gras** et *italique*.\n\n- un\n- [ ] à cocher\n\n"
                            "1. premier\n2. second\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n> Note")
        for attendu in ("<h1>Titre</h1>", "<strong>gras</strong>", "<em>italique</em>", "<ul><li>un</li>",
                        '<li class="case">', "<ol><li>premier</li>", '<th scope="col">A</th>', "<td>2</td>",
                        "<blockquote>Note</blockquote>"):
            self.assertIn(attendu, html)
        self.assertNotIn("---", html)

    def test_html_echappe(self):
        self.assertNotIn("<script>", md.convertir("Texte <script>alert(1)</script>"))


class RapportMensuel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texte = grm.rapport(DATE_REFERENCE)
        cls.d = rh.charger_donnees()

    def test_chiffres_identiques_aux_modules(self):
        fin_oct = rh.effectifs_mensuels(self.d, DATE_REFERENCE)[-1]["effectif_fin"]
        self.assertIn(f"Effectif actif en fin de mois : **{fin_oct}**", self.texte)
        tdb = tb.donnees_tableau_de_bord(DATE_REFERENCE)
        self.assertIn(f"CDD arrivant à échéance sous 30 jours : **{len(tdb['contrats_30'])}**", self.texte)
        jours_oct = sum(n for (m, _), n in rh.jours_absence_par_mois(self.d, DATE_REFERENCE).items() if m == "2026-10")
        self.assertIn(f"réalisés dans le mois : **{jours_oct}**", self.texte)
        prioritaires = sum(a["urgence"] in (tb.EN_RETARD, tb.SOUS_7) for a in tdb["actions"])
        self.assertIn(f"(en retard ou sous 7 jours) : **{prioritaires}**", self.texte)
        self.assertIn(f"{rc.indicateurs(rc.charger_donnees(), DATE_REFERENCE)['delai_moyen_decision_jours']} jours", self.texte)

    def test_mentions_et_confidentialite(self):
        self.assertIn("pas un document officiel de Nuru", self.texte)
        self.assertIn("appartient au responsable RH", self.texte)
        self.assertNotIn("Maladie", self.texte)
        self.assertNotIn("maternité", self.texte.lower())

    def test_fichier_a_jour(self):
        fichier = RACINE / "documents" / "rapports" / "rapport_mensuel_rh_2026-10.md"
        self.assertEqual(fichier.read_text(encoding="utf-8"), self.texte,
                         "rapport obsolète : relancer documents/generer_rapport_mensuel.py")


class Procedures(unittest.TestCase):
    def test_mentions_obligatoires(self):
        for f in (RACINE / "documents" / "procedures").glob("*.md"):
            texte = f.read_text(encoding="utf-8")
            with self.subTest(f.name):
                self.assertIn("pas un document officiel de Nuru", texte)
                self.assertIn("à vérifier", texte.lower().replace("à fixer", "à vérifier"))
                self.assertIn("À valider par le responsable RH", texte)


class PageAccueil(unittest.TestCase):
    PROFIL_VIDE = json.loads((RACINE / "portfolio" / "profil.json").read_text(encoding="utf-8"))

    def construire(self, **modifs):
        profil = {**self.PROFIL_VIDE, **modifs}
        return gp.construire_index(profil, [], (10, 0), (5, 0), (8, 6))

    def test_champs_vides_affiches_a_completer_sans_invention(self):
        vide = {k: "" for k in ("nom_complet", "email", "telephone", "linkedin", "portfolio_existant")}
        page = self.construire(**vide)
        self.assertGreaterEqual(page.count("À compléter"), 5)
        self.assertNotIn("mailto:", page)
        self.assertNotIn("linkedin.com", page)

    def test_profil_complete(self):
        page = self.construire(nom_complet="Prénom NOM", email="prenom.nom@exemple.test",
                               linkedin="https://www.linkedin.com/in/exemple", portfolio_existant="ftp://mauvais")
        self.assertIn("Prénom NOM", page)
        self.assertIn('href="mailto:prenom.nom@exemple.test"', page)
        self.assertIn('href="https://www.linkedin.com/in/exemple"', page)
        self.assertNotIn('href="ftp://mauvais"', page)       # seuls les liens https sont publiés

    def test_honnetete(self):
        page = self.construire()
        for attendu in ("indépendant de Nuru", "fictifs", "avec l'assistance de Claude Code",
                        "Non utilisé dans ce projet", "Limites connues", "ne note pas, ne classe pas"):
            self.assertIn(attendu, page)
        self.assertIn("10 tests réussis", page)
        self.assertIn("1 échec(s) sur 10 tests", gp.construire_index(self.PROFIL_VIDE, [], (10, 1), (5, 0), (8, 6)))


class SiteGenere(unittest.TestCase):
    def test_liens_mentions_et_affichage_mobile(self):
        if not (RACINE / "index.html").exists():
            self.skipTest("site non généré : lancer python portfolio/generer_portfolio.py")
        erreurs, _, _ = vp.verifier()
        self.assertEqual(erreurs, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
