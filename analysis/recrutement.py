"""
Module de suivi du recrutement : règles du processus, statuts, prochaines actions,
délais, planning et modèles de documents.

PRINCIPE : ce module ne prend AUCUNE décision de recrutement.
- Il n'attribue aucun score, ne classe pas les candidats et n'utilise aucune IA.
- Chaque étape est enregistrée par une personne (Chargé(e) RH, Comité de
  recrutement, Responsable RH). Le module vérifie seulement que l'enregistrement
  respecte le processus, puis indique la prochaine tâche ADMINISTRATIVE.
- Aucune caractéristique personnelle sensible (genre, âge, origine, santé,
  situation familiale…) n'est collectée ni utilisée.

DONNÉES FICTIVES - Portfolio personnel, non officiel de Nuru.
"""
from datetime import date, timedelta

from commun import DOSSIER_RAW, RACINE, en_date, lire_csv

ETAPES = {
    1: "Candidature reçue",
    2: "Présélection",
    3: "Convocation au test",
    4: "Test réalisé",
    5: "Vérification des références",
    6: "Décision du responsable RH",
    7: "Offre et contractualisation",
    8: "Intégration",
}

CRH, RRH, COMITE = "Chargé(e) RH", "Responsable RH", "Comité de recrutement"
INTERVENANTS_HUMAINS = {CRH, RRH, COMITE}

VALIDEE, FAVORABLE, DEFAVORABLE = "Validée", "Favorable", "Défavorable"
NON_RETENU, DESISTEMENT = "Non retenu(e)", "Désistement"
POURSUITE = {VALIDEE, FAVORABLE}          # le dossier passe à l'étape suivante
NEGATIFS = {NON_RETENU, DEFAVORABLE}      # le dossier est clôturé par une décision humaine

RESULTATS_AUTORISES = {
    1: {VALIDEE},
    2: {VALIDEE, NON_RETENU, DESISTEMENT},
    3: {VALIDEE, DESISTEMENT},
    4: {VALIDEE, NON_RETENU, DESISTEMENT},
    5: {VALIDEE, NON_RETENU, DESISTEMENT},
    6: {FAVORABLE, DEFAVORABLE, DESISTEMENT},
    7: {VALIDEE, DESISTEMENT},
    8: {VALIDEE, DESISTEMENT},
}
ETAPES_AVEC_GRILLE = {2, 4}   # présélection et test : grille d'évaluation remplie par le comité

DELAI_RELANCE_JOURS = 14        # dossier en cours sans action depuis plus de 14 jours
DELAI_REPONSE_JOURS = 7         # réponse écrite attendue dans les 7 jours après une décision négative
PREAVIS_CONVOCATION_JOURS = 5   # délai minimal entre la convocation et le test

STATUT_EN_COURS = "En cours"
STATUT_NON_RETENU = "Non retenu(e)"
STATUT_DESISTEMENT = "Désistement"
STATUT_RECRUTE = "Recruté(e), intégration à venir"
STATUT_INTEGRE = "Intégré(e)"

MODELE_CONVOCATION = RACINE / "documents" / "modeles_courriers" / "courriel_convocation_test.txt"

JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
           "septembre", "octobre", "novembre", "décembre"]


class TransitionRefusee(ValueError):
    """Levée quand un enregistrement ne respecte pas le processus."""


# --- Chargement --------------------------------------------------------------------
def charger_donnees(dossier=DOSSIER_RAW):
    d = {nom: lire_csv(dossier / f"{nom}.csv")
         for nom in ("offres_emploi", "candidatures", "recrutement_etapes", "planning_entretiens")}
    for e in d["recrutement_etapes"]:
        e["etape"] = int(e["etape"])
    return d


def evenements_de(donnees, candidature_id, jour=None):
    """Historique d'une candidature, trié, limité aux actions faites au plus tard à 'jour'."""
    evts = [e for e in donnees["recrutement_etapes"] if e["candidature_id"] == candidature_id
            and (jour is None or en_date(e["date"]) <= jour)]
    return sorted(evts, key=lambda e: (e["etape"], e["date"]))


def creneau_de(donnees, candidature_id, confirme_seulement=True):
    for c in donnees["planning_entretiens"]:
        if c["candidature_id"] == candidature_id and (c["statut"] == "Confirmé" or not confirme_seulement):
            return c
    return None


