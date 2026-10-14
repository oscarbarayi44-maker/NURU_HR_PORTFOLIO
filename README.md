# NURU HR DIGITAL PORTFOLIO

> [!WARNING]
> **Données 100 % fictives. Projet non officiel.**
> Toutes les personnes, dates, salaires et documents de ce projet sont **synthétiques** et ont été générés pour la démonstration. Toute ressemblance avec une personne réelle serait une pure coïncidence.
> Ce portfolio est un **projet personnel** réalisé dans le cadre d'une candidature à un stage en Ressources Humaines à Goma (RDC). **Ce n'est pas un outil officiel de Nuru**, il n'a pas été commandé par Nuru, et Nuru ne l'utilise pas.

---

## Voir le portfolio

Ouvrez **[index.html](index.html)** dans un navigateur : c'est la page de présentation du portfolio (profil, formation, compétences, réalisations, documents, IA responsable, tests et limites). Pour la publier en ligne gratuitement, suivez le guide [portfolio/PUBLIER.md](portfolio/PUBLIER.md).

## Objectif

Démontrer, à partir d'un cas fictif réaliste (une organisation de **30 collaborateurs** répartis entre Goma, Bukavu et Beni), ma capacité à :

| # | Compétence | Où la trouver |
|---|---|---|
| 1 | Organiser et archiver des dossiers RH | [Procédure d'archivage et plan de classement](documents/procedures/procedure_archivage_dossiers_individuels.md) |
| 2 | Suivre les contrats et leurs échéances | [Module de suivi RH](hr_admin/) : onglets Contrats et Échéances |
| 3 | Tenir un registre mensuel des effectifs | [Module de suivi RH](hr_admin/) : onglet Effectifs |
| 4 | Suivre absences, congés et stagiaires | [Module de suivi RH](hr_admin/) : onglets Absences et congés, Stagiaires |
| 5 | Organiser un processus de recrutement | [Module de recrutement](recruitment/) : 8 étapes, prochaines actions, planning, convocations, checklist d'intégration |
| 6 | Produire des tableaux de bord RH | [Tableau de bord RH](dashboard/) : indicateurs, graphiques, actions à effectuer, export CSV |
| 7 | Rédiger procédures et rapports administratifs | [3 procédures](documents/procedures/), [rapport mensuel généré](documents/rapports/rapport_mensuel_rh_2026-10.md), [modèles](documents/modeles_courriers/) |

## Structure du projet

```
NURU_HR_PORTFOLIO/
├── index.html             Page d'accueil du portfolio (générée)
├── README.md              Présentation du projet (ce fichier)
├── CLAUDE.md              Instructions de travail pour Claude Code
├── portfolio/             Profil modifiable, générateur du site, captures, vérificateur, guide de publication
├── data/
│   ├── README.md          Dictionnaire des données
│   ├── raw/               Données fictives initiales (générées par script)
│   └── processed/         Données nettoyées et enrichies, prêtes pour l'analyse
├── analysis/              Scripts Python : génération, préparation, contrôle qualité
├── sql/                   Création de la base SQLite et requêtes de consultation
├── hr_admin/              Contrats, effectifs, absences et stagiaires
├── recruitment/           Suivi du recrutement
├── dashboard/             Tableaux de bord RH
├── documents/             Procédures, modèles de courriers, rapports
└── assets/                Éléments graphiques
```

## Le cas fictif en bref (au 31 octobre 2026)

- **30 collaborateurs** enregistrés : 27 actifs et 3 sortis en 2026 (2 démissions, 1 fin de CDD).
- **55 contrats** (CDD, renouvellements et passages en CDI), dont **4 CDD arrivant à échéance dans les 90 jours**.
- **98 absences et demandes de congés** (congés annuels, maladie, maternité, congés de circonstance, absences non justifiées).
- **6 stagiaires** : 3 stages terminés, 2 en cours, 1 à venir.
- **2 offres d'emploi** et **10 candidatures** suivies en 8 étapes, de la réception à l'intégration ; toutes les décisions sont prises par des personnes et aucune caractéristique sensible n'est collectée.

## Outils utilisés

- **CSV / Excel** pour les registres (séparateur `;`, ouverture directe dans Excel en français).
- **Python** (bibliothèque standard uniquement) pour générer, préparer et contrôler les données.
- **SQL (SQLite)** pour interroger les données comme dans un SIRH.
- **Markdown** pour les procédures et les rapports.
- **Claude Code** dans VS Code, comme assistant de travail.

## Reproduire les données

Depuis la racine du projet :

```bash
python analysis/01_generer_donnees_fictives.py   # crée data/raw/
python analysis/02_preparer_donnees.py           # crée data/processed/
python analysis/03_verifier_coherence.py         # contrôle qualité
python sql/charger_base.py                       # crée la base SQLite et lance les requêtes
python hr_admin/generer_module.py                # génère le module de suivi RH (page HTML)
python recruitment/generer_module_recrutement.py # génère le module de recrutement et ses documents
python dashboard/generer_tableau_de_bord.py      # génère le tableau de bord RH et ses exports CSV
python documents/generer_rapport_mensuel.py      # génère le rapport mensuel RH
python portfolio/capturer_ecrans.py              # captures d'écran (Edge ou Chrome requis)
python portfolio/generer_portfolio.py            # génère index.html (exécute aussi les tests)
python portfolio/verifier_portfolio.py           # liens, mentions, affichage mobile, champs à compléter
python -m unittest discover -s analysis -v       # 76 tests
```

## Auteur

Candidat(e) au stage en Ressources Humaines. Licence en Sciences administratives et Management, Master en Management des organisations. Formation certifiée en introduction à la GRH dans le contexte humanitaire, formation certifiée en intelligence artificielle appliquée au monde professionnel avec Claude.
