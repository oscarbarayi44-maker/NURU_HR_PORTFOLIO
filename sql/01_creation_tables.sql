-- =====================================================================
-- NURU HR DIGITAL PORTFOLIO - Création de la base de données (SQLite)
-- DONNÉES FICTIVES - Portfolio personnel, pas un outil officiel de Nuru.
-- Les dates sont stockées au format texte AAAA-MM-JJ.
-- =====================================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS planning_entretiens;
DROP TABLE IF EXISTS recrutement_etapes;
DROP TABLE IF EXISTS candidatures;
DROP TABLE IF EXISTS offres_emploi;
DROP TABLE IF EXISTS stagiaires;
DROP TABLE IF EXISTS absences;
DROP TABLE IF EXISTS contrats;
DROP TABLE IF EXISTS collaborateurs;

CREATE TABLE collaborateurs (
    matricule           TEXT PRIMARY KEY,               -- ex. EMP-001
    prenom              TEXT NOT NULL,
    nom                 TEXT NOT NULL,
    genre               TEXT NOT NULL CHECK (genre IN ('F', 'M')),
    date_naissance      TEXT NOT NULL,
    departement         TEXT NOT NULL,
    poste               TEXT NOT NULL,
    categorie           TEXT NOT NULL CHECK (categorie IN ('Cadre', 'Agent de maîtrise', 'Exécution')),
    bureau              TEXT NOT NULL,
    date_embauche       TEXT NOT NULL,
    statut              TEXT NOT NULL CHECK (statut IN ('Actif', 'Sorti')),
    date_sortie         TEXT,
    motif_sortie        TEXT,
    email_professionnel TEXT
);

CREATE TABLE contrats (
    contrat_id               TEXT PRIMARY KEY,          -- ex. CTR-0001
    matricule                TEXT NOT NULL REFERENCES collaborateurs (matricule),
    type_contrat             TEXT NOT NULL CHECK (type_contrat IN ('CDI', 'CDD')),
    duree_mois               INTEGER,                   -- vide pour un CDI
    date_debut               TEXT NOT NULL,
    date_fin                 TEXT,                      -- vide pour un CDI en cours
    salaire_brut_mensuel_usd INTEGER NOT NULL,
    motif                    TEXT NOT NULL
);

CREATE TABLE absences (
    absence_id         TEXT PRIMARY KEY,                -- ex. ABS-0001
    matricule          TEXT NOT NULL REFERENCES collaborateurs (matricule),
    type_absence       TEXT NOT NULL,
    date_debut         TEXT NOT NULL,
    date_fin           TEXT NOT NULL,
    nb_jours_ouvrables INTEGER NOT NULL,
    statut             TEXT NOT NULL CHECK (statut IN ('Approuvée', 'En attente', 'Refusée', 'Constatée')),
    CHECK (date_debut <= date_fin)
);

CREATE TABLE stagiaires (
    stagiaire_id            TEXT PRIMARY KEY,           -- ex. STG-001
    prenom                  TEXT NOT NULL,
    nom                     TEXT NOT NULL,
    genre                   TEXT NOT NULL CHECK (genre IN ('F', 'M')),
    etablissement           TEXT NOT NULL,
    filiere                 TEXT NOT NULL,
    niveau                  TEXT NOT NULL,
    departement             TEXT NOT NULL,
    encadreur_matricule     TEXT NOT NULL REFERENCES collaborateurs (matricule),
    date_debut              TEXT NOT NULL,
    date_fin                TEXT NOT NULL,
    indemnite_mensuelle_usd INTEGER,
    note_evaluation_sur_20  INTEGER CHECK (note_evaluation_sur_20 BETWEEN 0 AND 20)
);

CREATE TABLE offres_emploi (
    offre_id         TEXT PRIMARY KEY,                  -- ex. OFF-2026-01
    intitule         TEXT NOT NULL,
    departement      TEXT NOT NULL,
    bureau           TEXT NOT NULL,
    type_contrat     TEXT NOT NULL,
    date_publication TEXT NOT NULL,
    date_cloture     TEXT NOT NULL,
    motif            TEXT
);

-- Aucune caractéristique personnelle sensible (genre, âge, origine…) : inutile au recrutement.
CREATE TABLE candidatures (
    candidature_id               TEXT PRIMARY KEY,      -- ex. CAND-001
    offre_id                     TEXT NOT NULL REFERENCES offres_emploi (offre_id),
    prenom                       TEXT NOT NULL,
    nom                          TEXT NOT NULL,
    date_candidature             TEXT NOT NULL,
    source                       TEXT,
    diplome                      TEXT,
    annees_experience            INTEGER,
    autorisation_references      TEXT CHECK (autorisation_references IN ('Oui', 'Non')),
    date_autorisation_references TEXT,
    date_reponse_candidat        TEXT,
    date_prise_fonction_prevue   TEXT
);

-- Journal des étapes : chaque ligne est une action enregistrée par une personne.
CREATE TABLE recrutement_etapes (
    evenement_id       TEXT PRIMARY KEY,                -- ex. EVT-001
    candidature_id     TEXT NOT NULL REFERENCES candidatures (candidature_id),
    etape              INTEGER NOT NULL CHECK (etape BETWEEN 1 AND 8),
    date               TEXT NOT NULL,
    resultat           TEXT NOT NULL CHECK (resultat IN ('Validée', 'Favorable', 'Défavorable', 'Non retenu(e)', 'Désistement')),
    intervenant        TEXT NOT NULL CHECK (intervenant IN ('Chargé(e) RH', 'Responsable RH', 'Comité de recrutement')),
    note_grille_sur_20 INTEGER CHECK (note_grille_sur_20 BETWEEN 0 AND 20),
    commentaire        TEXT,
    CHECK (etape <> 6 OR intervenant = 'Responsable RH'),
    UNIQUE (candidature_id, etape)
);

CREATE TABLE planning_entretiens (
    creneau_id     TEXT PRIMARY KEY,                    -- ex. PLN-01
    offre_id       TEXT NOT NULL REFERENCES offres_emploi (offre_id),
    candidature_id TEXT NOT NULL REFERENCES candidatures (candidature_id),
    date           TEXT NOT NULL,
    heure_debut    TEXT NOT NULL,
    heure_fin      TEXT NOT NULL,
    epreuve        TEXT,
    lieu           TEXT,
    panel          TEXT,
    statut         TEXT NOT NULL,
    CHECK (heure_debut < heure_fin)
);
