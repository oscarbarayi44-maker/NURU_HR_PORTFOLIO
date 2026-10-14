"""
Contenu commun du rapport de projet (Word, PDF) et de la présentation (PowerPoint).

Tous les chiffres sont calculés à partir des données sources au moment de la
génération ; les tests et le contrôle de cohérence sont réellement exécutés.
Les informations personnelles viennent de portfolio/profil.json.

DONNÉES FICTIVES - Portfolio personnel, indépendant de Nuru.
"""
import json
import sys
from datetime import date
from pathlib import Path

RAPPORTS = Path(__file__).resolve().parent
RACINE = RAPPORTS.parent.parent
for dossier in ("analysis", "portfolio"):
    if str(RACINE / dossier) not in sys.path:
        sys.path.insert(0, str(RACINE / dossier))

import insights as ins  # noqa: E402
import recrutement as rc  # noqa: E402
import suivi_rh as rh  # noqa: E402
import tableau_de_bord as tb  # noqa: E402
from commun import DATE_REFERENCE, DOSSIER_RAW, lire_csv  # noqa: E402

# Palette commune (bleu nuit dominant, orange en accent ; séries de graphiques validées
# pour la lisibilité, y compris en cas de daltonisme).
COULEURS = {
    "nuit": "14213D", "nuit_2": "22335A", "orange": "EB6834", "bleu": "2A78D6",
    "encre": "1F2933", "gris": "5B6573", "clair": "F3F5F8", "trait": "D9DEE6", "blanc": "FFFFFF",
}
CAPTURES = RACINE / "assets" / "captures"
FIGURES = RAPPORTS / "figures"
MENTION = ("Projet personnel de démonstration réalisé sur des données entièrement fictives. "
           "Indépendant de Nuru : ni commandé, ni validé, ni utilisé par Nuru, sans partenariat.")
MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
           "septembre", "octobre", "novembre", "décembre"]


def date_fr(d):
    return f"{d.day} {MOIS_FR[d.month - 1]} {d.year}"


def nb(x):
    """Entier avec espace insécable comme séparateur de milliers (6 053)."""
    return f"{x:,}".replace(",", " ")


def collecter(executer_verifications=True):
    """Rassemble toutes les données du rapport. Les verifications lancent les tests (≈ quelques secondes)."""
    jour = DATE_REFERENCE
    profil = json.loads((RACINE / "portfolio" / "profil.json").read_text(encoding="utf-8"))
    d_rh, d_rec = rh.charger_donnees(), rc.charger_donnees()
    tdb = tb.donnees_tableau_de_bord(jour)
    ind_rh = rh.indicateurs(d_rh, jour)
    ind_rec = rc.indicateurs(d_rec, jour)
    volumes = {nom: len(lire_csv(DOSSIER_RAW / f"{nom}.csv")) for nom in
               ("collaborateurs", "contrats", "absences", "stagiaires", "offres_emploi",
                "candidatures", "recrutement_etapes", "planning_entretiens")}
    if executer_verifications:
        import generer_portfolio as gp
        tests = gp.executer_tests()
        controle = gp.executer_controle_coherence()
        sql = gp.compter_sql()
    else:
        tests, controle, sql = (0, 0), (0, 0), (0, 0)
    return {
        "jour": jour, "date_document": date.today(), "profil": profil,
        "nom": profil["nom_complet"] or "[Votre nom à compléter]",
        "tdb": tdb, "ind_rh": ind_rh, "ind_rec": ind_rec, "volumes": volumes,
        "mensuel": rh.effectifs_mensuels(d_rh, jour),
        "entonnoir": {o: rc.entonnoir(d_rec, jour, o) for o in tdb["offres"]},
        "etats_rec": rc.tous_les_etats(d_rec, jour),
        "insights": ins.calculer_insights(jour),
        "tests": tests, "controle": controle, "sql": sql,
    }


