"""
Fonctions et paramètres partagés par les scripts du portfolio.

AVERTISSEMENT : toutes les données du projet sont FICTIVES (synthétiques).
Ce projet est un portfolio personnel ; ce n'est pas un outil officiel de Nuru.
"""
import calendar
import csv
from datetime import date, timedelta
from pathlib import Path

# --- Chemins du projet ------------------------------------------------------
RACINE = Path(__file__).resolve().parent.parent
DOSSIER_RAW = RACINE / "data" / "raw"
DOSSIER_PROCESSED = RACINE / "data" / "processed"

# --- Paramètres fixes -------------------------------------------------------
# Date à laquelle on "photographie" la situation RH (fin du mois d'octobre 2026).
DATE_REFERENCE = date(2026, 10, 31)
DEBUT_ANNEE = date(2026, 1, 1)

# Point-virgule + UTF-8 avec BOM : le fichier s'ouvre correctement dans
# Excel en français (colonnes séparées, accents lisibles).
SEPARATEUR = ";"
ENCODAGE = "utf-8-sig"


# --- Lecture / écriture CSV -------------------------------------------------
def ecrire_csv(chemin, lignes, colonnes):
    """Écrit une liste de dictionnaires dans un fichier CSV."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", newline="", encoding=ENCODAGE) as f:
        writer = csv.DictWriter(f, fieldnames=colonnes, delimiter=SEPARATEUR)
        writer.writeheader()
        for ligne in lignes:
            writer.writerow({c: ("" if ligne.get(c) is None else ligne.get(c)) for c in colonnes})
    print(f"  -> {chemin.relative_to(RACINE)} ({len(lignes)} lignes)")


def lire_csv(chemin):
    """Lit un fichier CSV et renvoie une liste de dictionnaires."""
    with open(chemin, newline="", encoding=ENCODAGE) as f:
        return list(csv.DictReader(f, delimiter=SEPARATEUR))


# --- Dates ------------------------------------------------------------------
def en_date(texte):
    """Convertit 'AAAA-MM-JJ' en date (ou None si la cellule est vide)."""
    return date.fromisoformat(texte) if texte else None


def ajouter_mois(d, nb_mois):
    """Ajoute un nombre de mois à une date (gère les fins de mois)."""
    m = d.month - 1 + nb_mois
    annee = d.year + m // 12
    mois = m % 12 + 1
    jour = min(d.day, calendar.monthrange(annee, mois)[1])
    return date(annee, mois, jour)


def fin_de_contrat(debut, duree_mois):
    """Date de fin d'un contrat de 'duree_mois' mois commençant à 'debut'."""
    return ajouter_mois(debut, duree_mois) - timedelta(days=1)


def jours_ouvrables(debut, fin):
    """Nombre de jours du lundi au vendredi entre deux dates (incluses).
    Simplification : les jours fériés ne sont pas déduits."""
    total = 0
    d = debut
    while d <= fin:
        if d.weekday() < 5:
            total += 1
        d += timedelta(days=1)
    return total


def mois_entre(debut, fin):
    """Nombre de mois complets entre deux dates."""
    mois = (fin.year - debut.year) * 12 + (fin.month - debut.month)
    if fin.day < debut.day:
        mois -= 1
    return mois


def age(date_naissance, a_la_date):
    return mois_entre(date_naissance, a_la_date) // 12
