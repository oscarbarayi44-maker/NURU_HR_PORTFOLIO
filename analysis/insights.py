"""
Insights RH : constats chiffrés calculés automatiquement à partir des données sources.

Règles :
- aucun chiffre saisi à la main : tout est recalculé depuis data/raw ;
- constats AGRÉGÉS uniquement (jamais de jugement sur une personne nommée) ;
- les motifs de santé ne sont jamais isolés : seul un taux global d'absences
  non planifiées est publié ;
- chaque « piste » est une suggestion : la décision appartient au responsable RH.

DONNÉES FICTIVES - Portfolio personnel, non officiel de Nuru.
"""
from datetime import date, timedelta

import recrutement as rc
import suivi_rh as rh
import tableau_de_bord as tb
from commun import en_date

ATTENTION, A_SUIVRE, INFORMATION = "Attention", "À suivre", "Information"
TYPES_NON_PLANIFIES = ("Maladie", "Absence non justifiée")   # hors congés et maternité
MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
           "septembre", "octobre", "novembre", "décembre"]
TAILLE_MIN_DEPARTEMENT = 3   # en dessous, une part en % n'a pas de sens et pourrait viser une personne


def pct(valeur, decimales=0):
    """Pourcentage au format français : 10,9 %."""
    texte = f"{valeur:.{decimales}f}".replace(".", ",")
    return f"{texte} %"


def maximums(compteur):
    """Toutes les clés à égalité sur la valeur maximale (jamais un choix arbitraire)."""
    if not compteur:
        return []
    plus_haut = max(compteur.values())
    return sorted(k for k, v in compteur.items() if v == plus_haut)


def nom_mois(cle):
    annee, mois = cle.split("-")
    return f"{MOIS_FR[int(mois) - 1]} {annee}"


def taux_absences_non_planifiees(d_rh, jour):
    """Jours d'absence non planifiés / jours travaillables (présents du lundi au vendredi), depuis le 1er janvier."""
    debut = date(jour.year, 1, 1)
    numerateur = 0
    for a in d_rh["absences"]:
        if a["type_absence"] in TYPES_NON_PLANIFIES and a["statut"] in rh.STATUTS_REALISES:
            d, fin = max(en_date(a["date_debut"]), debut), min(en_date(a["date_fin"]), jour)
            while d <= fin:
                numerateur += d.weekday() < 5
                d += timedelta(days=1)
    denominateur, d = 0, debut
    while d <= jour:
        if d.weekday() < 5:
            denominateur += sum(en_date(c["date_embauche"]) <= d and (not c["date_sortie"] or en_date(c["date_sortie"]) >= d)
                                for c in d_rh["collaborateurs"])
        d += timedelta(days=1)
    return numerateur, denominateur