# --- Textes partagés ------------------------------------------------------------------------
COMPETENCES_VISEES = [
    ("Organiser et archiver des dossiers RH", "Procédure d'archivage : plan de classement, nommage, sécurité"),
    ("Suivre les contrats et leurs échéances", "Module de suivi : alertes à 90, 60 et 30 jours"),
    ("Tenir un registre mensuel des effectifs", "Registre calculé : début, entrées, sorties, fin de mois"),
    ("Suivre absences, congés et stagiaires", "Registre unique, catégorie confidentielle pour la santé"),
    ("Organiser un processus de recrutement", "Module en 8 étapes, décisions humaines tracées"),
    ("Produire des tableaux de bord RH", "Tableau de bord : indicateurs, graphiques, insights, export CSV"),
    ("Rédiger procédures et rapports", "3 procédures, rapport mensuel généré, modèles de documents"),
]

PROBLEMES = [
    ("Dossiers difficiles à retrouver", "Plan de classement et règles de nommage communes."),
    ("Contrats échus sans décision préparée", "Alertes graduées ; la décision reste au responsable RH."),
    ("Effectifs mal connus d'un mois à l'autre", "Registre mensuel équilibré automatiquement."),
    ("Suivi dispersé des absences et stagiaires", "Un registre unique et confidentiel."),
    ("Recrutement peu traçable", "Prochaine action, responsable et échéance pour chaque dossier."),
    ("Pas de vue d'ensemble pour piloter", "Un tableau de bord à jour en une commande."),
]

OUTILS = [
    ("Python", "Génération des données, calculs, modules, tests automatisés (avec l'assistance de Claude Code)."),
    ("SQL (SQLite)", "Base relationnelle avec contraintes et requêtes de consultation et de recoupement."),
    ("CSV / Excel", "Registres lisibles directement dans Excel en français ; exports CSV."),
    ("HTML / CSS", "Pages de consultation autonomes, utilisables sans Internet, adaptées au téléphone."),
    ("Markdown", "Procédures, rapport mensuel et documentation."),
    ("R et Power BI", "Non utilisés dans ce projet (données préparées prêtes pour Power BI)."),
]

IA_RESPONSABLE = [
    ("Assistance déclarée", "Le projet a été construit avec Claude Code. Les propositions de l'IA ont été exécutées et "
                            "contrôlées par des tests ; je reste responsable du contenu."),
    ("Aucune décision automatisée", "Le recrutement n'est ni noté, ni classé, ni trié par l'outil. Chaque étape est "
                                    "enregistrée par une personne ; la décision appartient au responsable RH."),
    ("Données fictives et minimisation", "Aucune donnée réelle. Les écrans de suivi n'affichent ni date de naissance, "
                                         "ni salaire, ni motif de santé ; les insights sont agrégés."),
]

LIMITES = [
    "Outils de consultation : la saisie se fait dans les scripts, pas dans le navigateur.",
    "Pas de mot de passe ni de gestion des droits : un SIRH ou un espace à accès restreint serait nécessaire.",
    "Soldes de congés non calculés (règle d'acquisition à définir) ; jours fériés non déduits.",
    "Aucune notification ni envoi automatique de courriels.",
    "Règles du Code du travail de la RDC à faire vérifier par une personne compétente.",
    "Non testés : impression PDF depuis le navigateur, navigateurs autres qu'Edge, lecteurs d'écran.",
]

PROCHAINES_ETAPES = [
    "Ajouter une saisie sécurisée (formulaire) et un historique des modifications.",
    "Calculer les soldes de congés une fois la règle interne validée.",
    "Construire une version Power BI à partir des tables déjà préparées.",
    "Faire relire les procédures par un professionnel RH et les adapter au règlement intérieur.",
]

APPORTS_STAGE = [
    "Rigueur administrative : registres tenus à jour, contrôlés et traçables.",
    "Anticipation : repérer les échéances avant qu'elles ne deviennent des urgences.",
    "Sens du service : préparer des dossiers clairs pour faciliter les décisions du responsable RH.",
    "Usage responsable du numérique et de l'IA, au service de la confidentialité.",
    "Envie d'apprendre les pratiques réelles de l'équipe RH et de m'y adapter.",
]
