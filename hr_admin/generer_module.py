"""
Génère le module de consultation RH : hr_admin/module_suivi_rh.html
(une page autonome, sans connexion Internet, à ouvrir dans un navigateur).

DONNÉES FICTIVES - Portfolio personnel, non officiel de Nuru.

Utilisation (depuis la racine du projet) :
    python hr_admin/generer_module.py                    # date de référence 31/10/2026
    python hr_admin/generer_module.py --date 2026-12-01  # test : autre date de consultation
"""
import argparse
import sys
from datetime import date
from html import escape
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
sys.path.insert(0, str(DOSSIER.parent / "analysis"))

import suivi_rh as rh  # noqa: E402
from commun import DATE_REFERENCE  # noqa: E402
from page_html import badge, fdate, page, recherche, tableau, tuile  # noqa: E402

# Badge d'alerte : (classe CSS, icône). L'icône et le libellé portent le sens,
# la couleur n'est qu'un renfort.
BADGES = {
    rh.ECHU: ("critique", "⛔"), rh.URGENT: ("critique", "⚠"),
    rh.A_PREPARER: ("serieux", "◷"), rh.A_SURVEILLER: ("vigilance", "◔"),
    rh.RAS: ("bon", "✓"), rh.SANS_ECHEANCE: ("neutre", "–"),
}


