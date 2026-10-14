# Instructions de travail pour Claude Code

## Contexte
NURU HR DIGITAL PORTFOLIO est un portfolio personnel de candidature à un stage RH à Goma (RDC).
Il démontre des compétences en administration RH, suivi des contrats, effectifs, absences,
stagiaires, recrutement, tableaux de bord et rédaction administrative.

## Règles impératives
1. **Données fictives uniquement.** Ne jamais introduire de données personnelles réelles (noms, téléphones, adresses, pièces d'identité, salaires réels). Les e-mails utilisent le domaine réservé `exemple-rh.test`.
2. **Projet non officiel.** Ne jamais présenter ce projet comme officiel, commandé ou utilisé par Nuru. Pas de logo ni de charte graphique de Nuru. Tout livrable visible (tableau de bord, rapport, document) porte la mention : *« Données fictives – Portfolio personnel, non officiel de Nuru »*.
3. **Pas d'affirmation juridique non vérifiée.** Pour toute règle du Code du travail de la RDC (durée des CDD, congés, préavis…), signaler qu'elle doit être vérifiée dans le texte en vigueur.
4. **Ne modifier que les fichiers de ce dossier.** Ne jamais toucher aux fichiers personnels hors du projet.
5. **Ne jamais modifier `data/raw/` à la main.** Modifier le générateur, puis relancer la chaîne de scripts.

## Utilisateur
Profil RH débutant en programmation. Répondre en **français**, expliquer chaque fichier créé ou modifié, privilégier des solutions simples (Python standard, CSV, Excel, Markdown, SQLite).

## Conventions des données
- CSV : séparateur `;`, encodage UTF-8 avec BOM (`utf-8-sig`), noms de colonnes en snake_case sans accents.
- Dates au format ISO `AAAA-MM-JJ`.
- Identifiants : `EMP-001`, `CTR-0001`, `ABS-0001`, `STG-001`, `OFF-2026-01`, `CAND-001`.
- Date de référence du projet : **2026-10-31** (définie dans `analysis/commun.py`).
- Une personne sortie le jour J ne compte plus dans l'effectif à la fin du jour J.
- Jours d'absence = jours ouvrables du lundi au vendredi (jours fériés non déduits, simplification documentée).

## Chaîne de traitement
Après toute modification des données ou des scripts, lancer dans l'ordre :
```bash
python analysis/01_generer_donnees_fictives.py
python analysis/02_preparer_donnees.py
python analysis/03_verifier_coherence.py   # doit afficher "Toutes les règles sont respectées."
python sql/charger_base.py
python hr_admin/generer_module.py
python recruitment/generer_module_recrutement.py
python dashboard/generer_tableau_de_bord.py
python documents/generer_rapport_mensuel.py
python portfolio/capturer_ecrans.py
python portfolio/generer_portfolio.py
python portfolio/verifier_portfolio.py      # aucune erreur bloquante
python -m unittest discover -s analysis -v  # 76 tests doivent passer
```
Tableau de bord : aucune valeur écrite en dur ; tout indicateur est calculé depuis data/raw.
Toute nouvelle sortie du module doit respecter la minimisation : pas de date de naissance, e-mail,
salaire, genre individuel, motif de sortie, note de stage, ni motif de santé (catégorie confidentielle).
Ne pas considérer une tâche comme terminée si le contrôle de cohérence échoue.

## Rôle des dossiers
- `data/raw` : données brutes générées · `data/processed` : tables dérivées (ne pas éditer à la main).
- `analysis` : scripts Python (`commun.py` contient les paramètres partagés).
- `sql` : schéma, requêtes et chargement SQLite (`nuru_hr_demo.db` est généré, non versionné).
- `hr_admin`, `recruitment`, `dashboard`, `documents`, `assets` : livrables du portfolio.

## Recrutement : règles non négociables
- Aucune décision de recrutement automatisée : le code ne note pas, ne classe pas et ne sélectionne pas les candidats ; aucune IA de tri.
- Chaque étape du journal (`recrutement_etapes.csv`) est enregistrée par une personne (Chargé(e) RH, Comité de recrutement, Responsable RH) ; l'étape 6 est réservée au Responsable RH.
- Aucune caractéristique personnelle sensible des candidats (genre, âge, origine, santé, situation familiale, photo).
- Références contactées uniquement après autorisation écrite du candidat.
- Les candidats s'affichent par numéro de dossier, jamais triés par note.

## Portfolio (index.html)
- Les informations personnelles viennent uniquement de `portfolio/profil.json` : ne jamais inventer nom, coordonnées, établissements, années ni niveaux de compétence.
- Ne jamais présenter d'expérience professionnelle, de résultat obtenu chez Nuru, de partenariat ni de validation officielle.
- Les niveaux de compétence sont déclarés par l'utilisateur ; la page indique factuellement ce que le projet démontre (R et Power BI : non utilisés).
- Les résultats de tests affichés sont obtenus en exécutant les tests au moment de la génération.
