# recruitment : module de suivi du recrutement

> **Données fictives. Portfolio personnel, ce n'est pas un outil officiel de Nuru.**

## Principe : toutes les décisions restent humaines

- Le module **ne note pas, ne classe pas et ne sélectionne pas** les candidats. Il n'utilise **aucune IA**.
- Chaque étape est **enregistrée par une personne** : chargé(e) RH, comité de recrutement ou responsable RH. Un intervenant comme « Système automatique » est refusé.
- La **décision (étape 6) appartient exclusivement au responsable RH**. Une non-sélection est décidée par le comité ou par le responsable RH.
- **Aucune caractéristique personnelle sensible** (genre, âge, origine, santé, situation familiale, photo) n'est collectée.
- Les candidats s'affichent toujours dans l'ordre de leur numéro de dossier, jamais par note.
- Le module se limite à **contrôler le respect du processus** et à **rappeler la prochaine tâche administrative**.

## Le processus en 8 étapes

| Étape | Résultats possibles | Enregistrée par |
|---|---|---|
| 1. Candidature reçue | Validée | Chargé(e) RH |
| 2. Présélection | Validée / Non retenu(e) / Désistement | Comité (grille d'analyse du CV obligatoire) |
| 3. Convocation au test | Validée / Désistement | Chargé(e) RH (créneau dans le planning, préavis ≥ 5 jours) |
| 4. Test réalisé | Validée / Non retenu(e) / Désistement | Comité (grille de test et d'entretien obligatoire) |
| 5. Vérification des références | Validée / Non retenu(e) / Désistement | Chargé(e) RH, **seulement après l'autorisation écrite du candidat** |
| 6. Décision du responsable RH | Favorable / Défavorable / Désistement | **Responsable RH uniquement** |
| 7. Offre et contractualisation | Validée / Désistement | Responsable RH |
| 8. Intégration | Validée / Désistement | Chargé(e) RH |

Les étapes se suivent sans saut. Un dossier clôturé (non retenu ou désistement) n'évolue plus.

## Contenu du module

| Fichier | Rôle |
|---|---|
| `module_recrutement.html` | Page de consultation en 7 onglets : Vue d'ensemble, Candidatures (statut, prochaine action, responsable, échéance, alerte), Dates importantes, Historique, Planning des entretiens, Modèles, Processus |
| `planning_entretiens.md` | Exemple de planning des tests et entretiens (7 créneaux, Goma et Bukavu) |
| `convocations/convocation_CAND-xxx.txt` | Courriels de convocation remplis automatiquement à partir du modèle |
| `checklist_integration_CAND-001.md` | Checklist d'intégration datée pour la personne recrutée |
| [`../documents/modeles_courriers/courriel_convocation_test.txt`](../documents/modeles_courriers/courriel_convocation_test.txt) | Modèle de courriel, avec des champs `{prenom}`, `{date_longue}`… |
| `../documents/modeles_courriers/checklist_integration_modele.md` | Modèle vierge de checklist (repères J-10 à J+30) |
| [`generer_module_recrutement.py`](generer_module_recrutement.py) | Génère la page et les documents |
| [`../analysis/recrutement.py`](../analysis/recrutement.py) | Règles du processus, statuts, délais, modèles |
| [`../analysis/test_recrutement.py`](../analysis/test_recrutement.py) | 29 tests automatiques |

Données sources (dans `data/raw/`) : `candidatures.csv`, `recrutement_etapes.csv` (journal des étapes), `planning_entretiens.csv`, `offres_emploi.csv`.

## Règles de calcul

- **Statut** : *En cours*, *Non retenu(e)*, *Désistement*, *Recruté(e), intégration à venir* (contrat signé) ou *Intégré(e)*.
- **Prochaine action** : tâche administrative déduite de la dernière étape, par exemple « Envoyer la convocation » ou « Transmettre le dossier au responsable RH ». Elle n'indique jamais quel candidat retenir.
- **Échéance** : date du test planifié, date de prise de fonction, ou 7 jours après une décision négative pour envoyer la réponse écrite.
- **Alertes** :
  - *Relancer* : dossier en cours sans action depuis plus de 14 jours ;
  - *Échéance dépassée* : date d'échéance passée sans nouvelle action enregistrée.
- **Délai moyen jusqu'à la décision RH** : jours entre la candidature et l'étape 6.
- **Checklist d'intégration** : dates calculées à partir de la prise de fonction (J). Une date qui tombe un week-end est ramenée au vendredi précédent (avant l'arrivée) ou au lundi suivant (après l'arrivée).
- **Confirmation de présence** : demandée 2 jours ouvrables avant le test.

## Comment utiliser le module

Toutes les commandes se lancent depuis la racine du projet.

**1. Générer la page et les documents**
```bash
python recruitment/generer_module_recrutement.py
```
Le script contrôle d'abord les données. Si une transition est invalide (saut d'étape, décision sans responsable RH, références sans autorisation…), il **refuse de générer** le module et liste les problèmes.

**2. Consulter** : ouvrir `recruitment/module_recrutement.html` dans un navigateur. Un onglet peut s'ouvrir directement par l'adresse, par exemple `module_recrutement.html#candidatures`.

**3. Faire avancer un dossier** : ajouter une ligne au journal des étapes dans `analysis/01_generer_donnees_fictives.py` (liste `JOURNAL`), en indiquant l'étape suivante, la date, le résultat décidé par la personne et l'intervenant. Relancer ensuite la chaîne de scripts (voir le README principal).

**4. Simuler une autre date**
```bash
python recruitment/generer_module_recrutement.py --date 2026-11-10
```
Le fichier de test `module_recrutement_test_2026-11-10.html` est ignoré par Git. Au 10/11, aucune nouvelle action n'est enregistrée, ce qui fait apparaître 5 alertes *Échéance dépassée* :
- CAND-006, 007 et 008 : les tests des 4 et 5 novembre sont passés, mais sans résultat enregistré ;
- CAND-001 : la prise de fonction du 02/11 n'est pas encore enregistrée à l'étape 8 ;
- CAND-005 : la réponse écrite n'est toujours pas envoyée.

## Comment tester

```bash
python -m unittest discover -s analysis -v
```

| Groupe de tests | Ce qui est vérifié |
|---|---|
| Transitions | Parcours complet accepté. Refus : saut d'étape, dossier clôturé, intervenant automatique (« IA », « Système automatique »), décision hors responsable RH, références sans autorisation ou avec autorisation tardive, grille manquante, résultat impossible, date antérieure |
| Prochaines actions | Une action administrative par étape, sans aucun mot de décision (« rejeter », « retenir le », « classer »…), avec les échéances et alertes attendues |
| Calculs | Indicateurs recalculés à la main, statuts au 31/10, état à une date antérieure, ordre fixe, entonnoir recoupé avec SQL et avec le script de préparation |
| Modèles | Courriel sans champ vide et avec les bonnes dates, courriel incomplet refusé, checklist datée sur des jours ouvrables, planning complet |
| Garde-fous | Aucune caractéristique sensible dans les données, tous les intervenants sont humains |

**Exemples à vérifier dans la page (au 31/10/2026)**

| Dossier | Ce que vous devez voir |
|---|---|
| CAND-001 | Étape 7/8, *Recruté(e), intégration à venir*, préparer l'intégration avant le 02/11/2026 |
| CAND-005 | *Non retenu(e)*, réponse écrite non envoyée : alerte *Échéance dépassée de 46 jours* |
| CAND-006, 007, 008 | Étape 3/8, test et entretien les 4 et 5 novembre (comité de recrutement) |
| CAND-010 | *Désistement*, créneau du 05/11 annulé dans le planning |
| Vue d'ensemble | 10 candidatures, 3 en cours, 5 actions à mener, 1 alerte, 1 poste pourvu, délai moyen de 38 jours |

## Pas encore opérationnel

- **Saisie dans la page** : on ne peut pas enregistrer une étape depuis le navigateur. Le journal se modifie dans le générateur de données.
- **Envoi des courriels** : les convocations sont générées en texte, mais aucun courriel n'est envoyé.
- **Autres modèles** : réponse négative, offre d'emploi, courriel de bienvenue et grilles d'évaluation détaillées restent à rédiger.
- **Suivi de la checklist** : les cases ne s'enregistrent pas ; c'est un document à imprimer ou à cocher à la main.
- **Durée de conservation des données des candidats non retenus** : règle à définir, puis suppression à prévoir.
- **Contrôle d'accès** : la page n'a pas de mot de passe et doit être conservée sur un espace à accès restreint.
