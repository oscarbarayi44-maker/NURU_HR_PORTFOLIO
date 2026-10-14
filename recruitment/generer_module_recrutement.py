"""
Génère le module de suivi du recrutement et ses documents :
- recruitment/module_recrutement.html          page de consultation (7 onglets)
- recruitment/planning_entretiens.md           planning des tests et entretiens
- recruitment/convocations/*.txt               courriels de convocation remplis
- recruitment/checklist_integration_*.md       checklist datée pour chaque recrutement
- documents/modeles_courriers/checklist_integration_modele.md   modèle vierge

DONNÉES FICTIVES - Portfolio personnel, non officiel de Nuru.
Le module ne prend aucune décision : il affiche ce que les personnes ont enregistré.

Utilisation (depuis la racine du projet) :
    python recruitment/generer_module_recrutement.py
    python recruitment/generer_module_recrutement.py --date 2026-11-10   # simuler une autre date
"""
import argparse
import sys
from datetime import date
from html import escape
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
sys.path.insert(0, str(DOSSIER.parent / "analysis"))

import recrutement as rc  # noqa: E402
from commun import DATE_REFERENCE, RACINE, en_date  # noqa: E402
from page_html import MENTION_FICTIVE, badge, fdate, page, recherche, tableau, tuile  # noqa: E402

BADGES_STATUT = {
    rc.STATUT_EN_COURS: ("info", "▸"), rc.STATUT_NON_RETENU: ("neutre", "✕"),
    rc.STATUT_DESISTEMENT: ("neutre", "↩"), rc.STATUT_RECRUTE: ("bon", "✓"), rc.STATUT_INTEGRE: ("bon", "✓"),
}
QUI_ENREGISTRE = {
    1: "Chargé(e) RH", 2: "Comité de recrutement (grille d'analyse du CV)", 3: "Chargé(e) RH",
    4: "Comité de recrutement (grille de test et d'entretien)",
    5: "Chargé(e) RH, uniquement avec l'autorisation écrite du candidat",
    6: "Responsable RH, exclusivement", 7: "Responsable RH", 8: "Chargé(e) RH",
}
AVERTISSEMENT_DECISION = (
    '<p class="note decision"><strong>Aucune décision automatisée.</strong> Ce module ne note pas, '
    "ne classe pas et ne sélectionne pas les candidats ; il n'utilise aucune IA. Chaque étape est "
    "enregistrée par une personne (chargé(e) RH, comité de recrutement, responsable RH). Le module "
    "contrôle le respect du processus et rappelle la prochaine tâche administrative. Aucune "
    "caractéristique personnelle sensible (genre, âge, origine, santé, situation familiale) n'est collectée.</p>")


# --- Documents Markdown / texte ---------------------------------------------------------
def planning_markdown(d, jour):
    offres = {o["offre_id"]: o for o in d["offres_emploi"]}
    noms = {c["candidature_id"]: f"{c['prenom']} {c['nom']}" for c in d["candidatures"]}
    lignes = [f"# Planning des tests et entretiens\n",
              f"> {MENTION_FICTIVE}\n",
              f"Situation au {jour:%d/%m/%Y}. Chaque créneau comprend : {d['planning_entretiens'][0]['epreuve']}.\n"]
    for offre_id in sorted({c["offre_id"] for c in d["planning_entretiens"]}):
        creneaux = sorted((c for c in d["planning_entretiens"] if c["offre_id"] == offre_id),
                          key=lambda c: (c["date"], c["heure_debut"]))
        o = offres[offre_id]
        lignes += [f"\n## {o['intitule']} ({offre_id}), {o['bureau']}\n",
                   f"**Lieu :** {creneaux[0]['lieu']}  ",
                   f"**Panel :** {creneaux[0]['panel']}\n",
                   "| Créneau | Date | Horaire | Candidat(e) | Statut |", "|---|---|---|---|---|"]
        lignes += [f"| {c['creneau_id']} | {rc.date_longue(en_date(c['date']))} | {c['heure_debut']} à {c['heure_fin']} "
                   f"| {noms[c['candidature_id']]} ({c['candidature_id']}) | {c['statut']} |" for c in creneaux]
    lignes += ["\n## Rappels pour le panel\n",
               "- Utiliser la même grille d'entretien et les mêmes questions pour chaque candidat(e).",
               "- Noter uniquement des éléments liés aux compétences du poste.",
               "- Ne poser aucune question sur la situation familiale, la santé, la religion, l'origine ou l'âge.",
               "- La décision finale est prise par le responsable RH (étape 6), pas par la grille."]
    return "\n".join(lignes) + "\n"


