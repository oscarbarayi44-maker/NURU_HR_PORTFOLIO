"""
Étape 3 - Contrôle qualité : vérifie que les données fictives sont cohérentes.

Chaque règle affiche [OK] ou [ERREUR]. Le script se termine avec le code 1
si au moins une règle échoue.

Utilisation (depuis la racine du projet) :
    python analysis/03_verifier_coherence.py
"""
import sys
from datetime import timedelta

import recrutement
from commun import (DATE_REFERENCE, DOSSIER_PROCESSED, DOSSIER_RAW, age, en_date,
                    jours_ouvrables, lire_csv, mois_entre)

collaborateurs = lire_csv(DOSSIER_RAW / "collaborateurs.csv")
contrats = lire_csv(DOSSIER_RAW / "contrats.csv")
absences = lire_csv(DOSSIER_RAW / "absences.csv")
stagiaires = lire_csv(DOSSIER_RAW / "stagiaires.csv")
offres = lire_csv(DOSSIER_RAW / "offres_emploi.csv")
candidatures = lire_csv(DOSSIER_RAW / "candidatures.csv")
effectifs = lire_csv(DOSSIER_PROCESSED / "effectifs_mensuels_2026.csv")

par_matricule = {c["matricule"]: c for c in collaborateurs}
nb_erreurs = 0


def controle(libelle, problemes):
    """Affiche le résultat d'une règle. 'problemes' = liste de messages d'erreur."""
    global nb_erreurs
    if problemes:
        nb_erreurs += 1
        print(f"[ERREUR] {libelle}")
        for p in problemes:
            print(f"         - {p}")
    else:
        print(f"[OK]     {libelle}")


print(f"Contrôle de cohérence (date de référence : {DATE_REFERENCE})\n")

# --- Collaborateurs -----------------------------------------------------------
print("Collaborateurs")
controle("30 collaborateurs, matricules uniques",
         [] if len(par_matricule) == len(collaborateurs) == 30
         else [f"{len(collaborateurs)} lignes, {len(par_matricule)} matricules uniques"])
controle("Genre renseigné (F ou M)",
         [c["matricule"] for c in collaborateurs if c["genre"] not in ("F", "M")])
controle("Au moins 18 ans à la date d'embauche",
         [c["matricule"] for c in collaborateurs
          if age(en_date(c["date_naissance"]), en_date(c["date_embauche"])) < 18])
controle("Statut 'Sorti' <=> date et motif de sortie renseignés",
         [c["matricule"] for c in collaborateurs
          if (c["statut"] == "Sorti") != bool(c["date_sortie"] and c["motif_sortie"])])
controle("Date de sortie entre l'embauche et la date de référence",
         [c["matricule"] for c in collaborateurs if c["date_sortie"]
          and not en_date(c["date_embauche"]) <= en_date(c["date_sortie"]) <= DATE_REFERENCE])

noms = ([f"{c['prenom']} {c['nom']}" for c in collaborateurs]
        + [f"{s['prenom']} {s['nom']}" for s in stagiaires]
        + [f"{c['prenom']} {c['nom']}" for c in candidatures])
controle("Aucun nom en double (collaborateurs, stagiaires, candidats)",
         sorted({n for n in noms if noms.count(n) > 1}))

