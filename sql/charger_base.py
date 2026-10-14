"""
Crée la base SQLite sql/nuru_hr_demo.db à partir des CSV de data/raw,
puis exécute les requêtes de sql/02_requetes_consultation.sql.

DONNÉES FICTIVES - Portfolio personnel, pas un outil officiel de Nuru.

Utilisation (depuis la racine du projet) :
    python sql/charger_base.py
"""
import csv
import sqlite3
from pathlib import Path

DOSSIER_SQL = Path(__file__).resolve().parent
DOSSIER_RAW = DOSSIER_SQL.parent / "data" / "raw"
BASE = DOSSIER_SQL / "nuru_hr_demo.db"

# Ordre de chargement : les tables référencées d'abord (clés étrangères).
TABLES = ["collaborateurs", "contrats", "absences", "stagiaires", "offres_emploi", "candidatures",
          "recrutement_etapes", "planning_entretiens"]

connexion = sqlite3.connect(BASE)
connexion.executescript((DOSSIER_SQL / "01_creation_tables.sql").read_text(encoding="utf-8"))

for table in TABLES:
    with open(DOSSIER_RAW / f"{table}.csv", newline="", encoding="utf-8-sig") as f:
        lignes = list(csv.DictReader(f, delimiter=";"))
    colonnes = list(lignes[0].keys())
    requete = f"INSERT INTO {table} ({', '.join(colonnes)}) VALUES ({', '.join('?' * len(colonnes))})"
    # Une cellule vide devient NULL dans la base.
    connexion.executemany(requete, [[l[c] or None for c in colonnes] for l in lignes])
    print(f"{table} : {len(lignes)} lignes chargées")
connexion.commit()

# Exécution des requêtes de consultation, une par une.
texte = (DOSSIER_SQL / "02_requetes_consultation.sql").read_text(encoding="utf-8")
for bloc in texte.split(";"):
    titre = [l for l in bloc.splitlines() if l.startswith("-- ") and l[3:4].isdigit()]
    requete = "\n".join(l for l in bloc.splitlines() if not l.startswith("--")).strip()
    if not requete:
        continue
    curseur = connexion.execute(requete)
    print("\n" + (titre[0][3:] if titre else "Requête"))
    print(" | ".join(d[0] for d in curseur.description))
    for ligne in curseur.fetchall():
        print(" | ".join("" if v is None else str(v) for v in ligne))

connexion.close()
print(f"\nBase créée : {BASE.name}")