def checklist_markdown(candidature, offre, prise):
    lignes = [f"# Checklist d'intégration : {candidature['prenom']} {candidature['nom']}\n",
              f"> {MENTION_FICTIVE}\n",
              f"- **Poste :** {offre['intitule']} ({offre['bureau']})",
              f"- **Prise de fonction (J) :** {rc.date_longue(prise)}",
              "- **Fin de période d'essai :** date à reporter selon le contrat signé ; le bilan et la "
              "décision appartiennent au responsable RH.\n"]
    moment = None
    for item in rc.generer_checklist(prise):
        if item["moment"] != moment:
            moment = item["moment"]
            lignes.append(f"\n## {moment}\n")
        lignes.append(f"- [ ] **{item['date']:%d/%m/%Y}** ({item['repere']}) : {item['tache']} "
                      f"(*{item['responsable']}*)")
    return "\n".join(lignes) + "\n"


def checklist_modele_markdown():
    lignes = ["# Modèle de checklist d'intégration\n", f"> {MENTION_FICTIVE}\n",
              "J = date de prise de fonction. Une date qui tombe un week-end est ramenée au jour ouvrable "
              "précédent (avant l'arrivée) ou suivant (après l'arrivée).\n",
              "| Moment | Repère | Tâche | Responsable |", "|---|---|---|---|"]
    lignes += [f"| {m} | {'J' if dec == 0 else f'J{dec:+d}'} | {t} | {r} |"
               for m, dec, t, r in rc.CHECKLIST_INTEGRATION]
    lignes.append("| Fin de période d'essai | selon contrat | Bilan de période d'essai ; décision du responsable RH | Responsable RH |")
    return "\n".join(lignes) + "\n"


