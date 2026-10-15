"""Application Streamlit : affiche le portfolio RH déjà généré (pages HTML et documents).

Données fictives – Portfolio personnel, non officiel de Nuru.
Lancement local :  streamlit run streamlit_app.py
Aucun indicateur n'est calculé ici : l'application montre les fichiers produits par la chaîne de traitement.
"""
from pathlib import Path

import streamlit as st

RACINE = Path(__file__).resolve().parent
MENTION = "Données fictives – Portfolio personnel, non officiel de Nuru"

MODULES = {
    "Tableau de bord": RACINE / "dashboard" / "tableau_de_bord_rh.html",
    "Suivi administratif RH": RACINE / "hr_admin" / "module_suivi_rh.html",
    "Recrutement": RACINE / "recruitment" / "module_recrutement.html",
}
CAPTURES = [
    ("Tableau de bord RH", RACINE / "assets" / "captures" / "tableau_de_bord_bureau.png"),
    ("Échéances des contrats", RACINE / "assets" / "captures" / "module_rh_echeances.png"),
    ("Suivi du recrutement", RACINE / "assets" / "captures" / "module_recrutement.png"),
]
PROCEDURES = sorted((RACINE / "documents" / "procedures").glob("*.md"))
RAPPORT_MENSUEL = RACINE / "documents" / "rapports" / "rapport_mensuel_rh_2026-10.md"
TELECHARGEMENTS = [
    ("Rapport du projet (PDF)", RACINE / "documents" / "rapports" / "Rapport_projet_NURU_HR_Portfolio.pdf", "application/pdf"),
    ("Rapport du projet (Word)", RACINE / "documents" / "rapports" / "Rapport_projet_NURU_HR_Portfolio.docx",
     "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ("Présentation (PowerPoint)", RACINE / "documents" / "rapports" / "Presentation_NURU_HR_Portfolio.pptx",
     "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
]


def fichier_absent(chemin):
    st.warning(f"Fichier introuvable : `{chemin.relative_to(RACINE)}`. Relancez la chaîne de traitement.")


def titre_procedure(texte, chemin):
    """Titre de niveau 1 du document, sans le préfixe « Procédure : »."""
    for ligne in texte.splitlines():
        if ligne.startswith("# "):
            return ligne[2:].removeprefix("Procédure :").strip().capitalize()
    return chemin.stem


st.set_page_config(page_title="NURU HR Digital Portfolio", page_icon="📁", layout="wide")
st.title("NURU HR Digital Portfolio")
st.warning(MENTION)

onglets = st.tabs(["Accueil", *MODULES, "Documents"])

with onglets[0]:
    st.markdown(
        "Portfolio personnel réalisé dans le cadre d'une candidature à un stage en Ressources Humaines "
        "à Goma (RDC). Il présente des outils de démonstration pour l'administration RH, le suivi des "
        "contrats, des effectifs et des absences, le recrutement, les tableaux de bord et la rédaction "
        "administrative.\n\n"
        "Toutes les personnes et situations sont **fictives**. Ce projet n'a été ni commandé, ni validé, "
        "ni utilisé par Nuru. Les outils organisent l'information : les décisions RH restent humaines."
    )
    colonnes = st.columns(len(CAPTURES))
    for colonne, (legende, chemin) in zip(colonnes, CAPTURES):
        with colonne:
            if chemin.exists():
                st.image(str(chemin), caption=legende, width="stretch")
            else:
                fichier_absent(chemin)

for onglet, (nom, chemin) in zip(onglets[1:], MODULES.items()):
    with onglet:
        if chemin.exists():
            # Pages produites par le projet lui-même (contenu de confiance), hauteur ajustée au contenu
            st.iframe(chemin)
        else:
            fichier_absent(chemin)

with onglets[-1]:
    st.subheader("Rapports à télécharger")
    for libelle, chemin, type_mime in TELECHARGEMENTS:
        if chemin.exists():
            st.download_button(libelle, chemin.read_bytes(), file_name=chemin.name, mime=type_mime)
        else:
            fichier_absent(chemin)

    st.subheader("Rapport mensuel RH – octobre 2026")
    if RAPPORT_MENSUEL.exists():
        with st.expander("Afficher le rapport mensuel"):
            st.markdown(RAPPORT_MENSUEL.read_text(encoding="utf-8-sig"))
    else:
        fichier_absent(RAPPORT_MENSUEL)

    st.subheader("Procédures RH")
    for chemin in PROCEDURES:
        texte = chemin.read_text(encoding="utf-8-sig")
        with st.expander(titre_procedure(texte, chemin)):
            st.markdown(texte)

st.caption(MENTION)