# --- Transitions de statut ------------------------------------------------------------
def problemes_transition(historique, evenement, candidature):
    """Liste des règles non respectées si l'on ajoute 'evenement' à 'historique'."""
    p = []
    etape, resultat, intervenant = evenement["etape"], evenement["resultat"], evenement["intervenant"]
    if intervenant not in INTERVENANTS_HUMAINS:
        p.append(f"intervenant « {intervenant} » non autorisé : chaque étape est enregistrée par une personne")
    if etape not in ETAPES:
        return p + [f"étape {etape} inconnue"]
    if resultat not in RESULTATS_AUTORISES[etape]:
        p.append(f"résultat « {resultat} » impossible à l'étape {etape} ({ETAPES[etape]})")
    if not historique:
        if etape != 1:
            p.append("le dossier doit commencer à l'étape 1 (Candidature reçue)")
    else:
        precedent = historique[-1]
        if precedent["resultat"] not in POURSUITE:
            p.append(f"dossier déjà clôturé ({precedent['resultat']}) : aucune étape ne peut suivre")
        elif etape != precedent["etape"] + 1:
            p.append(f"saut d'étape interdit : {precedent['etape']} -> {etape}")
        if evenement["date"] < precedent["date"]:
            p.append("date antérieure à l'étape précédente")
    if etape == 6 and intervenant != RRH:
        p.append("la décision de l'étape 6 appartient au responsable RH")
    if resultat in NEGATIFS and intervenant not in (COMITE, RRH):
        p.append("une non-sélection est décidée par le comité de recrutement ou le responsable RH")
    if etape == 5 and resultat != DESISTEMENT:
        autorisation = candidature.get("date_autorisation_references", "")
        if candidature.get("autorisation_references") != "Oui" or not autorisation or autorisation > evenement["date"]:
            p.append("références contactées sans autorisation préalable du candidat")
    note = evenement.get("note_grille_sur_20")
    note = "" if note in (None, "") else str(note)
    if etape in ETAPES_AVEC_GRILLE and resultat != DESISTEMENT and note == "":
        p.append(f"grille d'évaluation manquante à l'étape {etape}")
    if note != "" and (etape not in ETAPES_AVEC_GRILLE or not 0 <= int(note) <= 20):
        p.append("note de grille inattendue (uniquement aux étapes 2 et 4, entre 0 et 20)")
    return p


def enregistrer_etape(historique, evenement, candidature):
    """Ajoute une étape si elle respecte le processus, sinon lève TransitionRefusee.
    Le module ne choisit jamais le résultat : il est fourni par la personne qui enregistre."""
    problemes = problemes_transition(historique, evenement, candidature)
    if problemes:
        raise TransitionRefusee(" ; ".join(problemes))
    return historique + [evenement]


# --- Statut et prochaine action -----------------------------------------------------------
def statut_candidature(historique):
    dernier = historique[-1]
    if dernier["resultat"] in NEGATIFS:
        return STATUT_NON_RETENU
    if dernier["resultat"] == DESISTEMENT:
        return STATUT_DESISTEMENT
    if dernier["etape"] == 8:
        return STATUT_INTEGRE
    if dernier["etape"] == 7:
        return STATUT_RECRUTE
    return STATUT_EN_COURS


def prochaine_action(candidature, historique, creneau):
    """(action, responsable, échéance ou None). Tâches administratives uniquement."""
    statut = statut_candidature(historique)
    dernier = historique[-1]
    if statut == STATUT_NON_RETENU:
        if candidature["date_reponse_candidat"]:
            return ("Aucune : dossier clôturé, réponse envoyée", "", None)
        return ("Envoyer la réponse écrite au candidat", CRH,
                en_date(dernier["date"]) + timedelta(days=DELAI_REPONSE_JOURS))
    if statut == STATUT_DESISTEMENT:
        return ("Aucune : désistement enregistré, archiver le dossier", "", None)
    if statut == STATUT_INTEGRE:
        return ("Aucune : intégration terminée", "", None)
    etape = dernier["etape"]
    if etape == 1:
        return ("Réaliser la présélection avec la grille d'analyse du CV", COMITE, None)
    if etape == 2:
        return ("Planifier le test et envoyer la convocation (modèle de courriel)", CRH, None)
    if etape == 3:
        if creneau:
            return (f"Faire passer le test et l'entretien le {creneau['date'][8:10]}/{creneau['date'][5:7]} "
                    f"à {creneau['heure_debut']}, puis enregistrer la grille", COMITE, en_date(creneau["date"]))
        return ("Fixer un créneau de test dans le planning", CRH, None)
    if etape == 4:
        if candidature["autorisation_references"] != "Oui":
            return ("Obtenir l'autorisation écrite du candidat avant de contacter ses références", CRH, None)
        return ("Vérifier les références (avec l'autorisation du candidat)", CRH, None)
    if etape == 5:
        return ("Transmettre le dossier complet au responsable RH pour décision", CRH, None)
    if etape == 6:
        return ("Préparer l'offre et le contrat", RRH, None)
    if etape == 7:
        prise = en_date(candidature["date_prise_fonction_prevue"])
        return ("Préparer l'intégration (checklist) et enregistrer l'arrivée", CRH, prise)
    return ("À vérifier", CRH, None)


