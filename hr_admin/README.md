# hr_admin : module de suivi administratif RH

> **Données fictives. Portfolio personnel, ce n'est pas un outil officiel de Nuru.**

## Ce que fait le module

Une page de consultation autonome, [module_suivi_rh.html](module_suivi_rh.html), qui s'ouvre dans n'importe quel navigateur sans connexion Internet. Elle présente la situation au **31/10/2026** en 7 onglets :

| Onglet | Contenu |
|---|---|
| Vue d'ensemble | 9 indicateurs clés, effectifs par département et type de contrat |
| Registre du personnel | Matricule, nom, poste, département, bureau, embauche, statut, contrat, sortie |
| Contrats | Tous les contrats : début, fin, motif, statut (En vigueur / Terminé / À venir) |
| Échéances | Alertes à **30, 60 et 90 jours**, avec le rappel que **toute décision contractuelle appartient au responsable RH** |
| Absences et congés | Jours d'absence par mois et par catégorie, détail des absences et demandes |
| Stagiaires | Encadreur, dates, statut, alerte de fin de stage (≤ 30 jours), état de l'évaluation |
| Effectifs | Répartition département × contrat et registre mensuel (début, entrées, sorties, fin) |

Chaque tableau dispose d'un champ **Rechercher** (nom, matricule, département…). Un onglet peut être ouvert directement par l'adresse, par exemple `module_suivi_rh.html#echeances`.

## Fichiers

| Fichier | Rôle |
|---|---|
| [`../analysis/suivi_rh.py`](../analysis/suivi_rh.py) | Moteur de calcul : toutes les règles (alertes, statuts, effectifs, absences) |
| [`generer_module.py`](generer_module.py) | Construit la page HTML à partir du moteur de calcul |
| `module_suivi_rh.html` | Page générée (ne pas modifier à la main) |
| [`../analysis/test_suivi_rh.py`](../analysis/test_suivi_rh.py) | 14 tests automatiques |

## Règles de calcul

- **Alerte de contrat** = jours entre la date de consultation et la fin du contrat en cours :
  ≤ 30 j → *Urgent* · 31 à 60 j → *À préparer* · 61 à 90 j → *À surveiller* · > 90 j → *RAS* · date dépassée → *Échu, à régulariser* · CDI → *Sans échéance*.
- **Effectif** : une personne sortie le jour J n'est plus comptée à la fin du jour J.
- **Jours d'absence** : jours ouvrables (lundi à vendredi) des absences *approuvées* ou *constatées*, jusqu'à la date de consultation. Les demandes *refusées* ou *en attente* ne sont pas comptées.
- **Stagiaire** : *Terminé* si la fin est passée, *À venir* si le début n'est pas atteint, sinon *En cours*.

## Protection des données (minimisation)

| Donnée | Traitement dans le module |
|---|---|
| Date de naissance, e-mail, genre individuel | Non affichés |
| Salaire, indemnité de stage | Non affichés |
| Motif de sortie | Non affiché (seule la date de sortie apparaît) |
| Maladie, maternité | Regroupées sous « Absence justifiée (motif confidentiel) ». Aucun diagnostic n'existe dans les données |
| Note d'évaluation des stagiaires | Remplacée par l'état : *Réalisée* / *À faire* |

Un test automatique vérifie que ces informations n'apparaissent ni dans les calculs ni dans la page.

## Comment tester le module

Toutes les commandes se lancent depuis la racine du projet.

**1. Lancer les tests automatiques**
```bash
python -m unittest discover -s analysis -v
```
Résultat attendu : `Ran 14 tests … OK`. Les tests couvrent trois aspects :
- **Exemples fictifs miniatures** : 3 collaborateurs de test (T-001, T-002, T-003) dont le résultat se calcule à la main. Par exemple, un CDD qui finit le 31/12/2026 donne 91 jours (*RAS*) au 01/10, 60 jours (*À préparer*) au 01/11, 30 jours (*Urgent*) au 01/12 et *Échu* au 05/01/2027.
- **Minimisation** : aucun champ sensible dans les sorties ni dans la page.
- **Recoupement avec les sources** : les résultats du module sont comparés à des requêtes SQL indépendantes, au script de préparation et aux CSV bruts.

**2. Vérifier à la main dans la page** (situation au 31/10/2026)

| Onglet | Ce que vous devez voir |
|---|---|
| Vue d'ensemble | Effectif actif **27**, dont 26 % en CDD ; **3** contrats ≤ 30 jours ; **1** entre 61 et 90 jours ; entrées / sorties **4 / 3** |
| Échéances | EMP-009 (3 j), EMP-021 (4 j), EMP-007 (30 j) en *Urgent* ; EMP-016 (65 j) en *À surveiller* |
| Absences | 632 jours ouvrables au total ; une demande *En attente* (EMP-014, novembre) |
| Stagiaires | STG-004 et STG-005 en cours, STG-006 à venir |
| Rechercher | Taper « Bukavu » dans le registre : seuls les collaborateurs de Bukavu restent affichés |

**3. Simuler une autre date de consultation**
```bash
python hr_admin/generer_module.py --date 2026-12-01
```
Le script crée `module_suivi_rh_test_2026-12-01.html`, un fichier séparé que Git ignore. Vous devez y voir **3 contrats « Échu, à régulariser »** (EMP-009, EMP-021, EMP-007) : leurs CDD sont terminés et aucun renouvellement n'est saisi. C'est exactement le cas que l'alerte doit révéler au responsable RH.

## Pas encore opérationnel

- **Saisie et modification** : le module ne fait que consulter. Pour ajouter un contrat ou une absence, il faut modifier le générateur de données puis relancer les scripts.
- **Contrôle d'accès** : la page n'a ni mot de passe ni gestion des droits. En situation réelle, il faudrait un espace à accès restreint ou un SIRH.
- **Date du jour automatique** : la situation est calculée à une date fixe (31/10/2026) ou à une date passée en paramètre, pas à la date du jour.
- **Soldes de congés** : non calculés, car la règle d'acquisition des droits (Code du travail de la RDC, convention ou règlement interne) n'est pas encore définie.
- **Jours fériés** : non déduits des jours d'absence.
- **Notifications** : aucun e-mail ni rappel automatique n'est envoyé à l'approche d'une échéance.
- **Export Excel ou PDF** : l'impression du navigateur fonctionne (tous les onglets s'impriment), mais il n'existe pas encore d'export dédié.
- **Plan de classement des dossiers individuels** : prévu dans une prochaine étape.
