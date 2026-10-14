"""
Module de suivi administratif RH : fonctions de calcul.

Chaque fonction reçoit les données ('donnees') et une date de consultation
('jour'), et renvoie uniquement les champs utiles au suivi administratif.

Protection des données (minimisation) :
- jamais affichés : date de naissance, e-mail, salaire, genre individuel,
  motif de sortie, note d'évaluation des stagiaires, indemnités ;
- les motifs de santé (maladie, maternité) sont regroupés sous
  « Absence justifiée (motif confidentiel) ».

DONNÉES FICTIVES - Portfolio personnel, non officiel de Nuru.
"""
import calendar
from datetime import date, timedelta

from commun import DOSSIER_RAW, en_date, lire_csv

SEUILS_ALERTE = (30, 60, 90)

URGENT = "Urgent (≤ 30 jours)"
A_PREPARER = "À préparer (31 à 60 jours)"
A_SURVEILLER = "À surveiller (61 à 90 jours)"
RAS = "RAS (> 90 jours)"
ECHU = "Échu, à régulariser"
SANS_ECHEANCE = "Sans échéance (CDI)"

CONFIDENTIEL = "Absence justifiée (motif confidentiel)"
CATEGORIE_AFFICHEE = {
    "Congé annuel": "Congé annuel",
    "Congé de circonstance": "Congé de circonstance",
    "Absence non justifiée": "Absence non justifiée",
    "Maladie": CONFIDENTIEL,
    "Congé de maternité": CONFIDENTIEL,
}
STATUTS_REALISES = ("Approuvée", "Constatée")


# --- Chargement et outils ----------------------------------------------------
def charger_donnees(dossier=DOSSIER_RAW):
    return {nom: lire_csv(dossier / f"{nom}.csv")
            for nom in ("collaborateurs", "contrats", "absences", "stagiaires")}


def nom_complet(personne):
    return f"{personne['prenom']} {personne['nom']}"


def categorie_affichee(type_absence):
    """Tout type inconnu est masqué par défaut (principe de précaution)."""
    return CATEGORIE_AFFICHEE.get(type_absence, CONFIDENTIEL)


def present_a(collab, jour):
    """En poste à la fin de 'jour' (une sortie le jour J n'est plus comptée)."""
    sortie = en_date(collab["date_sortie"])
    return en_date(collab["date_embauche"]) <= jour and (sortie is None or sortie > jour)


def dernier_contrat(donnees, matricule, jour):
    """Dernier contrat ayant commencé au plus tard à 'jour'."""
    commences = [ct for ct in donnees["contrats"]
                 if ct["matricule"] == matricule and en_date(ct["date_debut"]) <= jour]
    return max(commences, key=lambda ct: ct["date_debut"]) if commences else None


def niveau_alerte(jours_restants):
    """Niveau d'alerte d'un contrat selon le nombre de jours avant son terme."""
    if jours_restants is None:
        return SANS_ECHEANCE
    if jours_restants < 0:
        return ECHU
    if jours_restants <= SEUILS_ALERTE[0]:
        return URGENT
    if jours_restants <= SEUILS_ALERTE[1]:
        return A_PREPARER
    if jours_restants <= SEUILS_ALERTE[2]:
        return A_SURVEILLER
    return RAS


# --- 1. Registre du personnel --------------------------------------------------
def registre_personnel(donnees, jour):
    lignes = []
    for c in donnees["collaborateurs"]:
        if en_date(c["date_embauche"]) > jour:
            continue  # pas encore embauché à cette date
        actif = present_a(c, jour)
        ct = dernier_contrat(donnees, c["matricule"], jour)
        lignes.append({
            "matricule": c["matricule"], "nom": nom_complet(c), "poste": c["poste"],
            "departement": c["departement"], "bureau": c["bureau"],
            "date_embauche": c["date_embauche"],
            "statut": "Actif" if actif else "Sorti",
            "type_contrat": ct["type_contrat"] if actif else "",
            "date_sortie": "" if actif else c["date_sortie"],
        })
    return sorted(lignes, key=lambda l: l["matricule"])