# --- Page HTML ---------------------------------------------------------------------------
def construire(d, jour):
    e = escape
    etats = rc.tous_les_etats(d, jour)
    ind = rc.indicateurs(d, jour)
    offres = {o["offre_id"]: o for o in d["offres_emploi"]}

    tuiles = "".join([
        tuile("Candidatures", ind["candidatures"], f"{len(offres)} offres"),
        tuile("Dossiers en cours", ind["en_cours"], "processus non terminé"),
        tuile("Actions à mener", ind["actions_a_mener"], "voir l'onglet Candidatures"),
        tuile("Alertes de délai", ind["alertes"], "relance ou échéance dépassée"),
        tuile("Tests à venir", ind["tests_a_venir"], "créneaux confirmés"),
        tuile("Postes pourvus", ind["postes_pourvus"], "contrat signé"),
        tuile("Délai moyen jusqu'à la décision RH",
              "–" if ind["delai_moyen_decision_jours"] is None else f"{ind['delai_moyen_decision_jours']} j",
              "de la candidature à l'étape 6"),
    ])
    par_offre = {o: rc.entonnoir(d, jour, o) for o in offres}
    total = rc.entonnoir(d, jour)
    t_entonnoir = tableau(["Étape"] + [f"{offres[o]['intitule']} ({o})" for o in offres] + ["Total"],
                          [[f"{k}. {e(lib)}"] + [par_offre[o][k] for o in offres] + [total[k]]
                           for k, lib in rc.ETAPES.items()], num=tuple(range(1, len(offres) + 2)))

    t_cands = tableau(
        ["N°", "Candidat(e)", "Offre", "Étape actuelle", "Statut", "Prochaine action", "Responsable", "Échéance", "Alerte"],
        [[e(s["candidature_id"]), e(s["nom"]), e(s["offre_id"]), f"{s['etape']}/8 · {e(s['etape_libelle'])}",
          badge(s["statut"], *BADGES_STATUT[s["statut"]]), f'<span class="texte">{e(s["prochaine_action"])}</span>',
          e(s["responsable"]), fdate(s["echeance"]),
          badge(s["alerte"], "vigilance", "⚠") if s["alerte"] else ""] for s in etats])

    colonnes_dates = list(etats[0]["dates"])
    t_dates = tableau(["N°", "Candidat(e)"] + colonnes_dates,
                      [[e(s["candidature_id"]), e(s["nom"])] + [fdate(v) for v in s["dates"].values()] for s in etats])

    historiques = "".join(
        f"<details><summary>{e(s['candidature_id'])} · {e(s['nom'])} · {e(s['statut'])}</summary>"
        + tableau(["Étape", "Date", "Résultat", "Enregistré par", "Grille (sur 20)", "Commentaire"],
                  [[f"{h['etape']}. {e(rc.ETAPES[h['etape']])}", fdate(h["date"]), e(h["resultat"]),
                    e(h["intervenant"]), h["note_grille_sur_20"], e(h["commentaire"])] for h in s["historique"]],
                  num=(4,))
        + "</details>" for s in etats)

    noms = {c["candidature_id"]: f"{c['prenom']} {c['nom']}" for c in d["candidatures"]}
    t_planning = tableau(
        ["Créneau", "Offre", "Date", "Horaire", "Candidat(e)", "Lieu", "Panel", "Statut"],
        [[e(c["creneau_id"]), e(c["offre_id"]), e(rc.date_longue(en_date(c["date"]))),
          f"{c['heure_debut']} à {c['heure_fin']}", e(noms[c["candidature_id"]]), e(c["lieu"]),
          f'<span class="texte">{e(c["panel"])}</span>', e(c["statut"])]
         for c in sorted(d["planning_entretiens"], key=lambda c: (c["date"], c["heure_debut"]))])

    exemple = next(c for c in d["candidatures"] if c["candidature_id"] == "CAND-006")
    courriel = rc.generer_convocation(exemple, offres[exemple["offre_id"]], rc.creneau_de(d, "CAND-006"))
    recrue = next(c for c in d["candidatures"] if c["date_prise_fonction_prevue"])
    checklist = "".join(
        f"<li>☐ <strong>{i['date']:%d/%m/%Y}</strong> ({i['repere']}, {e(i['moment'])}) : {e(i['tache'])} "
        f"<em>({e(i['responsable'])})</em></li>"
        for i in rc.generer_checklist(en_date(recrue["date_prise_fonction_prevue"])))

    t_processus = tableau(["Étape", "Résultats possibles", "Enregistrée par"],
                          [[f"{k}. {e(lib)}", e(" / ".join(sorted(rc.RESULTATS_AUTORISES[k]))), e(QUI_ENREGISTRE[k])]
                           for k, lib in rc.ETAPES.items()])

    onglets = [
        ("vue", "Vue d'ensemble", f"""{AVERTISSEMENT_DECISION}<div class="tuiles">{tuiles}</div>
            <h2>Candidatures ayant franchi chaque étape</h2>{t_entonnoir}
            <p class="note">Un désistement n'est pas compté comme une étape franchie.</p>"""),
        ("candidatures", "Candidatures", f"""
            {recherche('candidatures', 'nom, offre, statut…')}{t_cands}
            <p class="note">Ordre fixe par numéro de dossier : les candidats ne sont jamais classés.
            Relance si un dossier en cours reste {rc.DELAI_RELANCE_JOURS} jours sans action ; réponse écrite
            attendue dans les {rc.DELAI_REPONSE_JOURS} jours après une décision négative.</p>"""),
        ("dates", "Dates importantes", f"{recherche('dates', 'nom, numéro…')}{t_dates}"),
        ("historique", "Historique", f"""<p class="note">Chaque ligne est une action enregistrée par une
            personne. Les grilles sont remplies par le comité ; elles éclairent la décision humaine sans la remplacer.</p>
            {historiques}"""),
        ("planning", "Planning des entretiens", f"""{t_planning}
            <p class="note">Préavis minimal de {rc.PREAVIS_CONVOCATION_JOURS} jours entre la convocation et le test.
            Même grille et mêmes questions pour chaque candidat(e).</p>"""),
        ("modeles", "Modèles", f"""
            <h2>Courriel de convocation (exemple rempli pour CAND-006)</h2><pre class="modele">{e(courriel)}</pre>
            <p class="note">Modèle source : documents/modeles_courriers/courriel_convocation_test.txt</p>
            <h2>Checklist d'intégration : {e(recrue['prenom'])} {e(recrue['nom'])}</h2>
            <ul class="liste-controle">{checklist}</ul>
            <p class="note">Fin de période d'essai : date selon le contrat signé ; bilan et décision par le responsable RH.</p>"""),
        ("processus", "Processus", f"""{AVERTISSEMENT_DECISION}{t_processus}
            <h3>Règles contrôlées à chaque enregistrement</h3>
            <ul>
              <li>Les étapes se suivent dans l'ordre, sans saut, et un dossier clôturé n'évolue plus.</li>
              <li>Chaque étape est enregistrée par une personne ; aucun intervenant automatique n'est accepté.</li>
              <li>L'étape 6 (décision) est réservée au responsable RH ; une non-sélection est décidée par le comité ou le responsable RH.</li>
              <li>Les références ne sont contactées qu'après l'autorisation écrite du candidat.</li>
              <li>Une grille d'évaluation est obligatoire aux étapes 2 et 4.</li>
            </ul>"""),
    ]
    avertissement = ""
    if jour > DATE_REFERENCE:
        avertissement = (f'<p class="note attention"><strong>Date de test.</strong> Les actions enregistrées '
                         f"s'arrêtent au {DATE_REFERENCE:%d/%m/%Y} : après cette date, les dossiers apparaissent "
                         f"sans nouvelle action, ce qui permet de tester les alertes de délai.</p>")
    return page("Suivi du recrutement",
                f"NURU HR DIGITAL PORTFOLIO · situation au <strong>{jour:%d/%m/%Y}</strong> · consultation seule",
                onglets, avant_onglets=avertissement)