def etat_candidature(donnees, candidature, jour):
    """Tout ce qu'il faut savoir sur une candidature à la date 'jour'."""
    cid = candidature["candidature_id"]
    historique = evenements_de(donnees, cid, jour)
    creneau = creneau_de(donnees, cid)
    dernier = historique[-1]
    statut = statut_candidature(historique)
    action, responsable, echeance = prochaine_action(candidature, historique, creneau)
    jours_sans_action = (jour - en_date(dernier["date"])).days

    alerte = ""
    if statut == STATUT_EN_COURS and echeance is None and jours_sans_action > DELAI_RELANCE_JOURS:
        alerte = f"Relancer : aucune action depuis {jours_sans_action} jours"
    elif echeance is not None and echeance < jour:
        alerte = f"Échéance dépassée de {(jour - echeance).days} jours"

    par_etape = {e["etape"]: e for e in historique}
    cloture = statut in (STATUT_NON_RETENU, STATUT_DESISTEMENT, STATUT_RECRUTE, STATUT_INTEGRE)
    # Étape affichée = dernière étape réellement franchie (un désistement n'en franchit aucune).
    franchies = [e["etape"] for e in historique if e["resultat"] != DESISTEMENT]
    etape = franchies[-1] if franchies else 1
    return {
        "candidature_id": cid, "offre_id": candidature["offre_id"],
        "nom": f"{candidature['prenom']} {candidature['nom']}",
        "etape": etape, "etape_libelle": ETAPES[etape],
        "dernier_resultat": dernier["resultat"], "statut": statut,
        "prochaine_action": action, "responsable": responsable, "echeance": echeance,
        "jours_sans_action": jours_sans_action, "alerte": alerte,
        "delai_traitement_jours": ((en_date(dernier["date"]) if cloture else jour)
                                   - en_date(candidature["date_candidature"])).days,
        "dates": {
            "Candidature": candidature["date_candidature"],
            "Présélection": par_etape.get(2, {}).get("date", ""),
            "Convocation": par_etape.get(3, {}).get("date", ""),
            "Test et entretien": (par_etape[4]["date"] if 4 in par_etape and par_etape[4]["resultat"] != DESISTEMENT
                                  else (creneau["date"] if creneau else "")),
            "Références": par_etape.get(5, {}).get("date", ""),
            "Décision RH": par_etape.get(6, {}).get("date", ""),
            "Contrat signé": par_etape.get(7, {}).get("date", ""),
            "Prise de fonction prévue": candidature["date_prise_fonction_prevue"],
            "Réponse envoyée": candidature["date_reponse_candidat"],
        },
        "historique": historique,
    }


def tous_les_etats(donnees, jour):
    # Ordre fixe par numéro de dossier : le module ne classe jamais les candidats.
    return [etat_candidature(donnees, c, jour)
            for c in sorted(donnees["candidatures"], key=lambda c: c["candidature_id"])]


# --- Indicateurs ----------------------------------------------------------------------------
def entonnoir(donnees, jour, offre_id=None):
    """Nombre de candidatures ayant franchi chaque étape (un désistement ne compte pas)."""
    cands = [c for c in donnees["candidatures"] if offre_id is None or c["offre_id"] == offre_id]
    resultat = {}
    for k in ETAPES:
        resultat[k] = sum(any(e["etape"] == k and e["resultat"] != DESISTEMENT
                              for e in evenements_de(donnees, c["candidature_id"], jour)) for c in cands)
    return resultat