# --- 2. Dates de début et de fin des contrats ---------------------------------
def tableau_contrats(donnees, jour):
    par_matricule = {c["matricule"]: c for c in donnees["collaborateurs"]}
    lignes = []
    for ct in donnees["contrats"]:
        debut, fin = en_date(ct["date_debut"]), en_date(ct["date_fin"])
        if debut > jour:
            statut = "À venir"
        elif fin is not None and fin < jour:
            statut = "Terminé"
        else:
            statut = "En vigueur"
        lignes.append({
            "contrat_id": ct["contrat_id"], "matricule": ct["matricule"],
            "nom": nom_complet(par_matricule[ct["matricule"]]),
            "type_contrat": ct["type_contrat"], "date_debut": ct["date_debut"],
            "date_fin": ct["date_fin"], "motif": ct["motif"], "statut": statut,
        })
    return sorted(lignes, key=lambda l: (l["matricule"], l["date_debut"]))


# --- 3. Échéances des contrats (30 / 60 / 90 jours) ---------------------------
def echeances(donnees, jour):
    lignes = []
    for c in donnees["collaborateurs"]:
        if not present_a(c, jour):
            continue
        ct = dernier_contrat(donnees, c["matricule"], jour)
        fin = en_date(ct["date_fin"])
        jours = None if fin is None else (fin - jour).days
        lignes.append({
            "matricule": c["matricule"], "nom": nom_complet(c), "poste": c["poste"],
            "departement": c["departement"], "type_contrat": ct["type_contrat"],
            "date_fin": ct["date_fin"], "jours_restants": jours,
            "alerte": niveau_alerte(jours),
        })
    # Les plus urgentes d'abord, les CDI à la fin.
    return sorted(lignes, key=lambda l: (l["jours_restants"] is None, l["jours_restants"] or 0))


def compter_alertes(lignes_echeances):
    niveaux = (ECHU, URGENT, A_PREPARER, A_SURVEILLER, RAS, SANS_ECHEANCE)
    return {n: sum(l["alerte"] == n for l in lignes_echeances) for n in niveaux}


# --- 4. Absences et congés ------------------------------------------------------
def liste_absences(donnees):
    par_matricule = {c["matricule"]: c for c in donnees["collaborateurs"]}
    lignes = [{
        "absence_id": a["absence_id"], "matricule": a["matricule"],
        "nom": nom_complet(par_matricule[a["matricule"]]),
        "categorie": categorie_affichee(a["type_absence"]),
        "date_debut": a["date_debut"], "date_fin": a["date_fin"],
        "nb_jours_ouvrables": int(a["nb_jours_ouvrables"]), "statut": a["statut"],
    } for a in donnees["absences"]]
    return sorted(lignes, key=lambda l: (l["date_debut"], l["matricule"]), reverse=True)


def jours_absence_par_mois(donnees, jour):
    """Jours ouvrables d'absence réalisés, du 1er janvier à 'jour', par mois et catégorie."""
    debut_annee = date(jour.year, 1, 1)
    resultat = {}
    for a in donnees["absences"]:
        if a["statut"] not in STATUTS_REALISES:
            continue
        d = max(en_date(a["date_debut"]), debut_annee)
        fin = min(en_date(a["date_fin"]), jour)
        while d <= fin:
            if d.weekday() < 5:
                cle = (d.strftime("%Y-%m"), categorie_affichee(a["type_absence"]))
                resultat[cle] = resultat.get(cle, 0) + 1
            d += timedelta(days=1)
    return resultat


def demandes_en_attente(donnees):
    return [a for a in donnees["absences"] if a["statut"] == "En attente"]


