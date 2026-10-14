# dashboard : tableau de bord RH

> **Données fictives. Portfolio personnel, ce n'est pas un outil officiel de Nuru.**

Une page unique, `tableau_de_bord_rh.html`, qui rassemble les indicateurs des modules RH et recrutement. Elle s'ouvre dans un navigateur, **sans connexion Internet ni installation** : pas de bibliothèque externe, les graphiques sont construits en HTML/CSS.

## Ce que montre le tableau de bord

| Zone | Contenu | Source |
|---|---|---|
| Indicateurs clés | Effectif actif, CDD à échéance sous 30 jours, stagiaires suivis, absences enregistrées, candidatures, actions à effectuer | `collaborateurs.csv`, `contrats.csv`, `stagiaires.csv`, `absences.csv`, `candidatures.csv` |
| Effectifs par département | Barres empilées CDI / CDD, avec légende | collaborateurs + contrat en vigueur |
| Candidatures par étape | Candidatures ayant franchi chacune des 8 étapes, par offre, avec légende | `recrutement_etapes.csv` |
| Absences | Jours ouvrables réalisés par catégorie (motifs de santé regroupés et confidentiels) | `absences.csv` |
| CDD à échéance sous 30 jours | Liste et rappel : la décision appartient au responsable RH | `contrats.csv` |
| Insights RH | 7 constats chiffrés calculés automatiquement (échéances de CDD, part de CDD par département, rotation, absences non planifiées, pic de congés, efficacité du recrutement, actions en retard), avec un niveau (Attention / À suivre / Information) et une piste d'action. Constats agrégés uniquement, sans motif de santé isolé ; la décision appartient au responsable RH. Calcul : [`analysis/insights.py`](../analysis/insights.py) | tous les fichiers ci-dessus |
| Actions administratives | Tâches consolidées (contrats, congés, stagiaires, recrutement), triées par urgence, avec légende des niveaux | tous les fichiers ci-dessus |

**Aucune valeur n'est écrite dans le code.** Chaque chiffre est recalculé à partir de `data/raw/` à chaque génération, via [`analysis/tableau_de_bord.py`](../analysis/tableau_de_bord.py), qui s'appuie sur les modules RH et recrutement.

**Interactions disponibles**
- **Infobulle :** au survol (ou au clavier avec Tab) d'une barre, une infobulle donne le détail par série.
- **Voir les données :** sous chaque graphique, ce lien affiche le tableau des chiffres.
- **Exporter les indicateurs (CSV)** et **Exporter les actions (CSV)** : les fichiers s'ouvrent directement dans Excel (séparateur `;`, accents conservés).
- **Imprimer / PDF :** ouvre l'impression du navigateur ; choisir « Enregistrer au format PDF » pour obtenir un PDF.

**Affichage responsive :** sur téléphone, les indicateurs et les graphiques passent sur une colonne, et les libellés des barres passent au-dessus de la barre. Le thème clair ou sombre suit le réglage du système. Les deux couleurs de série ont été contrôlées dans les deux thèmes, y compris pour les daltoniens.

**Niveaux d'urgence des actions :** ⛔ En retard · ⚠ Sous 7 jours · ◷ Sous 30 jours · ◔ Plus tard · – Sans date fixée.

## Lancer le tableau de bord localement

Prérequis : **Python 3.10 ou plus récent** (aucune bibliothèque à installer) et un navigateur récent (Edge, Chrome ou Firefox).

Depuis la racine du projet, dans le terminal de VS Code :

```bash
python dashboard/generer_tableau_de_bord.py
```

Résultat attendu :
```
Tableau de bord généré : dashboard/tableau_de_bord_rh.html (situation au 31/10/2026)
Exports : dashboard/exports/indicateurs_rh_2026-10-31.csv, dashboard/exports/actions_rh_2026-10-31.csv
```

Ouvrir ensuite le fichier dans le navigateur :
- dans l'explorateur Windows, double-cliquer sur `dashboard/tableau_de_bord_rh.html` ;
- ou dans le terminal : `start dashboard/tableau_de_bord_rh.html` (Windows).

Aucun serveur web n'est nécessaire. Si un serveur local est préféré : `python -m http.server 8000`, puis ouvrir `http://localhost:8000/dashboard/tableau_de_bord_rh.html`.

**Après une modification des données**, relancer la chaîne complète décrite dans le [README principal](../README.md), puis régénérer le tableau de bord.

**Simuler une autre date de situation**
```bash
python dashboard/generer_tableau_de_bord.py --date 2026-12-10
```
Cette commande crée `tableau_de_bord_rh_test_2026-12-10.html`, que Git ignore. Les exports CSV ne sont écrits que pour la date de référence.

## Tests

```bash
python -m unittest discover -s analysis -v
```
Les 11 tests du tableau de bord (fichier [`analysis/test_tableau_de_bord.py`](../analysis/test_tableau_de_bord.py)) vérifient :
- **Indicateurs :** chacun est recalculé directement depuis les CSV, sans passer par les modules, au 31/10/2026 et au 10/12/2026, et doit être identique à celui du tableau de bord. Ils doivent aussi varier avec la date : par exemple, le CDD de EMP-016 n'entre dans la fenêtre des 30 jours qu'en décembre.
- **Recoupement :** les totaux d'absences et de recrutement correspondent aux fichiers de `data/processed/`.
- **Actions :** les niveaux d'urgence et leurs limites sont respectés, le tri va du plus urgent au moins urgent, et aucun motif de santé n'apparaît.
- **Exports :** les fichiers CSV sont lisibles, leurs totaux sont cohérents, ils commencent par le marqueur UTF-8 attendu par Excel, et ils sont identiques aux données intégrées dans la page.
- **Page :**
  - les mentions obligatoires sont présentes ;
  - le nombre de barres et de légendes est correct ;
  - aucune largeur de barre ne dépasse 100 % ;
  - aucun champ n'est laissé vide ;
  - la page contient bien la balise responsive (`viewport`).

## Limites connues

- **Génération manuelle :** la page est une photographie à une date donnée. Il faut relancer le script après chaque modification des données ; la page ne se met pas à jour seule.
- **Pas de filtres :** la page ne permet pas de filtrer par bureau ou par période.
- **Export du navigateur :** le bouton d'export télécharge le fichier via le navigateur. Les copies écrites sur disque dans `dashboard/exports/` le sont uniquement par le script Python.
- **Contrôle d'accès :** la page n'a pas de mot de passe et doit être conservée sur un espace à accès restreint en situation réelle.