# --- Contrats -----------------------------------------------------------------
print("\nContrats")
problemes_chaine, problemes_couverture, problemes_cdd, problemes_cdi = [], [], [], []
for c in collaborateurs:
    m = c["matricule"]
    liste = sorted((ct for ct in contrats if ct["matricule"] == m), key=lambda ct: ct["date_debut"])
    if not liste:
        problemes_chaine.append(f"{m} : aucun contrat")
        continue
    if liste[0]["date_debut"] != c["date_embauche"]:
        problemes_chaine.append(f"{m} : le 1er contrat ne commence pas à la date d'embauche")
    for prec, suiv in zip(liste, liste[1:]):
        if not prec["date_fin"] or en_date(prec["date_fin"]) + timedelta(days=1) != en_date(suiv["date_debut"]):
            problemes_chaine.append(f"{m} : trou ou chevauchement entre {prec['contrat_id']} et {suiv['contrat_id']}")
    dernier = liste[-1]
    if c["statut"] == "Actif" and dernier["date_fin"] and en_date(dernier["date_fin"]) < DATE_REFERENCE:
        problemes_couverture.append(f"{m} : actif mais dernier contrat terminé le {dernier['date_fin']}")
    if c["statut"] == "Sorti" and dernier["date_fin"] != c["date_sortie"]:
        problemes_couverture.append(f"{m} : le dernier contrat ne se termine pas à la date de sortie")
    for ct in liste:
        if ct["type_contrat"] == "CDD":
            debut, fin = en_date(ct["date_debut"]), en_date(ct["date_fin"])
            if fin is None or fin < debut or mois_entre(debut, fin + timedelta(days=1)) > 24:
                problemes_cdd.append(f"{ct['contrat_id']} : date de fin absente ou durée > 24 mois")
        elif ct["date_fin"] and ct["date_fin"] != c["date_sortie"]:
            problemes_cdi.append(f"{ct['contrat_id']} : CDI avec date de fin sans sortie du collaborateur")
controle("Chaque collaborateur a une suite de contrats continue depuis l'embauche", problemes_chaine)
controle("Actifs couverts par un contrat ; sortants : contrat clos à la date de sortie", problemes_couverture)
controle("CDD : date de fin renseignée et durée ≤ 24 mois", problemes_cdd)
controle("CDI : pas de date de fin, sauf en cas de sortie", problemes_cdi)
controle("Contrats rattachés à un matricule existant",
         [ct["contrat_id"] for ct in contrats if ct["matricule"] not in par_matricule])

# --- Absences -------------------------------------------------------------------
print("\nAbsences et congés")
controle("Absences rattachées à un matricule existant",
         [a["absence_id"] for a in absences if a["matricule"] not in par_matricule])
controle("Date de début ≤ date de fin et nombre de jours ouvrables exact",
         [a["absence_id"] for a in absences
          if en_date(a["date_debut"]) > en_date(a["date_fin"])
          or jours_ouvrables(en_date(a["date_debut"]), en_date(a["date_fin"])) != int(a["nb_jours_ouvrables"])])
hors_contrat = []
for a in absences:
    c = par_matricule[a["matricule"]]
    sortie = en_date(c["date_sortie"])
    if en_date(a["date_debut"]) < en_date(c["date_embauche"]) or (sortie and en_date(a["date_fin"]) > sortie):
        hors_contrat.append(f"{a['absence_id']} ({a['matricule']})")
controle("Absences comprises dans la période d'emploi", hors_contrat)
chevauchements = []
effectives = [a for a in absences if a["statut"] != "Refusée"]
for i, a in enumerate(effectives):
    for b in effectives[i + 1:]:
        if a["matricule"] == b["matricule"] and a["date_debut"] <= b["date_fin"] and b["date_debut"] <= a["date_fin"]:
            chevauchements.append(f"{a['absence_id']} / {b['absence_id']}")
controle("Pas de chevauchement d'absences pour un même collaborateur", chevauchements)
controle("Absences futures = uniquement des congés annuels planifiés",
         [a["absence_id"] for a in absences if en_date(a["date_debut"]) > DATE_REFERENCE
          and (a["type_absence"] != "Congé annuel" or a["statut"] not in ("Approuvée", "En attente"))])
controle("Congé de maternité attribué uniquement à des collaboratrices",
         [a["absence_id"] for a in absences
          if a["type_absence"] == "Congé de maternité" and par_matricule[a["matricule"]]["genre"] != "F"])

