"""
Étape 1 - Génère les données FICTIVES brutes dans data/raw/.

AVERTISSEMENT : toutes les personnes, dates et montants sont inventés.
Toute ressemblance avec une personne réelle serait une pure coïncidence.
Ce projet est un portfolio personnel ; ce n'est pas un outil officiel de Nuru.

Utilisation (depuis la racine du projet) :
    python analysis/01_generer_donnees_fictives.py

La graine aléatoire est fixe : relancer le script produit exactement
les mêmes fichiers.
"""
import random
from datetime import date, timedelta

from commun import (DATE_REFERENCE, DEBUT_ANNEE, DOSSIER_RAW, ecrire_csv,
                    fin_de_contrat, jours_ouvrables)

random.seed(2026)

# ---------------------------------------------------------------------------
# 1. Collaborateurs (30 profils fictifs)
# ---------------------------------------------------------------------------
# Schéma de contrats : "CDD12>CDI" = un CDD de 12 mois, puis passage en CDI.
# (prénom, nom, genre, département, poste, catégorie, bureau,
#  date d'embauche, schéma de contrats, date de sortie, motif de sortie)
D, RH, FIN, LOG = "Direction", "Ressources humaines", "Finance", "Logistique"
OPS, COM = "Opérations techniques", "Commercial et service client"
IT, SG = "Informatique", "Services généraux"

COLLABORATEURS = [
    ("Bienvenu", "Mukeba", "M", D, "Directeur(trice) pays", "Cadre", "Goma", "2017-03-01", "CDI", None, None),
    ("Clarisse", "Bisimwa", "F", D, "Assistant(e) de direction", "Agent de maîtrise", "Goma", "2021-06-01", "CDD12>CDD12>CDI", None, None),
    ("Neema", "Lukusa", "F", RH, "Responsable RH", "Cadre", "Goma", "2019-02-01", "CDD12>CDI", None, None),
    ("Josué", "Mirindi", "M", RH, "Chargé(e) RH", "Agent de maîtrise", "Goma", "2025-08-01", "CDD12>CDD12", None, None),
    ("Grâce", "Balume", "F", FIN, "Responsable financier(ère)", "Cadre", "Goma", "2018-09-03", "CDI", None, None),
    ("Patrick", "Amisi", "M", FIN, "Comptable", "Agent de maîtrise", "Goma", "2022-01-10", "CDD12>CDD12>CDI", None, None),
    ("Rachel", "Safari", "F", FIN, "Comptable", "Agent de maîtrise", "Bukavu", "2025-12-01", "CDD12", None, None),
    ("Olivier", "Kalume", "M", LOG, "Responsable logistique", "Cadre", "Goma", "2016-05-02", "CDI", None, None),
    ("Divine", "Shabani", "F", LOG, "Logisticien(ne)", "Agent de maîtrise", "Goma", "2024-11-04", "CDD12>CDD12", None, None),
    ("Dieudonné", "Byamungu", "M", LOG, "Chauffeur", "Exécution", "Goma", "2016-08-01", "CDI", None, None),
    ("Espoir", "Cirhuza", "M", LOG, "Chauffeur", "Exécution", "Bukavu", "2020-04-01", "CDD12>CDI", None, None),
    ("Héritier", "Kubuya", "M", LOG, "Chauffeur", "Exécution", "Beni", "2023-03-01", "CDD12>CDD12>CDI", None, None),
    ("Arsène", "Rusimbi", "M", LOG, "Magasinier(ère)", "Exécution", "Goma", "2021-10-01", "CDD12>CDI", None, None),
    ("Ruth", "Mushagalusa", "F", OPS, "Chef(fe) de projet technique", "Cadre", "Goma", "2019-07-01", "CDI", None, None),
    ("Elie", "Kalinda", "M", OPS, "Ingénieur(e) électricien(ne)", "Cadre", "Goma", "2020-01-06", "CDD12>CDI", None, None),
    ("Aline", "Zihindula", "F", OPS, "Ingénieur(e) électricien(ne)", "Cadre", "Bukavu", "2026-01-05", "CDD12", None, None),
    ("Baraka", "Mwamba", "M", OPS, "Technicien(ne) électricien(ne)", "Exécution", "Goma", "2022-05-02", "CDD12>CDD12>CDI", None, None),
    ("Tumaini", "Bahizi", "M", OPS, "Technicien(ne) électricien(ne)", "Exécution", "Goma", "2024-02-01", "CDD12>CDD12>CDI", None, None),
    ("Faraja", "Maombi", "F", OPS, "Technicien(ne) électricien(ne)", "Exécution", "Beni", "2023-09-01", "CDD12>CDD12>CDI", None, None),
    ("Riziki", "Barhakomerwa", "M", OPS, "Technicien(ne) électricien(ne)", "Exécution", "Bukavu", "2026-04-01", "CDD6", "2026-09-30", "Fin de CDD"),
    ("Imani", "Lwaboshi", "F", OPS, "Technicien(ne) électricien(ne)", "Exécution", "Goma", "2025-05-05", "CDD12>CDD6", None, None),
    ("Jospin", "Ilunga", "M", OPS, "Technicien(ne) électricien(ne)", "Exécution", "Beni", "2021-02-01", "CDD12>CDI", "2026-06-30", "Démission"),
    ("Furaha", "Nsimire", "F", COM, "Responsable commercial(e)", "Cadre", "Goma", "2018-02-05", "CDI", None, None),
    ("Gloire", "Kasereka", "M", COM, "Agent(e) commercial(e)", "Exécution", "Goma", "2023-06-01", "CDD12>CDI", None, None),
    ("Zawadi", "Muhindo", "F", COM, "Agent(e) commercial(e)", "Exécution", "Bukavu", "2024-07-01", "CDD12>CDD12>CDI", None, None),
    ("Pascal", "Paluku", "M", COM, "Agent(e) commercial(e)", "Exécution", "Beni", "2026-03-02", "CDD12", None, None),
    ("Merveille", "Kavira", "F", COM, "Chargé(e) service client", "Exécution", "Goma", "2022-09-01", "CDD12>CDI", "2026-03-15", "Démission"),
    ("Christelle", "Masika", "F", COM, "Chargé(e) service client", "Exécution", "Goma", "2026-04-15", "CDD12", None, None),
    ("Nadine", "Mapendo", "F", IT, "Administrateur(trice) systèmes", "Cadre", "Goma", "2020-10-01", "CDD12>CDI", None, None),
    ("Bahati", "Kambale", "M", SG, "Agent(e) de sécurité", "Exécution", "Goma", "2019-11-04", "CDI", None, None),
]

