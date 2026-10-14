"""
Étape 2 - Transforme les données brutes (data/raw) en tables prêtes à
l'analyse et aux tableaux de bord (data/processed).

AVERTISSEMENT : toutes les données sont FICTIVES. Ce projet est un portfolio
personnel ; ce n'est pas un outil officiel de Nuru.

Utilisation (depuis la racine du projet) :
    python analysis/02_preparer_donnees.py
"""
import calendar
from datetime import date, timedelta

from commun import (DATE_REFERENCE, DEBUT_ANNEE, DOSSIER_PROCESSED, DOSSIER_RAW,
                    age, ecrire_csv, en_date, lire_csv, mois_entre)

collaborateurs = lire_csv(DOSSIER_RAW / "collaborateurs.csv")
contrats = lire_csv(DOSSIER_RAW / "contrats.csv")
absences = lire_csv(DOSSIER_RAW / "absences.csv")
stagiaires = lire_csv(DOSSIER_RAW / "stagiaires.csv")
offres = lire_csv(DOSSIER_RAW / "offres_emploi.csv")
candidatures = lire_csv(DOSSIER_RAW / "candidatures.csv")

par_matricule = {c["matricule"]: c for c in collaborateurs}


def contrat_a_la_date(matricule, jour):
    """Contrat en vigueur pour un collaborateur à une date donnée."""
    for ct in contrats:
        if ct["matricule"] == matricule:
            fin = en_date(ct["date_fin"])
            if en_date(ct["date_debut"]) <= jour and (fin is None or jour <= fin):
                return ct
    return None


def present_apres(c, jour):
    """Le collaborateur fait-il partie de l'effectif à la fin de 'jour' ?
    Convention : une personne sortie le jour J ne compte plus à la fin de J."""
    sortie = en_date(c["date_sortie"])
    return en_date(c["date_embauche"]) <= jour and (sortie is None or sortie > jour)


print("Préparation des données dans data/processed/ :")

# 1. Collaborateurs enrichis ---------------------------------------------------
enrichis = []
for c in collaborateurs:
    sortie = en_date(c["date_sortie"])
    jour_calcul = sortie or DATE_REFERENCE
    ct = contrat_a_la_date(c["matricule"], jour_calcul)
    enrichis.append({
        **{k: c[k] for k in ("matricule", "prenom", "nom", "genre", "departement",
                             "poste", "categorie", "bureau", "date_embauche", "statut",
                             "date_sortie", "motif_sortie")},
        "age": age(en_date(c["date_naissance"]), jour_calcul),
        "anciennete_mois": mois_entre(en_date(c["date_embauche"]), jour_calcul),
        "type_contrat_actuel": ct["type_contrat"],
        "date_fin_contrat_actuel": ct["date_fin"],
        "salaire_brut_mensuel_usd": ct["salaire_brut_mensuel_usd"],
    })
ecrire_csv(DOSSIER_PROCESSED / "collaborateurs_enrichis.csv", enrichis, list(enrichis[0].keys()))

# 2. Suivi des échéances de contrats (collaborateurs actifs) ----------------
echeances = []
for c in enrichis:
    if c["statut"] != "Actif":
        continue
    fin = en_date(c["date_fin_contrat_actuel"])
    if fin is None:
        jours, alerte = "", "Sans échéance (CDI)"
    else:
        jours = (fin - DATE_REFERENCE).days
        if jours <= 30:
            alerte = "Urgent (≤ 30 jours)"
        elif jours <= 60:
            alerte = "À préparer (31 à 60 jours)"
        elif jours <= 90:
            alerte = "À surveiller (61 à 90 jours)"
        else:
            alerte = "RAS (> 90 jours)"
    echeances.append({
        "matricule": c["matricule"], "nom_complet": f"{c['prenom']} {c['nom']}",
        "departement": c["departement"], "poste": c["poste"], "bureau": c["bureau"],
        "type_contrat": c["type_contrat_actuel"], "date_fin_contrat": c["date_fin_contrat_actuel"],
        "jours_restants": jours, "niveau_alerte": alerte,
    })
echeances.sort(key=lambda e: (e["jours_restants"] == "", e["jours_restants"] or 0))
ecrire_csv(DOSSIER_PROCESSED / "suivi_echeances_contrats.csv", echeances, list(echeances[0].keys()))