# --- Stagiaires -----------------------------------------------------------------
print("\nStagiaires")
problemes_enc = []
for s in stagiaires:
    enc = par_matricule.get(s["encadreur_matricule"])
    if enc is None:
        problemes_enc.append(f"{s['stagiaire_id']} : encadreur inconnu")
        continue
    if enc["departement"] != s["departement"]:
        problemes_enc.append(f"{s['stagiaire_id']} : encadreur d'un autre département")
    if enc["date_sortie"] and en_date(enc["date_sortie"]) < en_date(s["date_fin"]):
        problemes_enc.append(f"{s['stagiaire_id']} : encadreur parti avant la fin du stage")
controle("Encadreur existant, du même département et présent pendant le stage", problemes_enc)
controle("Date de début < date de fin",
         [s["stagiaire_id"] for s in stagiaires if s["date_debut"] >= s["date_fin"]])
controle("Note d'évaluation présente si et seulement si le stage est terminé",
         [s["stagiaire_id"] for s in stagiaires
          if bool(s["note_evaluation_sur_20"]) != (en_date(s["date_fin"]) < DATE_REFERENCE)])

# --- Recrutement ----------------------------------------------------------------
print("\nRecrutement")
offres_par_id = {o["offre_id"]: o for o in offres}
donnees_rec = recrutement.charger_donnees()
controle("10 candidatures rattachées à une offre existante",
         [] if len(candidatures) == 10 and all(c["offre_id"] in offres_par_id for c in candidatures)
         else ["nombre de candidatures ou offre inconnue"])
controle("Aucune caractéristique personnelle sensible dans les candidatures",
         sorted({"genre", "date_naissance", "age", "nationalite", "situation_familiale", "religion", "sante"}
                & set(candidatures[0])))
controle("Transitions, intervenants humains, autorisations et planning conformes au processus",
         recrutement.verifier_donnees(donnees_rec))
etats_rec = recrutement.tous_les_etats(donnees_rec, DATE_REFERENCE)
controle("Au plus un contrat signé par offre",
         [o for o in offres_par_id
          if sum(s["offre_id"] == o and s["etape"] >= 7 and s["statut"] != recrutement.STATUT_DESISTEMENT
                 for s in etats_rec) > 1])
controle("Recrue pas encore comptée dans les effectifs (prise de fonction après la date de référence)",
         [c["candidature_id"] for c in candidatures
          if c["date_prise_fonction_prevue"] and en_date(c["date_prise_fonction_prevue"]) <= DATE_REFERENCE])

# --- Registre des effectifs -----------------------------------------------------
print("\nRegistre mensuel des effectifs")
problemes_eff = []
for e in effectifs:
    debut, ent, sor, fin = (int(e[k]) for k in ("effectif_debut", "entrees", "sorties", "effectif_fin"))
    if debut + ent - sor != fin:
        problemes_eff.append(f"{e['mois']} : {debut} + {ent} - {sor} ≠ {fin}")
    if int(e["dont_femmes"]) + int(e["dont_hommes"]) != fin or int(e["dont_cdi"]) + int(e["dont_cdd"]) != fin:
        problemes_eff.append(f"{e['mois']} : sous-totaux (genre ou contrat) ≠ effectif")
for prec, suiv in zip(effectifs, effectifs[1:]):
    if prec["effectif_fin"] != suiv["effectif_debut"]:
        problemes_eff.append(f"{suiv['mois']} : effectif de début ≠ effectif de fin du mois précédent")
nb_actifs = sum(c["statut"] == "Actif" for c in collaborateurs)
if int(effectifs[-1]["effectif_fin"]) != nb_actifs:
    problemes_eff.append(f"effectif fin octobre ({effectifs[-1]['effectif_fin']}) ≠ actifs ({nb_actifs})")
controle("Début + entrées - sorties = fin ; continuité ; total = nombre d'actifs", problemes_eff)

# --- Bilan ----------------------------------------------------------------------
print("\n" + ("Toutes les règles sont respectées." if nb_erreurs == 0
              else f"{nb_erreurs} règle(s) en erreur : corrigez avant d'aller plus loin."))
sys.exit(1 if nb_erreurs else 0)