# Salaire mensuel brut FICTIF en USD au premier contrat (+5 % à chaque nouveau contrat).
SALAIRE_INITIAL = {
    "Directeur(trice) pays": 4200, "Assistant(e) de direction": 900,
    "Responsable RH": 1900, "Chargé(e) RH": 1100,
    "Responsable financier(ère)": 2100, "Comptable": 1000,
    "Responsable logistique": 1800, "Logisticien(ne)": 950,
    "Chauffeur": 450, "Magasinier(ère)": 500,
    "Chef(fe) de projet technique": 2300, "Ingénieur(e) électricien(ne)": 1600,
    "Technicien(ne) électricien(ne)": 650, "Responsable commercial(e)": 1900,
    "Agent(e) commercial(e)": 550, "Chargé(e) service client": 600,
    "Administrateur(trice) systèmes": 1500, "Agent(e) de sécurité": 400,
}


def date_naissance_fictive(date_embauche):
    """Date de naissance aléatoire : entre 21 et 45 ans à l'embauche."""
    age_embauche = random.randint(21, 45)
    annee = date_embauche.year - age_embauche
    return date(annee, random.randint(1, 12), random.randint(1, 28))


def construire_contrats(matricule, debut, schema, date_sortie, salaire):
    """Transforme un schéma comme 'CDD12>CDD12>CDI' en une suite de contrats."""
    contrats = []
    etapes = schema.split(">")
    for i, etape in enumerate(etapes):
        if i == 0:
            motif = "Embauche initiale"
        elif etape == "CDI":
            motif = "Passage en CDI"
        else:
            motif = "Renouvellement"
        fin = None if etape == "CDI" else fin_de_contrat(debut, int(etape[3:]))
        # Départ anticipé (démission) : le contrat se termine à la date de sortie.
        if date_sortie and (fin is None or date_sortie < fin):
            fin = date_sortie
        contrats.append({
            "matricule": matricule,
            "type_contrat": "CDI" if etape == "CDI" else "CDD",
            "duree_mois": "" if etape == "CDI" else etape[3:],
            "date_debut": debut,
            "date_fin": fin,
            "salaire_brut_mensuel_usd": salaire,
            "motif": motif,
        })
        if fin is None or fin == date_sortie:
            break
        debut = fin + timedelta(days=1)
        salaire = round(salaire * 1.05 / 10) * 10
    return contrats


