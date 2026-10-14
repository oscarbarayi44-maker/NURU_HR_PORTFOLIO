-- =====================================================================
-- NURU HR DIGITAL PORTFOLIO - Requêtes de consultation (SQLite)
-- DONNÉES FICTIVES - Date de référence du projet : 2026-10-31
-- =====================================================================

-- 1. Effectif actif par département et par genre
SELECT departement,
       COUNT(*)                                  AS effectif,
       SUM(CASE WHEN genre = 'F' THEN 1 ELSE 0 END) AS femmes,
       SUM(CASE WHEN genre = 'M' THEN 1 ELSE 0 END) AS hommes
FROM collaborateurs
WHERE statut = 'Actif'
GROUP BY departement
ORDER BY effectif DESC;

-- 2. CDD arrivant à échéance dans les 90 jours (alerte de renouvellement)
SELECT c.matricule,
       c.prenom || ' ' || c.nom                                   AS collaborateur,
       c.poste,
       ct.date_fin,
       CAST(julianday(ct.date_fin) - julianday('2026-10-31') AS INTEGER) AS jours_restants
FROM contrats ct
JOIN collaborateurs c ON c.matricule = ct.matricule
WHERE c.statut = 'Actif'
  AND ct.type_contrat = 'CDD'
  AND ct.date_fin BETWEEN '2026-10-31' AND date('2026-10-31', '+90 days')
ORDER BY ct.date_fin;

-- 3. Jours d'absence 2026 par type (absences réalisées uniquement)
SELECT type_absence,
       COUNT(*)                AS nb_absences,
       SUM(nb_jours_ouvrables) AS total_jours
FROM absences
WHERE statut IN ('Approuvée', 'Constatée')
  AND date_debut <= '2026-10-31'
GROUP BY type_absence
ORDER BY total_jours DESC;

-- 4. Stagiaires en cours ou à venir, avec leur encadreur
SELECT s.stagiaire_id,
       s.prenom || ' ' || s.nom AS stagiaire,
       s.departement,
       c.prenom || ' ' || c.nom AS encadreur,
       s.date_debut,
       s.date_fin
FROM stagiaires s
JOIN collaborateurs c ON c.matricule = s.encadreur_matricule
WHERE s.date_fin >= '2026-10-31'
ORDER BY s.date_debut;

-- 5. Dernière étape enregistrée pour chaque candidature (ordre fixe, aucun classement)
SELECT ca.candidature_id,
       ca.prenom || ' ' || ca.nom AS candidat,
       ca.offre_id,
       e.etape,
       e.resultat,
       e.date                     AS date_derniere_action,
       e.intervenant
FROM candidatures ca
JOIN recrutement_etapes e ON e.candidature_id = ca.candidature_id
WHERE e.etape = (SELECT MAX(etape) FROM recrutement_etapes x WHERE x.candidature_id = ca.candidature_id)
ORDER BY ca.candidature_id;

-- 6. Masse salariale mensuelle brute (fictive) des actifs par département
SELECT c.departement,
       SUM(ct.salaire_brut_mensuel_usd) AS masse_salariale_usd
FROM collaborateurs c
JOIN contrats ct ON ct.matricule = c.matricule
WHERE c.statut = 'Actif'
  AND ct.date_debut <= '2026-10-31'
  AND (ct.date_fin IS NULL OR ct.date_fin >= '2026-10-31')
GROUP BY c.departement
ORDER BY masse_salariale_usd DESC;
