# Données du projet : dictionnaire des données

> **Données 100 % fictives.** Générées par `analysis/01_generer_donnees_fictives.py`. Portfolio personnel, non officiel de Nuru.

Format commun : CSV, séparateur `;`, encodage UTF-8 (s'ouvre directement dans Excel), dates `AAAA-MM-JJ`.
Date de référence : **31 octobre 2026**.

## `raw/` : données initiales

| Fichier | Lignes | Contenu | Colonnes principales |
|---|---|---|---|
| `collaborateurs.csv` | 30 | Une ligne par collaborateur | matricule, prenom, nom, genre, date_naissance, departement, poste, categorie, bureau, date_embauche, statut (Actif/Sorti), date_sortie, motif_sortie, email_professionnel |
| `contrats.csv` | 55 | Historique de tous les contrats (embauche, renouvellements, passage en CDI) | contrat_id, matricule, type_contrat (CDD/CDI), duree_mois, date_debut, date_fin (vide = CDI en cours), salaire_brut_mensuel_usd, motif |
| `absences.csv` | 98 | Absences et demandes de congés de 2026 | absence_id, matricule, type_absence, date_debut, date_fin, nb_jours_ouvrables, statut (Approuvée / En attente / Refusée / Constatée) |
| `stagiaires.csv` | 6 | Conventions de stage | stagiaire_id, prenom, nom, filiere, niveau, departement, encadreur_matricule, date_debut, date_fin, indemnite_mensuelle_usd, note_evaluation_sur_20 |
| `offres_emploi.csv` | 2 | Offres publiées | offre_id, intitule, departement, bureau, date_publication, date_cloture, motif |
| `candidatures.csv` | 10 | Candidatures, **sans aucune caractéristique personnelle sensible** (pas de genre, d'âge, d'origine…) | candidature_id, offre_id, prenom, nom, date_candidature, source, diplome, annees_experience, autorisation_references, date_autorisation_references, date_reponse_candidat, date_prise_fonction_prevue |
| `recrutement_etapes.csv` | 36 | Journal des étapes : chaque ligne est une action enregistrée par une personne | evenement_id, candidature_id, etape (1 à 8), date, resultat, intervenant (Chargé(e) RH / Comité de recrutement / Responsable RH), note_grille_sur_20 (étapes 2 et 4), commentaire |
| `planning_entretiens.csv` | 7 | Créneaux de test et d'entretien | creneau_id, offre_id, candidature_id, date, heure_debut, heure_fin, epreuve, lieu, panel, statut |

**Processus de recrutement fictif en 8 étapes** : Candidature reçue → Présélection → Convocation au test → Test réalisé → Vérification des références (avec autorisation du candidat) → Décision du responsable RH → Offre et contractualisation → Intégration. Les décisions sont humaines ; les règles sont détaillées dans [recruitment/README.md](../recruitment/README.md).

## `processed/` : données préparées (par `analysis/02_preparer_donnees.py`)

| Fichier | Contenu |
|---|---|
| `collaborateurs_enrichis.csv` | Collaborateurs + âge, ancienneté (mois), contrat actuel et salaire actuel |
| `suivi_echeances_contrats.csv` | Collaborateurs actifs avec jours restants avant la fin du contrat et niveau d'alerte (≤ 30 / 60 / 90 jours) |
| `effectifs_mensuels_2026.csv` | Registre mensuel : effectif de début, entrées, sorties, effectif de fin, répartition par genre et par type de contrat |
| `absences_par_mois_2026.csv` | Jours ouvrables d'absence par mois et par type (absences approuvées ou constatées uniquement) |
| `stagiaires_suivi.csv` | Stagiaires avec encadreur, durée et statut (Terminé / En cours / À venir) |
| `recrutement_entonnoir.csv` | Nombre de candidatures ayant franchi chaque étape (1 à 8), par offre ; un désistement n'est pas compté |

## Simplifications assumées
- Les jours fériés ne sont pas déduits des jours d'absence.
- Les salaires sont des montants fictifs en USD, augmentés de 5 % à chaque nouveau contrat.
- Les établissements des stagiaires sont anonymisés (« Université partenaire (fictive) »).