collaborateurs, contrats = [], []
for n, (prenom, nom, genre, dept, poste, cat, bureau, embauche, schema, sortie, motif) in enumerate(COLLABORATEURS, start=1):
    matricule = f"EMP-{n:03d}"
    embauche = date.fromisoformat(embauche)
    sortie = date.fromisoformat(sortie) if sortie else None
    collaborateurs.append({
        "matricule": matricule, "prenom": prenom, "nom": nom, "genre": genre,
        "date_naissance": date_naissance_fictive(embauche),
        "departement": dept, "poste": poste, "categorie": cat, "bureau": bureau,
        "date_embauche": embauche,
        "statut": "Sorti" if sortie else "Actif",
        "date_sortie": sortie, "motif_sortie": motif,
        # Domaine .test : réservé, il ne peut correspondre à aucune vraie adresse.
        "email_professionnel": f"{matricule.lower()}@exemple-rh.test",
    })
    contrats += construire_contrats(matricule, embauche, schema, sortie, SALAIRE_INITIAL[poste])

for n, c in enumerate(contrats, start=1):
    c["contrat_id"] = f"CTR-{n:04d}"

# ---------------------------------------------------------------------------
# 2. Absences et congés (1er janvier -> 31 octobre 2026, + 2 congés planifiés)
# ---------------------------------------------------------------------------
def ajouter_jours_ouvrables(debut, nb):
    """Date de fin d'une absence de 'nb' jours ouvrables commençant à 'debut'."""
    d, compte = debut, 0
    while True:
        if d.weekday() < 5:
            compte += 1
            if compte == nb:
                return d
        d += timedelta(days=1)


def chevauche(debut, fin, deja_prises):
    return any(debut <= f and d <= fin for d, f in deja_prises)


absences = []


def ajouter_absence(matricule, type_abs, debut, fin, statut, deja_prises):
    deja_prises.append((debut, fin))
    absences.append({
        "matricule": matricule, "type_absence": type_abs,
        "date_debut": debut, "date_fin": fin,
        "nb_jours_ouvrables": jours_ouvrables(debut, fin), "statut": statut,
    })


def placer_au_hasard(matricule, type_abs, nb_jours, fenetre, deja_prises, statut="Approuvée"):
    """Cherche une période libre dans la fenêtre d'emploi du collaborateur."""
    debut_f, fin_f = fenetre
    for _ in range(200):
        debut = debut_f + timedelta(days=random.randint(0, (fin_f - debut_f).days))
        if debut.weekday() >= 5:
            continue
        fin = ajouter_jours_ouvrables(debut, nb_jours)
        if fin <= fin_f and not chevauche(debut, fin, deja_prises):
            ajouter_absence(matricule, type_abs, debut, fin, statut, deja_prises)
            return


