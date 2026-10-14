"""
Génère le rapport mensuel RH (Markdown) à partir des données sources :
documents/rapports/rapport_mensuel_rh_AAAA-MM.md

Aucun chiffre n'est saisi à la main : tout vient des modules RH, recrutement
et tableau de bord. DONNÉES FICTIVES - Portfolio personnel, non officiel de Nuru.

Utilisation (depuis la racine du projet) :
    python documents/generer_rapport_mensuel.py
"""
import sys
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
sys.path.insert(0, str(DOSSIER.parent / "analysis"))

import insights as ins  # noqa: E402
import recrutement as rc  # noqa: E402
import suivi_rh as rh  # noqa: E402
import tableau_de_bord as tb  # noqa: E402
from commun import DATE_REFERENCE  # noqa: E402

MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
           "septembre", "octobre", "novembre", "décembre"]


def fdate(d):
    return f"{d:%d/%m/%Y}" if d else "sans date"


def pluriel(n, singulier, pluriel_):
    return f"{n} {singulier if n <= 1 else pluriel_}"


def rapport(jour):
    d_rh, d_rec = rh.charger_donnees(), rc.charger_donnees()
    tdb = tb.donnees_tableau_de_bord(jour)
    mois_cle = jour.strftime("%Y-%m")
    mois_txt = f"{MOIS_FR[jour.month - 1]} {jour.year}"
    mensuel = {m["mois"]: m for m in rh.effectifs_mensuels(d_rh, jour)}[mois_cle]
    depuis_janvier = rh.effectifs_mensuels(d_rh, jour)
    absences_mois = {c: n for (m, c), n in rh.jours_absence_par_mois(d_rh, jour).items() if m == mois_cle}
    ech = rh.echeances(d_rh, jour)
    stg = rh.suivi_stagiaires(d_rh, jour)
    ind_rec = rc.indicateurs(d_rec, jour)
    prioritaires = [a for a in tdb["actions"] if a["urgence"] in (tb.EN_RETARD, tb.SOUS_7)]

    L = [f"# Rapport mensuel RH : {mois_txt}",
         "",
         "> Rapport généré automatiquement à partir de données **fictives**. Portfolio personnel, "
         "ce n'est pas un document officiel de Nuru.",
         "",
         f"**Situation arrêtée au {fdate(jour)}.** Destinataire : responsable RH (exemple).",
         "",
         "## 1. Synthèse",
         "",
         f"- Effectif actif en fin de mois : **{mensuel['effectif_fin']}**, dont {tdb['part_cdd_pct']} % en CDD.",
         f"- Mouvements du mois : {pluriel(mensuel['entrees'], 'entrée', 'entrées')}, "
         f"{pluriel(mensuel['sorties'], 'sortie', 'sorties')}.",
         f"- CDD arrivant à échéance sous 30 jours : **{len(tdb['contrats_30'])}**.",
         f"- Jours ouvrables d'absence réalisés dans le mois : **{sum(absences_mois.values())}**.",
         f"- Recrutement : {ind_rec['candidatures']} candidatures suivies, {ind_rec['en_cours']} dossiers en cours, "
         f"{pluriel(ind_rec['postes_pourvus'], 'poste pourvu', 'postes pourvus')}.",
         f"- Actions prioritaires (en retard ou sous 7 jours) : **{len(prioritaires)}**.",
         "",
         "### Points d'attention (insights)",
         ""]
    for i in ins.calculer_insights(jour):
        L.append(f"- **{i['niveau']} · {i['titre']} ({i['indicateur']})** : {i['constat']} *Piste : {i['piste']}*")
    L += ["",
         "Les pistes sont des suggestions ; la décision appartient au responsable RH.",
         "",
         "## 2. Effectifs",
         "",
         "| Département | CDI | CDD | Total |",
         "|---|---|---|---|"]
    for dep, v in tdb["effectifs_departements"].items():
        L.append(f"| {dep} | {v['CDI']} | {v['CDD']} | {v['CDI'] + v['CDD']} |")
    L += ["",
          f"Depuis le 1er janvier : {sum(m['entrees'] for m in depuis_janvier)} entrées et "
          f"{sum(m['sorties'] for m in depuis_janvier)} sorties ; effectif passé de "
          f"{depuis_janvier[0]['effectif_debut']} à {mensuel['effectif_fin']}.",
          "",
          "## 3. Contrats à échéance (90 jours)",
          "",
          "| Matricule | Poste | Fin du contrat | Jours restants | Niveau |",
          "|---|---|---|---|---|"]
    for l in ech:
        if l["jours_restants"] is not None and l["jours_restants"] <= 90:
            L.append(f"| {l['matricule']} | {l['poste']} | {l['date_fin'][8:10]}/{l['date_fin'][5:7]}/{l['date_fin'][:4]} "
                     f"| {l['jours_restants']} | {l['alerte']} |")
    L += ["",
          "Ces alertes sont indicatives : **la décision (renouvellement ou fin de contrat) appartient au responsable RH.**",
          "",
          "## 4. Absences et congés du mois",
          "",
          "| Catégorie | Jours ouvrables |",
          "|---|---|"]
    for cat, n in sorted(absences_mois.items(), key=lambda kv: -kv[1]):
        L.append(f"| {cat} | {n} |")
    L += ["",
          f"Demandes de congé en attente de décision : {tdb['absences']['en_attente']}. "
          "Les motifs de santé sont regroupés sous une catégorie confidentielle ; aucun détail médical n'est communiqué.",
          "",
          "## 5. Stagiaires",
          ""]
    for statut in ("En cours", "À venir", "Terminé"):
        noms = [f"{s['stagiaire_id']} ({s['departement']})" for s in stg if s["statut"] == statut]
        L.append(f"- **{statut}** : {', '.join(noms) if noms else 'aucun'}")
    L += ["",
          "## 6. Recrutement",
          "",
          "| Étape | " + " | ".join(tdb["offres"].values()) + " |",
          "|---|" + "---|" * len(tdb["offres"])]
    for k, lib in rc.ETAPES.items():
        L.append(f"| {k}. {lib} | " + " | ".join(str(tdb["entonnoir"][o][k]) for o in tdb["offres"]) + " |")
    delai = ind_rec["delai_moyen_decision_jours"]
    L += ["",
          f"Délai moyen entre la candidature et la décision du responsable RH : "
          f"{'non calculable' if delai is None else f'{delai} jours'}. "
          "Toutes les décisions de recrutement ont été prises par des personnes.",
          "",
          "## 7. Actions prioritaires",
          "",
          "| Urgence | Échéance | Domaine | Objet | Action | Responsable |",
          "|---|---|---|---|---|---|"]
    for a in prioritaires:
        L.append(f"| {a['urgence']} | {fdate(a['echeance'])} | {a['domaine']} | {a['objet']} | {a['action']} | {a['responsable']} |")
    L += ["",
          "## 8. Méthode",
          "",
          "Chiffres calculés par `documents/generer_rapport_mensuel.py` à partir des fichiers de `data/raw/`, "
          "avec les mêmes règles que le module de suivi RH et le tableau de bord. Jours d'absence = jours "
          "ouvrables du lundi au vendredi, jours fériés non déduits.",
          ""]
    return "\n".join(L)


if __name__ == "__main__":
    jour = DATE_REFERENCE
    sortie = DOSSIER / "rapports" / f"rapport_mensuel_rh_{jour:%Y-%m}.md"
    sortie.write_text(rapport(jour), encoding="utf-8")
    print(f"Rapport généré : documents/rapports/{sortie.name}")