# 3. Registre mensuel des effectifs 2026 --------------------------------------
effectifs = []
mois = DEBUT_ANNEE
while mois <= DATE_REFERENCE:
    dernier_jour = date(mois.year, mois.month, calendar.monthrange(mois.year, mois.month)[1])
    veille = mois - timedelta(days=1)
    presents_fin = [c for c in collaborateurs if present_apres(c, dernier_jour)]
    types_fin = [contrat_a_la_date(c["matricule"], dernier_jour)["type_contrat"] for c in presents_fin]
    effectifs.append({
        "mois": mois.strftime("%Y-%m"),
        "effectif_debut": sum(present_apres(c, veille) for c in collaborateurs),
        "entrees": sum(mois <= en_date(c["date_embauche"]) <= dernier_jour for c in collaborateurs),
        "sorties": sum(c["date_sortie"] != "" and mois <= en_date(c["date_sortie"]) <= dernier_jour
                       for c in collaborateurs),
        "effectif_fin": len(presents_fin),
        "dont_femmes": sum(c["genre"] == "F" for c in presents_fin),
        "dont_hommes": sum(c["genre"] == "M" for c in presents_fin),
        "dont_cdi": types_fin.count("CDI"),
        "dont_cdd": types_fin.count("CDD"),
    })
    mois = dernier_jour + timedelta(days=1)
ecrire_csv(DOSSIER_PROCESSED / "effectifs_mensuels_2026.csv", effectifs, list(effectifs[0].keys()))

# 4. Jours d'absence par mois et par type (absences effectives uniquement) ---
compteur = {}
for a in absences:
    if a["statut"] not in ("Approuvée", "Constatée"):
        continue  # une demande refusée ou en attente n'est pas une absence réalisée
    d, fin = en_date(a["date_debut"]), min(en_date(a["date_fin"]), DATE_REFERENCE)
    while d <= fin:
        if d.weekday() < 5:
            cle = (d.strftime("%Y-%m"), a["type_absence"])
            compteur[cle] = compteur.get(cle, 0) + 1
        d += timedelta(days=1)
absences_mois = [{"mois": m, "type_absence": t, "jours_ouvrables": n}
                 for (m, t), n in sorted(compteur.items())]
ecrire_csv(DOSSIER_PROCESSED / "absences_par_mois_2026.csv", absences_mois,
           ["mois", "type_absence", "jours_ouvrables"])

# 5. Suivi des stagiaires ------------------------------------------------------
suivi_stg = []
for s in stagiaires:
    debut, fin = en_date(s["date_debut"]), en_date(s["date_fin"])
    if fin < DATE_REFERENCE:
        statut = "Terminé"
    elif debut > DATE_REFERENCE:
        statut = "À venir"
    else:
        statut = "En cours"
    enc = par_matricule[s["encadreur_matricule"]]
    suivi_stg.append({
        "stagiaire_id": s["stagiaire_id"], "nom_complet": f"{s['prenom']} {s['nom']}",
        "genre": s["genre"], "filiere": s["filiere"], "niveau": s["niveau"],
        "departement": s["departement"],
        "encadreur": f"{enc['prenom']} {enc['nom']} ({enc['matricule']})",
        "date_debut": s["date_debut"], "date_fin": s["date_fin"],
        "duree_mois": mois_entre(debut, fin + timedelta(days=1)),
        "statut": statut, "note_evaluation_sur_20": s["note_evaluation_sur_20"],
    })
ecrire_csv(DOSSIER_PROCESSED / "stagiaires_suivi.csv", suivi_stg, list(suivi_stg[0].keys()))

# 6. Entonnoir de recrutement ----------------------------------------------------
ETAPES = ["Candidature reçue", "Présélection", "Convocation au test", "Test réalisé",
          "Vérification des références", "Décision du responsable RH", "Offre et contractualisation",
          "Intégration"]
journal = lire_csv(DOSSIER_RAW / "recrutement_etapes.csv")
# Étape franchie = étape enregistrée avec un résultat autre que « Désistement ».
franchies = {(e["candidature_id"], int(e["etape"])) for e in journal
             if e["resultat"] != "Désistement" and en_date(e["date"]) <= DATE_REFERENCE}
entonnoir = []
for o in offres:
    cands = [c["candidature_id"] for c in candidatures if c["offre_id"] == o["offre_id"]]
    for i, etape in enumerate(ETAPES, start=1):
        nb = sum((cid, i) in franchies for cid in cands)
        entonnoir.append({
            "offre_id": o["offre_id"], "intitule": o["intitule"], "etape": etape,
            "ordre_etape": i, "nb_candidats": nb,
            "taux_par_rapport_aux_candidatures_pct": round(100 * nb / len(cands)),
        })
ecrire_csv(DOSSIER_PROCESSED / "recrutement_entonnoir.csv", entonnoir, list(entonnoir[0].keys()))
print("Terminé.")