for c in collaborateurs:
    m = c["matricule"]
    debut_f = max(DEBUT_ANNEE, c["date_embauche"])
    fin_f = min(DATE_REFERENCE, c["date_sortie"] or DATE_REFERENCE)
    prises = []

    # Cas fixés à la main pour illustrer des situations précises.
    if m == "EMP-019":  # congé de maternité : 14 semaines
        ajouter_absence(m, "Congé de maternité", date(2026, 3, 2), date(2026, 6, 7), "Approuvée", prises)
    if m in ("EMP-008", "EMP-014"):  # congés planifiés après la date de référence
        statut = "Approuvée" if m == "EMP-008" else "En attente"
        debut = date(2026, 12, 14) if m == "EMP-008" else date(2026, 11, 16)
        ajouter_absence(m, "Congé annuel", debut, ajouter_jours_ouvrables(debut, 10), statut, prises)
    if m in ("EMP-024", "EMP-011"):  # absence non justifiée d'un jour
        jour = date(2026, 5, 18) if m == "EMP-024" else date(2026, 8, 3)
        ajouter_absence(m, "Absence non justifiée", jour, jour, "Constatée", prises)

    duree_fenetre = (fin_f - debut_f).days
    if duree_fenetre >= 90:
        for _ in range(2 if duree_fenetre >= 200 else 1):
            placer_au_hasard(m, "Congé annuel", random.randint(5, 12), (debut_f, fin_f), prises)
    for _ in range(random.randint(0, 2)):
        placer_au_hasard(m, "Maladie", random.randint(1, 4), (debut_f, fin_f), prises)
    if random.random() < 0.2:
        placer_au_hasard(m, "Congé de circonstance", random.randint(2, 3), (debut_f, fin_f), prises)

# Une demande de congé refusée (n'a pas eu lieu, ne compte pas comme absence).
for a in absences:
    if a["matricule"] == "EMP-017" and a["type_absence"] == "Congé annuel":
        a["statut"] = "Refusée"
        break

absences.sort(key=lambda a: (a["date_debut"], a["matricule"]))
for n, a in enumerate(absences, start=1):
    a["absence_id"] = f"ABS-{n:04d}"

# ---------------------------------------------------------------------------
# 3. Stagiaires (6 profils fictifs)
# ---------------------------------------------------------------------------
STAGIAIRES = [
    ("Sifa", "Bagula", "F", "Gestion des ressources humaines", "Licence 3", RH, "EMP-003", "2026-02-02", "2026-04-30", 75, 16),
    ("Josaphat", "Kakule", "M", "Génie électrique", "Licence 3", OPS, "EMP-015", "2026-03-02", "2026-08-31", 75, 15),
    ("Ornella", "Bulambo", "F", "Comptabilité", "Licence 2", FIN, "EMP-005", "2026-06-01", "2026-08-28", 75, 14),
    ("Moïse", "Kambale", "M", "Génie électrique", "Master 1", OPS, "EMP-014", "2026-09-01", "2027-02-26", 100, None),
    ("Joëlle", "Namegabe", "F", "Sciences commerciales", "Licence 3", COM, "EMP-023", "2026-10-01", "2026-12-31", 75, None),
    ("Daniel", "Mastaki", "M", "Informatique de gestion", "Licence 3", IT, "EMP-029", "2026-11-02", "2027-01-29", 75, None),
]
stagiaires = [{
    "stagiaire_id": f"STG-{n:03d}", "prenom": p, "nom": nm, "genre": g,
    "etablissement": "Université partenaire (fictive)", "filiere": fil, "niveau": niv,
    "departement": dept, "encadreur_matricule": enc,
    "date_debut": deb, "date_fin": fin,
    "indemnite_mensuelle_usd": ind, "note_evaluation_sur_20": note,
} for n, (p, nm, g, fil, niv, dept, enc, deb, fin, ind, note) in enumerate(STAGIAIRES, start=1)]