def calculer_insights(jour):
    d_rh, d_rec = rh.charger_donnees(), rc.charger_donnees()
    tdb = tb.donnees_tableau_de_bord(jour)
    resultats = []

    # 1. Échéances de CDD
    ech = [l for l in rh.echeances(d_rh, jour) if l["jours_restants"] is not None]
    sous_30 = [l for l in ech if 0 <= l["jours_restants"] <= 30]
    sous_90 = [l for l in ech if 0 <= l["jours_restants"] <= 90]
    if ech:
        prochaine = min(ech, key=lambda l: l["jours_restants"])
        resultats.append({
            "theme": "Contrats", "niveau": ATTENTION if sous_30 else INFORMATION,
            "titre": "Échéances de CDD concentrées sur les prochaines semaines",
            "indicateur": f"{len(sous_30)} / {len(ech)}",
            "constat": f"{len(sous_30)} des {len(ech)} CDD en cours se terminent dans les 30 jours "
                       f"({len(sous_90)} dans les 90 jours). Première échéance : "
                       f"{en_date(prochaine['date_fin']):%d/%m/%Y}, dans {prochaine['jours_restants']} jours.",
            "piste": "Préparer dès maintenant les dossiers (avis du responsable hiérarchique, besoins du service) "
                     "pour que le responsable RH décide avant chaque échéance.",
        })

    # 2. Part de CDD par département (départements d'au moins 3 personnes)
    parts = {dep: v["CDD"] / (v["CDI"] + v["CDD"]) for dep, v in tdb["effectifs_departements"].items()
             if v["CDI"] + v["CDD"] >= TAILLE_MIN_DEPARTEMENT}
    if parts:
        deps_max = maximums(parts)
        part_max = parts[deps_max[0]]
        details = " ; ".join(f"{dep} : {tdb['effectifs_departements'][dep]['CDD']} CDD sur "
                             f"{sum(tdb['effectifs_departements'][dep].values())} personnes" for dep in deps_max)
        resultats.append({
            "theme": "Effectifs", "niveau": A_SUIVRE if part_max > tdb["part_cdd_pct"] / 100 else INFORMATION,
            "titre": "Département le plus dépendant des CDD" if len(deps_max) == 1 else "Départements les plus dépendants des CDD",
            "indicateur": pct(100 * part_max),
            "constat": f"{details} ({pct(100 * part_max)}), contre {pct(tdb['part_cdd_pct'])} pour l'ensemble de "
                       f"l'effectif. Calcul limité aux départements d'au moins {TAILLE_MIN_DEPARTEMENT} personnes.",
            "piste": "Vérifier avec le responsable du département si ces postes correspondent à des besoins "
                     "temporaires ou permanents.",
        })

    # 3. Rotation du personnel depuis janvier
    mensuel = rh.effectifs_mensuels(d_rh, jour)
    effectif_moyen = sum(m["effectif_fin"] for m in mensuel) / len(mensuel)
    sorties = sum(m["sorties"] for m in mensuel)
    entrees = sum(m["entrees"] for m in mensuel)
    deps_sortie = {}
    for c in d_rh["collaborateurs"]:
        if c["date_sortie"] and date(jour.year, 1, 1) <= en_date(c["date_sortie"]) <= jour:
            deps_sortie[c["departement"]] = deps_sortie.get(c["departement"], 0) + 1
    rotation = 100 * sorties / effectif_moyen if effectif_moyen else 0
    deps_max_sorties = maximums(deps_sortie)
    dep_sorties = deps_max_sorties[0] if len(deps_max_sorties) == 1 else None
    resultats.append({
        "theme": "Effectifs", "niveau": A_SUIVRE if sorties else INFORMATION,
        "titre": "Rotation du personnel depuis janvier",
        "indicateur": pct(rotation, 1),
        "constat": f"{sorties} sortie(s) et {entrees} entrée(s) en {len(mensuel)} mois, pour un effectif moyen de "
                   f"{effectif_moyen:.1f}".replace(".", ",") + " personnes."
                   + (f" {deps_sortie[dep_sorties]} des {sorties} sorties concernent le département {dep_sorties}."
                      if dep_sorties and deps_sortie[dep_sorties] > 1 else ""),
        "piste": "Proposer un court entretien de départ systématique pour comprendre les causes, sans en tirer "
                 "de conclusion sur un cas isolé.",
    })

    # 4. Absences non planifiées (taux global, sans détail par motif)
    jours_np, jours_travaillables = taux_absences_non_planifiees(d_rh, jour)
    taux = 100 * jours_np / jours_travaillables if jours_travaillables else 0
    resultats.append({
        "theme": "Absences", "niveau": INFORMATION,
        "titre": "Absences non planifiées",
        "indicateur": pct(taux, 1),
        "constat": f"{jours_np} jours d'absence non planifiés sur {jours_travaillables} jours travaillables depuis le "
                   "1er janvier (absences pour raison de santé et absences non justifiées, congés exclus).",
        "piste": "Suivre ce taux chaque mois ; une hausse durable justifie un échange collectif sur les conditions "
                 "de travail, jamais un contrôle individuel des motifs.",
    })

    # 5. Pic de congés annuels
    conges = {}
    for (mois, cat), n in rh.jours_absence_par_mois(d_rh, jour).items():
        if cat == "Congé annuel":
            conges[mois] = conges.get(mois, 0) + n
    if conges:
        mois_pic = max(conges, key=conges.get)
        total = sum(conges.values())
        resultats.append({
            "theme": "Absences", "niveau": INFORMATION,
            "titre": "Mois le plus chargé en congés annuels",
            "indicateur": nom_mois(mois_pic),
            "constat": f"{conges[mois_pic]} jours de congé annuel en {nom_mois(mois_pic)}, soit "
                       f"{pct(100 * conges[mois_pic] / total)} des {total} jours pris depuis janvier.",
            "piste": "Établir un planning prévisionnel des congés par service pour garantir la continuité "
                     "pendant les périodes chargées.",
        })

    # 6. Recrutement : conversion et délai (agrégés, aucun candidat nommé ni classé)
    entonnoir = rc.entonnoir(d_rec, jour)
    ind_rec = rc.indicateurs(d_rec, jour)
    if entonnoir[2]:
        convoques = [e["candidature_id"] for e in d_rec["recrutement_etapes"]
                     if e["etape"] == 3 and e["resultat"] != rc.DESISTEMENT and en_date(e["date"]) <= jour]
        sources = {}
        for c in d_rec["candidatures"]:
            if c["candidature_id"] in convoques:
                sources[c["source"]] = sources.get(c["source"], 0) + 1
        srcs = maximums(sources)
        if len(srcs) == 1:
            texte_src = f"Source la plus représentée parmi les convocations : {srcs[0]} ({sources[srcs[0]]} sur {len(convoques)})."
        elif srcs:
            texte_src = (f"Sources à égalité parmi les convocations : {', '.join(srcs)} "
                         f"({sources[srcs[0]]} chacune sur {len(convoques)}).")
        else:
            texte_src = ""
        delai = ind_rec["delai_moyen_decision_jours"]
        resultats.append({
            "theme": "Recrutement", "niveau": INFORMATION,
            "titre": "Efficacité du processus de recrutement",
            "indicateur": pct(100 * entonnoir[3] / entonnoir[2]),
            "constat": f"{entonnoir[3]} des {entonnoir[2]} candidatures examinées en présélection ont été convoquées au test. "
                       + (f"Délai moyen entre la candidature et la décision du responsable RH : {delai} jours. " if delai else "")
                       + texte_src,
            "piste": "Comparer ce délai à l'objectif fixé par le responsable RH et conserver les canaux de diffusion "
                     "qui apportent des profils adaptés.",
        })

    # 7. Actions en retard
    retards = [a for a in tdb["actions"] if a["urgence"] == tb.EN_RETARD]
    if retards:
        plus_ancien = max((jour - a["echeance"]).days for a in retards)
        resultats.append({
            "theme": "Organisation", "niveau": ATTENTION,
            "titre": "Actions administratives en retard",
            "indicateur": str(len(retards)),
            "constat": f"{len(retards)} action(s) ont dépassé leur échéance ; la plus ancienne de {plus_ancien} jours. "
                       f"Domaine(s) concerné(s) : {', '.join(sorted({a['domaine'] for a in retards}))}.",
            "piste": "Traiter ces actions en priorité et ajouter un point hebdomadaire de suivi des échéances.",
        })

    ordre = {ATTENTION: 0, A_SUIVRE: 1, INFORMATION: 2}
    return sorted(resultats, key=lambda i: ordre[i["niveau"]])
