"""
Tableau de bord RH : rassemble les indicateurs des modules RH et recrutement.

Aucune valeur n'est écrite dans le code : tout est recalculé à partir des
fichiers CSV de data/raw, via suivi_rh.py et recrutement.py.

DONNÉES FICTIVES - Portfolio personnel, non officiel de Nuru.
"""
import csv
import io

import recrutement as rc
import suivi_rh as rh
from commun import SEPARATEUR, en_date

# Niveaux d'urgence des actions, du plus pressant au moins pressant.
EN_RETARD, SOUS_7, SOUS_30, PLUS_TARD, SANS_DATE = (
    "En retard", "Sous 7 jours", "Sous 30 jours", "Plus tard", "Sans date fixée")
ORDRE_URGENCE = [EN_RETARD, SOUS_7, SOUS_30, PLUS_TARD, SANS_DATE]


def urgence(echeance, jour):
    if echeance is None:
        return SANS_DATE
    ecart = (echeance - jour).days
    if ecart < 0:
        return EN_RETARD
    if ecart <= 7:
        return SOUS_7
    if ecart <= 30:
        return SOUS_30
    return PLUS_TARD


def actions_a_effectuer(d_rh, d_rec, jour):
    """Liste consolidée des tâches administratives (contrats, congés, stagiaires, recrutement)."""
    actions = []

    def ajouter(domaine, objet, action, responsable, echeance):
        actions.append({"domaine": domaine, "objet": objet, "action": action, "responsable": responsable,
                        "echeance": echeance, "urgence": urgence(echeance, jour)})

    for l in rh.echeances(d_rh, jour):
        jours = l["jours_restants"]
        if jours is not None and jours <= rh.SEUILS_ALERTE[-1]:
            texte = ("Régulariser le contrat échu" if jours < 0 else
                     "Préparer le dossier de fin de CDD (renouvellement ou fin) pour décision du responsable RH")
            ajouter("Contrats", f"{l['matricule']} · {l['nom']}", texte, "Responsable RH", en_date(l["date_fin"]))

    noms = {c["matricule"]: rh.nom_complet(c) for c in d_rh["collaborateurs"]}
    for a in rh.demandes_en_attente(d_rh):
        ajouter("Congés", f"{a['matricule']} · {noms[a['matricule']]}",
                f"Traiter la demande ({rh.categorie_affichee(a['type_absence']).lower()}, "
                f"{a['nb_jours_ouvrables']} jours ouvrables)", "Responsable hiérarchique", en_date(a["date_debut"]))

    for s in rh.suivi_stagiaires(d_rh, jour):
        objet = f"{s['stagiaire_id']} · {s['nom']}"
        if s["statut"] == "En cours" and s["fin_proche"]:
            ajouter("Stagiaires", objet, "Préparer l'évaluation finale et l'attestation de stage",
                    f"Encadreur ({s['encadreur']})", en_date(s["date_fin"]))
        elif s["statut"] == "À venir" and (en_date(s["date_debut"]) - jour).days <= 30:
            ajouter("Stagiaires", objet, "Préparer l'accueil (poste, encadreur, convention signée)",
                    "Chargé(e) RH", en_date(s["date_debut"]))
        elif s["evaluation_finale"] == "À faire":
            ajouter("Stagiaires", objet, "Recueillir l'évaluation finale", f"Encadreur ({s['encadreur']})", None)

    for e in rc.tous_les_etats(d_rec, jour):
        if e["responsable"]:
            ajouter("Recrutement", f"{e['candidature_id']} · {e['nom']} ({e['offre_id']})",
                    e["prochaine_action"], e["responsable"], e["echeance"])

    return sorted(actions, key=lambda a: (ORDRE_URGENCE.index(a["urgence"]),
                                          a["echeance"] or jour, a["domaine"], a["objet"]))