# ---------------------------------------------------------------------------
# 4. Offres d'emploi et 10 candidatures fictives
# ---------------------------------------------------------------------------
offres = [
    {"offre_id": "OFF-2026-01", "intitule": "Assistant(e) RH", "departement": RH, "bureau": "Goma",
     "type_contrat": "CDD", "date_publication": "2026-08-17", "date_cloture": "2026-09-04",
     "motif": "Renfort de l'équipe RH"},
    {"offre_id": "OFF-2026-02", "intitule": "Technicien(ne) électricien(ne)", "departement": OPS, "bureau": "Bukavu",
     "type_contrat": "CDD", "date_publication": "2026-09-07", "date_cloture": "2026-09-25",
     "motif": "Remplacement (fin de CDD de EMP-020)"},
]

# Processus en 8 étapes : 1 Candidature reçue, 2 Présélection, 3 Convocation au test,
# 4 Test réalisé, 5 Vérification des références, 6 Décision du responsable RH,
# 7 Offre et contractualisation, 8 Intégration.
# Aucun champ « genre » ni autre caractéristique personnelle sensible : inutile au recrutement.
# (prénom, nom, offre, date de candidature, source, diplôme, années d'expérience,
#  autorisation de contacter les références, date de cette autorisation,
#  date de la réponse écrite au candidat, date de prise de fonction prévue)
CANDIDATURES = [
    ("Rebecca", "Nabintu", "OFF-2026-01", "2026-08-20", "Site carrières", "Licence en GRH", 2, "Oui", "2026-09-17", "", "2026-11-02"),
    ("Samuel", "Bwira", "OFF-2026-01", "2026-08-25", "Réseaux sociaux", "Licence en Sciences administratives", 3, "Oui", "2026-09-17", "2026-10-01", ""),
    ("Laetitia", "Chance", "OFF-2026-01", "2026-08-28", "Bouche-à-oreille", "Graduat en Secrétariat", 1, "", "", "2026-09-22", ""),
    ("Fiston", "Mulume", "OFF-2026-01", "2026-09-01", "Site carrières", "Licence en Économie", 0, "", "", "2026-09-10", ""),
    ("Annie", "Kitoko", "OFF-2026-01", "2026-09-03", "Réseaux sociaux", "Diplôme d'État", 4, "", "", "", ""),
    ("Trésor", "Bashizi", "OFF-2026-02", "2026-09-10", "Université", "Graduat en Électricité", 1, "", "", "", ""),
    ("Prisca", "Mulonda", "OFF-2026-02", "2026-09-12", "Site carrières", "Licence en Génie électrique", 2, "", "", "", ""),
    ("Kevin", "Murhula", "OFF-2026-02", "2026-09-15", "Bouche-à-oreille", "Graduat en Électricité", 3, "", "", "", ""),
    ("Junior", "Cikuru", "OFF-2026-02", "2026-09-22", "Réseaux sociaux", "Diplôme d'État (électricité)", 1, "", "", "2026-10-05", ""),
    ("Éloïse", "Mapenzi", "OFF-2026-02", "2026-09-24", "Université", "Graduat en Électricité", 0, "", "", "", ""),
]
candidatures = [{
    "candidature_id": f"CAND-{n:03d}", "offre_id": o, "prenom": p, "nom": nm,
    "date_candidature": dc, "source": src, "diplome": dip, "annees_experience": exp,
    "autorisation_references": aut, "date_autorisation_references": date_aut,
    "date_reponse_candidat": rep, "date_prise_fonction_prevue": pdf,
} for n, (p, nm, o, dc, src, dip, exp, aut, date_aut, rep, pdf) in enumerate(CANDIDATURES, start=1)]