def indicateurs(donnees, jour):
    etats = tous_les_etats(donnees, jour)
    decisions = [(en_date(e["dates"]["Décision RH"]) - en_date(e["dates"]["Candidature"])).days
                 for e in etats if e["dates"]["Décision RH"] and en_date(e["dates"]["Décision RH"]) <= jour]
    return {
        "candidatures": len(etats),
        "en_cours": sum(e["statut"] == STATUT_EN_COURS for e in etats),
        "actions_a_mener": sum(bool(e["responsable"]) for e in etats),
        "alertes": sum(bool(e["alerte"]) for e in etats),
        "tests_a_venir": sum(c["statut"] == "Confirmé" and en_date(c["date"]) >= jour
                             for c in donnees["planning_entretiens"]),
        "postes_pourvus": sum(e["statut"] in (STATUT_RECRUTE, STATUT_INTEGRE) for e in etats),
        "delai_moyen_decision_jours": round(sum(decisions) / len(decisions)) if decisions else None,
    }


# --- Contrôle global des données ------------------------------------------------------------
def verifier_donnees(donnees):
    """Rejoue toutes les transitions et contrôle planning et dates. Renvoie la liste des problèmes."""
    problemes = []
    offres = {o["offre_id"]: o for o in donnees["offres_emploi"]}
    for c in donnees["candidatures"]:
        cid = c["candidature_id"]
        if c["offre_id"] not in offres:
            problemes.append(f"{cid} : offre inconnue")
            continue
        o = offres[c["offre_id"]]
        if not o["date_publication"] <= c["date_candidature"] <= o["date_cloture"]:
            problemes.append(f"{cid} : candidature hors de la période de publication")
        historique = []
        for e in evenements_de(donnees, cid):
            try:
                historique = enregistrer_etape(historique, e, c)
            except TransitionRefusee as erreur:
                problemes.append(f"{cid} {e['evenement_id']} : {erreur}")
        if not historique:
            problemes.append(f"{cid} : aucune étape enregistrée")
            continue
        if historique[0]["date"] != c["date_candidature"]:
            problemes.append(f"{cid} : l'étape 1 ne correspond pas à la date de candidature")
        statut = statut_candidature(historique)
        dernier = historique[-1]
        if c["date_reponse_candidat"] and (statut != STATUT_NON_RETENU or c["date_reponse_candidat"] < dernier["date"]):
            problemes.append(f"{cid} : date de réponse incohérente")
        if c["date_prise_fonction_prevue"] and (statut not in (STATUT_RECRUTE, STATUT_INTEGRE)
                                                or c["date_prise_fonction_prevue"] <= historique[-1]["date"]):
            problemes.append(f"{cid} : date de prise de fonction incohérente")
        if statut == STATUT_RECRUTE and not c["date_prise_fonction_prevue"]:
            problemes.append(f"{cid} : recruté(e) sans date de prise de fonction")
        # Planning : toute convocation correspond à un créneau, fixé avec un préavis suffisant.
        convocation = next((e for e in historique if e["etape"] == 3), None)
        creneau = creneau_de(donnees, cid, confirme_seulement=False)
        if convocation and not creneau:
            problemes.append(f"{cid} : convoqué(e) sans créneau dans le planning")
        if creneau and convocation:
            if (en_date(creneau["date"]) - en_date(convocation["date"])).days < PREAVIS_CONVOCATION_JOURS:
                problemes.append(f"{cid} : préavis de convocation inférieur à {PREAVIS_CONVOCATION_JOURS} jours")
            test = next((e for e in historique if e["etape"] == 4 and e["resultat"] != DESISTEMENT), None)
            if test and test["date"] != creneau["date"]:
                problemes.append(f"{cid} : la date du test diffère du planning")
            if creneau["statut"] != "Confirmé" and statut != STATUT_DESISTEMENT:
                problemes.append(f"{cid} : créneau annulé sans désistement")
    confirmes = [c for c in donnees["planning_entretiens"] if c["statut"] == "Confirmé"]
    for c in donnees["planning_entretiens"]:
        if c["heure_fin"] <= c["heure_debut"] or en_date(c["date"]).weekday() >= 5:
            problemes.append(f"{c['creneau_id']} : horaire invalide ou créneau un week-end")
    for i, a in enumerate(confirmes):
        for b in confirmes[i + 1:]:
            if a["date"] == b["date"] and a["lieu"] == b["lieu"] and a["heure_debut"] < b["heure_fin"] \
                    and b["heure_debut"] < a["heure_fin"]:
                problemes.append(f"{a['creneau_id']} / {b['creneau_id']} : créneaux qui se chevauchent")
    return problemes