def generer_documents(d, jour):
    """Écrit le planning, les convocations et les checklists. Renvoie la liste des fichiers créés."""
    offres = {o["offre_id"]: o for o in d["offres_emploi"]}
    fichiers = {DOSSIER / "planning_entretiens.md": planning_markdown(d, jour),
                RACINE / "documents" / "modeles_courriers" / "checklist_integration_modele.md": checklist_modele_markdown()}
    for c in d["candidatures"]:
        creneau = rc.creneau_de(d, c["candidature_id"])
        if creneau:
            fichiers[DOSSIER / "convocations" / f"convocation_{c['candidature_id']}.txt"] = \
                rc.generer_convocation(c, offres[c["offre_id"]], creneau)
        if c["date_prise_fonction_prevue"]:
            fichiers[DOSSIER / f"checklist_integration_{c['candidature_id']}.md"] = \
                checklist_markdown(c, offres[c["offre_id"]], en_date(c["date_prise_fonction_prevue"]))
    for chemin, texte in fichiers.items():
        chemin.parent.mkdir(exist_ok=True)
        chemin.write_text(texte, encoding="utf-8")
    return list(fichiers)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Génère le module de suivi du recrutement.")
    parser.add_argument("--date", help="date de consultation AAAA-MM-JJ (par défaut : 2026-10-31)")
    args = parser.parse_args()
    jour = date.fromisoformat(args.date) if args.date else DATE_REFERENCE
    donnees = rc.charger_donnees()
    problemes = rc.verifier_donnees(donnees)
    if problemes:
        print("Données de recrutement incohérentes, module non généré :")
        print("\n".join(f"  - {p}" for p in problemes))
        sys.exit(1)
    nom = "module_recrutement.html" if jour == DATE_REFERENCE else f"module_recrutement_test_{jour}.html"
    (DOSSIER / nom).write_text(construire(donnees, jour), encoding="utf-8")
    print(f"Module généré : recruitment/{nom} (situation au {jour:%d/%m/%Y})")
    if jour == DATE_REFERENCE:
        for f in generer_documents(donnees, jour):
            print(f"Document : {f.relative_to(RACINE)}")