def donnees_tableau_de_bord(jour):
    d_rh, d_rec = rh.charger_donnees(), rc.charger_donnees()
    ind = rh.indicateurs(d_rh, jour)
    echeances = rh.echeances(d_rh, jour)
    stagiaires = rh.suivi_stagiaires(d_rh, jour)

    jours_par_categorie = {}
    for (_, categorie), nb in rh.jours_absence_par_mois(d_rh, jour).items():
        jours_par_categorie[categorie] = jours_par_categorie.get(categorie, 0) + nb
    realisees = [a for a in d_rh["absences"]
                 if a["statut"] in rh.STATUTS_REALISES and en_date(a["date_debut"]) <= jour]

    offres = {o["offre_id"]: o["intitule"] for o in d_rec["offres_emploi"]}
    etats = rc.tous_les_etats(d_rec, jour)

    return {
        "jour": jour,
        "effectif_total": ind["effectif_actif"],
        "collaborateurs_enregistres": len(d_rh["collaborateurs"]),
        "part_cdd_pct": ind["part_cdd_pct"],
        "effectifs_departements": rh.effectifs_par_departement(d_rh, jour),
        "contrats_30": [l for l in echeances if l["alerte"] == rh.URGENT],
        "contrats_echus": ind["echus"],
        "stagiaires": {statut: sum(s["statut"] == statut for s in stagiaires)
                       for statut in ("En cours", "À venir", "Terminé")},
        "absences": {
            "enregistrees": len(d_rh["absences"]),
            "realisees": len(realisees),
            "en_attente": len(rh.demandes_en_attente(d_rh)),
            "jours_realises": sum(jours_par_categorie.values()),
            "jours_par_categorie": dict(sorted(jours_par_categorie.items(), key=lambda kv: -kv[1])),
        },
        "offres": offres,
        "candidatures_total": len(d_rec["candidatures"]),
        "entonnoir": {o: rc.entonnoir(d_rec, jour, o) for o in offres},
        "en_cours_par_etape": {k: sum(e["etape"] == k and e["statut"] == rc.STATUT_EN_COURS for e in etats)
                               for k in rc.ETAPES},
        "actions": actions_a_effectuer(d_rh, d_rec, jour),
    }


# --- Exports CSV (ouverture directe dans Excel en français) -----------------------------
def _csv(entetes, lignes):
    tampon = io.StringIO()
    w = csv.writer(tampon, delimiter=SEPARATEUR, lineterminator="\r\n")
    w.writerow(entetes)
    w.writerows(lignes)
    return tampon.getvalue()


def export_actions_csv(tdb):
    return _csv(["Urgence", "Échéance", "Domaine", "Objet", "Action", "Responsable"],
                [[a["urgence"], a["echeance"].isoformat() if a["echeance"] else "", a["domaine"],
                  a["objet"], a["action"], a["responsable"]] for a in tdb["actions"]])


def export_indicateurs_csv(tdb):
    j = tdb["jour"].isoformat()
    lignes = [
        [j, "Effectif", "Effectif actif", tdb["effectif_total"]],
        [j, "Contrats", "CDD arrivant à échéance sous 30 jours", len(tdb["contrats_30"])],
        [j, "Stagiaires", "Stagiaires suivis", sum(tdb["stagiaires"].values())],
        [j, "Absences", "Absences et demandes enregistrées", tdb["absences"]["enregistrees"]],
        [j, "Absences", "Jours ouvrables d'absence réalisés", tdb["absences"]["jours_realises"]],
        [j, "Recrutement", "Candidatures", tdb["candidatures_total"]],
        [j, "Actions", "Actions administratives à effectuer", len(tdb["actions"])],
    ]
    for dep, v in tdb["effectifs_departements"].items():
        lignes += [[j, "Effectif par département", f"{dep} : CDI", v["CDI"]],
                   [j, "Effectif par département", f"{dep} : CDD", v["CDD"]]]
    for cat, nb in tdb["absences"]["jours_par_categorie"].items():
        lignes.append([j, "Jours d'absence par catégorie", cat, nb])
    for offre, etapes in tdb["entonnoir"].items():
        for k, nb in etapes.items():
            lignes.append([j, f"Candidatures ayant franchi l'étape ({offre})", f"{k}. {rc.ETAPES[k]}", nb])
    return _csv(["Date de situation", "Rubrique", "Indicateur", "Valeur"], lignes)