# --- Modèles de documents --------------------------------------------------------------------
def date_longue(d):
    """date(2026, 11, 4) -> 'mercredi 4 novembre 2026'."""
    return f"{JOURS_FR[d.weekday()]} {d.day} {MOIS_FR[d.month - 1]} {d.year}"


def decaler_jours_ouvrables(d, nb):
    """Avance (nb > 0) ou recule (nb < 0) de nb jours ouvrables."""
    pas = 1 if nb > 0 else -1
    while nb:
        d += timedelta(days=pas)
        if d.weekday() < 5:
            nb -= pas
    return d


def ramener_sur_jour_ouvrable(d, sens):
    """Si la date tombe un week-end, la décale au jour ouvrable précédent (-1) ou suivant (+1)."""
    while d.weekday() >= 5:
        d += timedelta(days=sens)
    return d


def generer_convocation(candidature, offre, creneau, signataire="Josué Mirindi, Chargé RH"):
    """Remplit le modèle de courriel de convocation. Lève KeyError si un champ manque."""
    jour_test = en_date(creneau["date"])
    valeurs = {
        "prenom": candidature["prenom"], "nom": candidature["nom"],
        "intitule": offre["intitule"], "offre_id": offre["offre_id"], "bureau": offre["bureau"],
        "date_longue": date_longue(jour_test),
        "heure_debut": creneau["heure_debut"].replace(":", "h"),
        "heure_fin": creneau["heure_fin"].replace(":", "h"),
        "lieu": creneau["lieu"], "epreuve": creneau["epreuve"],
        "date_confirmation": date_longue(decaler_jours_ouvrables(jour_test, -2)),
        "signataire": signataire,
    }
    return MODELE_CONVOCATION.read_text(encoding="utf-8").format(**valeurs)


# Checklist d'intégration : (moment, décalage en jours calendaires par rapport à J,
# tâche, responsable). Les tâches avant l'arrivée sont ramenées au jour ouvrable
# précédent, les suivantes au jour ouvrable suivant.
CHECKLIST_INTEGRATION = [
    ("Avant l'arrivée", -10, "Envoyer le courriel de bienvenue (date, heure, lieu, personne à contacter)", CRH),
    ("Avant l'arrivée", -7, "Constituer le dossier individuel (contrat signé, pièces administratives)", CRH),
    ("Avant l'arrivée", -5, "Préparer le poste de travail, la messagerie et les accès informatiques", "Administrateur(trice) systèmes"),
    ("Avant l'arrivée", -3, "Désigner un(e) référent(e) pour les premières semaines", RRH),
    ("Jour 1", 0, "Accueil, présentation de l'organisation et visite des locaux", RRH),
    ("Jour 1", 0, "Remettre et expliquer le règlement intérieur, le code de conduite et les politiques internes", CRH),
    ("Jour 1", 0, "Présenter les consignes de sécurité et les contacts d'urgence", "Agent(e) de sécurité"),
    ("Première semaine", 2, "Présenter l'équipe et les principaux interlocuteurs", "Responsable hiérarchique"),
    ("Première semaine", 4, "Point de fin de première semaine (questions, besoins)", "Responsable hiérarchique"),
    ("Premier mois", 14, "Formation aux outils et procédures RH", RRH),
    ("Premier mois", 30, "Entretien de suivi à un mois", "Responsable hiérarchique et RH"),
]


def generer_checklist(prise_de_fonction):
    """Checklist datée à partir de la date de prise de fonction (J)."""
    lignes = []
    for moment, decalage, tache, responsable in CHECKLIST_INTEGRATION:
        brute = prise_de_fonction + timedelta(days=decalage)
        lignes.append({
            "moment": moment, "repere": f"J{decalage:+d}" if decalage else "J",
            "date": ramener_sur_jour_ouvrable(brute, -1 if decalage < 0 else 1),
            "tache": tache, "responsable": responsable,
        })
    return lignes