def construire(jour):
    d = rh.charger_donnees()
    ind = rh.indicateurs(d, jour)
    e = escape

    # --- Vue d'ensemble -------------------------------------------------------
    tuiles = "".join([
        tuile("Effectif actif", ind["effectif_actif"], f"dont {ind['part_cdd_pct']} % en CDD"),
        tuile("Contrats à échéance ≤ 30 jours", ind["echeances_30"], "action urgente à étudier"),
        tuile("Échéance entre 31 et 60 jours", ind["echeances_60"], "à préparer"),
        tuile("Échéance entre 61 et 90 jours", ind["echeances_90"], "à surveiller"),
        tuile("Contrats échus non régularisés", ind["echus"], "doit rester à 0"),
        tuile("Jours d'absence réalisés", ind["jours_absence_realises"], f"depuis le 01/01/{jour.year}, jours ouvrables"),
        tuile("Demandes de congé en attente", ind["demandes_en_attente"], "à traiter"),
        tuile("Stagiaires en cours", ind["stagiaires_en_cours"], f"{ind['stagiaires_a_venir']} à venir"),
        tuile(f"Entrées / sorties {jour.year}", f"{ind['entrees_annee']} / {ind['sorties_annee']}", "depuis le 1er janvier"),
    ])

    # --- Registre du personnel --------------------------------------------------
    registre = rh.registre_personnel(d, jour)
    t_registre = tableau(
        ["Matricule", "Nom", "Poste", "Département", "Bureau", "Embauche", "Statut", "Contrat", "Sortie"],
        [[e(r["matricule"]), e(r["nom"]), e(r["poste"]), e(r["departement"]), e(r["bureau"]),
          fdate(r["date_embauche"]), e(r["statut"]), e(r["type_contrat"]), fdate(r["date_sortie"])]
         for r in registre])

    # --- Contrats -----------------------------------------------------------------
    contrats = rh.tableau_contrats(d, jour)
    t_contrats = tableau(
        ["N° contrat", "Matricule", "Nom", "Type", "Début", "Fin", "Motif", "Statut"],
        [[e(c["contrat_id"]), e(c["matricule"]), e(c["nom"]), e(c["type_contrat"]),
          fdate(c["date_debut"]), fdate(c["date_fin"]) or "Indéterminée", e(c["motif"]), e(c["statut"])]
         for c in contrats])

    # --- Échéances ------------------------------------------------------------------
    ech = rh.echeances(d, jour)
    t_ech = tableau(
        ["Alerte", "Matricule", "Nom", "Poste", "Département", "Contrat", "Fin du contrat", "Jours restants"],
        [[badge(l["alerte"], *BADGES[l["alerte"]]), e(l["matricule"]), e(l["nom"]), e(l["poste"]),
          e(l["departement"]), e(l["type_contrat"]), fdate(l["date_fin"]) or "Indéterminée",
          "" if l["jours_restants"] is None else l["jours_restants"]]
         for l in ech], num=(7,))

    # --- Absences -------------------------------------------------------------------
    par_mois = rh.jours_absence_par_mois(d, jour)
    categories = [c for c in ("Congé annuel", "Congé de circonstance", rh.CONFIDENTIEL, "Absence non justifiée")
                  if any(k[1] == c for k in par_mois)]
    mois = sorted({k[0] for k in par_mois})
    lignes_mois = [[m] + [par_mois.get((m, c), 0) for c in categories] + [sum(par_mois.get((m, c), 0) for c in categories)]
                   for m in mois]
    totaux = ["Total"] + [sum(l[i + 1] for l in lignes_mois) for i in range(len(categories))] + [sum(par_mois.values())]
    t_abs_mois = tableau(["Mois"] + categories + ["Total"], lignes_mois,
                         num=tuple(range(1, len(categories) + 2)), pied=totaux)
    t_abs = tableau(
        ["N°", "Matricule", "Nom", "Catégorie", "Début", "Fin", "Jours ouvrables", "Statut"],
        [[e(a["absence_id"]), e(a["matricule"]), e(a["nom"]), e(a["categorie"]),
          fdate(a["date_debut"]), fdate(a["date_fin"]), a["nb_jours_ouvrables"], e(a["statut"])]
         for a in rh.liste_absences(d)], num=(6,))

    # --- Stagiaires -------------------------------------------------------------------
    t_stg = tableau(
        ["N°", "Nom", "Filière", "Niveau", "Département", "Encadreur", "Début", "Fin", "Statut", "Évaluation finale"],
        [[e(s["stagiaire_id"]), e(s["nom"]), e(s["filiere"]), e(s["niveau"]), e(s["departement"]),
          e(s["encadreur"]), fdate(s["date_debut"]), fdate(s["date_fin"]),
          (badge(f"En cours, fin dans {s['jours_avant_fin']} j", "vigilance", "◔") if s["fin_proche"] else e(s["statut"])),
          e(s["evaluation_finale"])]
         for s in rh.suivi_stagiaires(d, jour)])

    # --- Effectifs ----------------------------------------------------------------------
    eff = rh.effectifs_par_departement(d, jour)
    t_eff = tableau(
        ["Département", "CDI", "CDD", "Total"],
        [[e(dep), v["CDI"], v["CDD"], v["CDI"] + v["CDD"]] for dep, v in eff.items()],
        num=(1, 2, 3),
        pied=["Total", sum(v["CDI"] for v in eff.values()), sum(v["CDD"] for v in eff.values()),
              ind["effectif_actif"]])
    t_mensuel = tableau(
        ["Mois", "Effectif début", "Entrées", "Sorties", "Effectif fin"],
        [[m["mois"], m["effectif_debut"], m["entrees"], m["sorties"], m["effectif_fin"]]
         for m in rh.effectifs_mensuels(d, jour)], num=(1, 2, 3, 4))

    avertissement_date = ""
    if jour > DATE_REFERENCE:
        avertissement_date = (f'<p class="note attention"><strong>Date de test.</strong> Les données fictives '
                              f's\'arrêtent au {DATE_REFERENCE:%d/%m/%Y}. Après cette date, les absences et les '
                              f'mouvements de personnel ne sont pas renseignés : seules les alertes de contrats '
                              f'et de stages sont significatives.</p>')

    onglets = [
        ("vue", "Vue d'ensemble", f"""
            <div class="tuiles">{tuiles}</div>
            <h2>Effectifs par département et type de contrat</h2>{t_eff}"""),
        ("registre", "Registre du personnel", f"""
            {recherche('registre')}{t_registre}
            <p class="note">Champs volontairement absents : date de naissance, coordonnées, salaire, motif de sortie.</p>"""),
        ("contrats", "Contrats", f"{recherche('contrats')}{t_contrats}"),
        ("echeances", "Échéances", f"""
            <p class="note decision"><strong>Alerte indicative.</strong> Ce module signale les contrats
            dont la fin approche (seuils de 30, 60 et 90 jours). <strong>Toute décision contractuelle
            (renouvellement, fin de contrat, passage en CDI) appartient au responsable RH</strong>,
            après vérification du dossier et des règles applicables du Code du travail de la RDC.</p>
            {recherche('echeances')}{t_ech}"""),
        ("absences", "Absences et congés", f"""
            <p class="note">Par confidentialité, les absences pour raison de santé (maladie, maternité)
            sont regroupées sous « {rh.CONFIDENTIEL} ». Aucune information médicale n'est enregistrée
            ni affichée. Seules les absences approuvées ou constatées sont comptées.</p>
            <h2>Jours ouvrables d'absence par mois</h2>{t_abs_mois}
            <h2>Détail des absences et demandes</h2>{recherche('absences')}{t_abs}"""),
        ("stagiaires", "Stagiaires", f"""
            {recherche('stagiaires')}{t_stg}
            <p class="note">La note d'évaluation n'est pas affichée : seul l'état de l'évaluation est indiqué.</p>"""),
        ("effectifs", "Effectifs", f"""
            <h2>Par département et type de contrat</h2>{t_eff}
            <h2>Registre mensuel {jour.year}</h2>{t_mensuel}
            <p class="note">Une personne sortie le jour J n'est plus comptée à la fin du jour J.</p>"""),
    ]
    sous_titre = f"NURU HR DIGITAL PORTFOLIO · situation au <strong>{jour:%d/%m/%Y}</strong> · consultation seule"
    return page("Suivi administratif RH", sous_titre, onglets, avant_onglets=avertissement_date)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Génère le module de suivi administratif RH.")
    parser.add_argument("--date", help="date de consultation AAAA-MM-JJ (par défaut : 2026-10-31)")
    args = parser.parse_args()
    jour = date.fromisoformat(args.date) if args.date else DATE_REFERENCE
    # La version de référence est conservée ; une date de test produit un fichier séparé.
    nom = "module_suivi_rh.html" if jour == DATE_REFERENCE else f"module_suivi_rh_test_{jour}.html"
    sortie = DOSSIER / nom
    sortie.write_text(construire(jour), encoding="utf-8")
    print(f"Module généré : hr_admin/{nom} (situation au {jour:%d/%m/%Y})")