# --- 5. Suivi des stagiaires ----------------------------------------------------
def suivi_stagiaires(donnees, jour):
    par_matricule = {c["matricule"]: c for c in donnees["collaborateurs"]}
    lignes = []
    for s in donnees["stagiaires"]:
        debut, fin = en_date(s["date_debut"]), en_date(s["date_fin"])
        if fin < jour:
            statut = "Terminé"
        elif debut > jour:
            statut = "À venir"
        else:
            statut = "En cours"
        if statut == "Terminé":
            evaluation = "Réalisée" if s["note_evaluation_sur_20"] else "À faire"
        else:
            evaluation = ""
        jours_avant_fin = (fin - jour).days if statut == "En cours" else None
        lignes.append({
            "stagiaire_id": s["stagiaire_id"], "nom": nom_complet(s),
            "filiere": s["filiere"], "niveau": s["niveau"], "departement": s["departement"],
            "encadreur": nom_complet(par_matricule[s["encadreur_matricule"]]),
            "date_debut": s["date_debut"], "date_fin": s["date_fin"],
            "statut": statut, "jours_avant_fin": jours_avant_fin,
            "fin_proche": jours_avant_fin is not None and jours_avant_fin <= SEUILS_ALERTE[0],
            "evaluation_finale": evaluation,
        })
    return lignes


# --- 6. Effectifs ----------------------------------------------------------------
def effectifs_par_departement(donnees, jour):
    """{département: {'CDI': n, 'CDD': n}} pour les collaborateurs en poste."""
    tableau = {}
    for c in donnees["collaborateurs"]:
        if present_a(c, jour):
            type_ct = dernier_contrat(donnees, c["matricule"], jour)["type_contrat"]
            ligne = tableau.setdefault(c["departement"], {"CDI": 0, "CDD": 0})
            ligne[type_ct] += 1
    return dict(sorted(tableau.items(), key=lambda kv: -sum(kv[1].values())))


def effectifs_mensuels(donnees, jour):
    """Registre mensuel du 1er janvier jusqu'au mois de 'jour' inclus."""
    collabs = donnees["collaborateurs"]
    lignes = []
    mois = date(jour.year, 1, 1)
    while mois <= jour:
        dernier = date(mois.year, mois.month, calendar.monthrange(mois.year, mois.month)[1])
        arret = min(dernier, jour)  # mois en cours : arrêté à la date de consultation
        lignes.append({
            "mois": mois.strftime("%Y-%m"),
            "effectif_debut": sum(present_a(c, mois - timedelta(days=1)) for c in collabs),
            "entrees": sum(mois <= en_date(c["date_embauche"]) <= arret for c in collabs),
            "sorties": sum(bool(c["date_sortie"]) and mois <= en_date(c["date_sortie"]) <= arret
                           for c in collabs),
            "effectif_fin": sum(present_a(c, arret) for c in collabs),
        })
        mois = dernier + timedelta(days=1)
    return lignes


# --- Indicateurs clés --------------------------------------------------------------
def indicateurs(donnees, jour):
    eff = effectifs_par_departement(donnees, jour)
    actifs = sum(sum(v.values()) for v in eff.values())
    cdd = sum(v["CDD"] for v in eff.values())
    alertes = compter_alertes(echeances(donnees, jour))
    stg = suivi_stagiaires(donnees, jour)
    mensuel = effectifs_mensuels(donnees, jour)
    return {
        "effectif_actif": actifs,
        "part_cdd_pct": round(100 * cdd / actifs) if actifs else 0,
        "echus": alertes[ECHU],
        "echeances_30": alertes[URGENT],
        "echeances_60": alertes[A_PREPARER],
        "echeances_90": alertes[A_SURVEILLER],
        "jours_absence_realises": sum(jours_absence_par_mois(donnees, jour).values()),
        "demandes_en_attente": len(demandes_en_attente(donnees)),
        "stagiaires_en_cours": sum(s["statut"] == "En cours" for s in stg),
        "stagiaires_a_venir": sum(s["statut"] == "À venir" for s in stg),
        "entrees_annee": sum(m["entrees"] for m in mensuel),
        "sorties_annee": sum(m["sorties"] for m in mensuel),
    }