# Journal des étapes : chaque ligne est une action enregistrée par une PERSONNE.
# (candidature, étape, date, résultat, intervenant, note de la grille sur 20, commentaire)
CRH, RRH, COMITE = "Chargé(e) RH", "Responsable RH", "Comité de recrutement"
JOURNAL = [
    ("CAND-001", 1, "2026-08-20", "Validée", CRH, None, "Dossier complet"),
    ("CAND-001", 2, "2026-09-08", "Validée", COMITE, 16, "Grille d'analyse du CV"),
    ("CAND-001", 3, "2026-09-10", "Validée", CRH, None, "Convocation envoyée pour le 17/09/2026"),
    ("CAND-001", 4, "2026-09-17", "Validée", COMITE, 16, "Test écrit et entretien structuré"),
    ("CAND-001", 5, "2026-09-24", "Validée", CRH, None, "2 références contactées avec l'accord écrit de la candidate"),
    ("CAND-001", 6, "2026-09-29", "Favorable", RRH, None, "Décision motivée versée au dossier"),
    ("CAND-001", 7, "2026-10-12", "Validée", RRH, None, "Contrat signé, prise de fonction le 02/11/2026"),
    ("CAND-002", 1, "2026-08-25", "Validée", CRH, None, "Dossier complet"),
    ("CAND-002", 2, "2026-09-08", "Validée", COMITE, 15, "Grille d'analyse du CV"),
    ("CAND-002", 3, "2026-09-10", "Validée", CRH, None, "Convocation envoyée pour le 17/09/2026"),
    ("CAND-002", 4, "2026-09-17", "Validée", COMITE, 13, "Test écrit et entretien structuré"),
    ("CAND-002", 5, "2026-09-24", "Validée", CRH, None, "2 références contactées avec l'accord écrit du candidat"),
    ("CAND-002", 6, "2026-09-29", "Défavorable", RRH, None, "Décision motivée versée au dossier"),
    ("CAND-003", 1, "2026-08-28", "Validée", CRH, None, "Dossier complet"),
    ("CAND-003", 2, "2026-09-08", "Validée", COMITE, 13, "Grille d'analyse du CV"),
    ("CAND-003", 3, "2026-09-10", "Validée", CRH, None, "Convocation envoyée pour le 17/09/2026"),
    ("CAND-003", 4, "2026-09-17", "Non retenu(e)", COMITE, 9, "Compétences attendues non démontrées au test"),
    ("CAND-004", 1, "2026-09-01", "Validée", CRH, None, "Dossier complet"),
    ("CAND-004", 2, "2026-09-08", "Non retenu(e)", COMITE, 10, "Expérience requise non démontrée"),
    ("CAND-005", 1, "2026-09-03", "Validée", CRH, None, "Dossier complet"),
    ("CAND-005", 2, "2026-09-08", "Non retenu(e)", COMITE, 8, "Diplôme requis absent"),
    ("CAND-006", 1, "2026-09-10", "Validée", CRH, None, "Dossier complet"),
    ("CAND-006", 2, "2026-10-02", "Validée", COMITE, 14, "Grille d'analyse du CV"),
    ("CAND-006", 3, "2026-10-26", "Validée", CRH, None, "Convocation envoyée pour le 04/11/2026"),
    ("CAND-007", 1, "2026-09-12", "Validée", CRH, None, "Dossier complet"),
    ("CAND-007", 2, "2026-10-02", "Validée", COMITE, 17, "Grille d'analyse du CV"),
    ("CAND-007", 3, "2026-10-26", "Validée", CRH, None, "Convocation envoyée pour le 04/11/2026"),
    ("CAND-008", 1, "2026-09-15", "Validée", CRH, None, "Dossier complet"),
    ("CAND-008", 2, "2026-10-02", "Validée", COMITE, 12, "Grille d'analyse du CV"),
    ("CAND-008", 3, "2026-10-26", "Validée", CRH, None, "Convocation envoyée pour le 05/11/2026"),
    ("CAND-009", 1, "2026-09-22", "Validée", CRH, None, "Dossier complet"),
    ("CAND-009", 2, "2026-10-02", "Non retenu(e)", COMITE, 9, "Qualification technique requise absente"),
    ("CAND-010", 1, "2026-09-24", "Validée", CRH, None, "Dossier complet"),
    ("CAND-010", 2, "2026-10-02", "Validée", COMITE, 13, "Grille d'analyse du CV"),
    ("CAND-010", 3, "2026-10-26", "Validée", CRH, None, "Convocation envoyée pour le 05/11/2026"),
    ("CAND-010", 4, "2026-10-28", "Désistement", CRH, None, "La candidate a accepté un autre poste"),
]
journal_recrutement = [{
    "evenement_id": f"EVT-{n:03d}", "candidature_id": c, "etape": e, "date": d, "resultat": r,
    "intervenant": i, "note_grille_sur_20": note, "commentaire": com,
} for n, (c, e, d, r, i, note, com) in enumerate(JOURNAL, start=1)]

# Planning des tests et entretiens (lieux et panels fictifs).
EPREUVE = "Test écrit (60 min) puis entretien structuré (45 min)"
GOMA = "Bureau de Goma, salle de réunion (adresse fictive)"
BUKAVU = "Bureau de Bukavu, salle de formation (adresse fictive)"
PANEL_1 = "Neema Lukusa (Responsable RH) ; Josué Mirindi (Chargé RH)"
PANEL_2 = ("Neema Lukusa (Responsable RH, en visioconférence) ; Ruth Mushagalusa (Cheffe de projet technique) ; "
           "Aline Zihindula (Ingénieure électricienne)")
PLANNING = [
    ("OFF-2026-01", "CAND-001", "2026-09-17", "08:30", "10:30", GOMA, PANEL_1, "Confirmé"),
    ("OFF-2026-01", "CAND-002", "2026-09-17", "11:00", "13:00", GOMA, PANEL_1, "Confirmé"),
    ("OFF-2026-01", "CAND-003", "2026-09-17", "14:00", "16:00", GOMA, PANEL_1, "Confirmé"),
    ("OFF-2026-02", "CAND-006", "2026-11-04", "08:30", "10:30", BUKAVU, PANEL_2, "Confirmé"),
    ("OFF-2026-02", "CAND-007", "2026-11-04", "11:00", "13:00", BUKAVU, PANEL_2, "Confirmé"),
    ("OFF-2026-02", "CAND-008", "2026-11-05", "08:30", "10:30", BUKAVU, PANEL_2, "Confirmé"),
    ("OFF-2026-02", "CAND-010", "2026-11-05", "11:00", "13:00", BUKAVU, PANEL_2, "Annulé (désistement)"),
]
planning_entretiens = [{
    "creneau_id": f"PLN-{n:02d}", "offre_id": o, "candidature_id": c, "date": d,
    "heure_debut": hd, "heure_fin": hf, "epreuve": EPREUVE, "lieu": lieu, "panel": panel, "statut": st,
} for n, (o, c, d, hd, hf, lieu, panel, st) in enumerate(PLANNING, start=1)]

# ---------------------------------------------------------------------------
# 5. Écriture des fichiers
# ---------------------------------------------------------------------------
print("Génération des données fictives dans data/raw/ :")
ecrire_csv(DOSSIER_RAW / "collaborateurs.csv", collaborateurs,
           ["matricule", "prenom", "nom", "genre", "date_naissance", "departement", "poste",
            "categorie", "bureau", "date_embauche", "statut", "date_sortie", "motif_sortie",
            "email_professionnel"])
ecrire_csv(DOSSIER_RAW / "contrats.csv", contrats,
           ["contrat_id", "matricule", "type_contrat", "duree_mois", "date_debut", "date_fin",
            "salaire_brut_mensuel_usd", "motif"])
ecrire_csv(DOSSIER_RAW / "absences.csv", absences,
           ["absence_id", "matricule", "type_absence", "date_debut", "date_fin",
            "nb_jours_ouvrables", "statut"])
ecrire_csv(DOSSIER_RAW / "stagiaires.csv", stagiaires, list(stagiaires[0].keys()))
ecrire_csv(DOSSIER_RAW / "offres_emploi.csv", offres, list(offres[0].keys()))
ecrire_csv(DOSSIER_RAW / "candidatures.csv", candidatures, list(candidatures[0].keys()))
ecrire_csv(DOSSIER_RAW / "recrutement_etapes.csv", journal_recrutement, list(journal_recrutement[0].keys()))
ecrire_csv(DOSSIER_RAW / "planning_entretiens.csv", planning_entretiens, list(planning_entretiens[0].keys()))
print("Terminé. Rappel : toutes ces données sont synthétiques.")
