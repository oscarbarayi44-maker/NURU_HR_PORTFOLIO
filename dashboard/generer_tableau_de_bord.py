"""
Génère le tableau de bord RH : dashboard/tableau_de_bord_rh.html
(page autonome, sans connexion Internet ni bibliothèque externe)
et ses exports CSV : dashboard/exports/.

Tous les chiffres sont calculés à partir des fichiers de data/raw.
DONNÉES FICTIVES - Portfolio personnel, non officiel de Nuru.

Utilisation (depuis la racine du projet) :
    python dashboard/generer_tableau_de_bord.py
    python dashboard/generer_tableau_de_bord.py --date 2026-11-15   # simuler une autre date
"""
import argparse
import sys
from datetime import date
from html import escape
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
sys.path.insert(0, str(DOSSIER.parent / "analysis"))

import recrutement as rc  # noqa: E402
import insights as ins  # noqa: E402
import tableau_de_bord as tb  # noqa: E402
from commun import DATE_REFERENCE  # noqa: E402
from page_html import MENTION_FICTIVE, fdate  # noqa: E402

# Badges d'urgence : (classe CSS, icône). Le libellé et l'icône portent le sens.
BADGES_URGENCE = {
    tb.EN_RETARD: ("critique", "⛔"), tb.SOUS_7: ("serieux", "⚠"), tb.SOUS_30: ("vigilance", "◷"),
    tb.PLUS_TARD: ("neutre", "◔"), tb.SANS_DATE: ("neutre", "–"),
}
SERIE_1, SERIE_2 = "--serie-1", "--serie-2"


def badge(texte):
    classe, icone = BADGES_URGENCE[texte]
    return f'<span class="badge {classe}"><span aria-hidden="true">{icone}</span> {escape(texte)}</span>'


def legende(series):
    return '<ul class="legende">' + "".join(
        f'<li><span class="pastille" style="background:var({var})"></span>{escape(nom)}</li>'
        for nom, var in series) + "</ul>"


def barres(lignes, series):
    """Barres horizontales (empilées si plusieurs séries).
    lignes = [(libellé, [valeur par série])], series = [(nom, variable CSS)]."""
    maximum = max((sum(v) for _, v in lignes), default=0) or 1
    html = []
    for libelle, valeurs in lignes:
        total = sum(valeurs)
        segments = "".join(
            f'<span class="seg" style="width:{100 * v / maximum:.2f}%;background:var({var})"></span>'
            for v, (_, var) in zip(valeurs, series) if v > 0)
        detail = " · ".join(f"{nom} : {v}" for v, (nom, _) in zip(valeurs, series))
        info = f"{libelle} · {detail}" + (f" · Total : {total}" if len(series) > 1 else "")
        html.append(f'<div class="barre" tabindex="0" data-info="{escape(info)}" aria-label="{escape(info)}">'
                    f'<span class="b-lib">{escape(libelle)}</span><span class="b-piste">{segments}</span>'
                    f'<span class="b-val">{total}</span></div>')
    return '<div class="barres">' + "".join(html) + "</div>"


def table_donnees(entetes, lignes):
    """Vue tableau d'un graphique (accessibilité, impression)."""
    th = "".join(f'<th scope="col">{escape(e)}</th>' for e in entetes)
    corps = "".join("<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in l) + "</tr>" for l in lignes)
    return (f'<details class="donnees"><summary>Voir les données</summary>'
            f'<div class="defile"><table><thead><tr>{th}</tr></thead><tbody>{corps}</tbody></table></div></details>')


def tuile(libelle, valeur, detail, hero=False):
    return (f'<div class="tuile{" hero" if hero else ""}"><div class="t-lib">{escape(libelle)}</div>'
            f'<div class="t-val">{valeur}</div><div class="t-det">{escape(detail)}</div></div>')


BADGES_INSIGHT = {ins.ATTENTION: ("serieux", "⚠"), ins.A_SUIVRE: ("vigilance", "◔"), ins.INFORMATION: ("neutre", "ℹ")}


def carte_insights(liste):
    """Cartes d'insights : niveau (icône + libellé), indicateur, constat chiffré, piste d'action."""
    cartes = "".join(
        f'<article class="insight"><div class="i-tete"><span class="badge {BADGES_INSIGHT[i["niveau"]][0]}">'
        f'<span aria-hidden="true">{BADGES_INSIGHT[i["niveau"]][1]}</span> {escape(i["niveau"])}</span>'
        f'<span class="i-theme">{escape(i["theme"])}</span></div>'
        f'<h3>{escape(i["titre"])}</h3><div class="i-val">{escape(i["indicateur"])}</div>'
        f'<p>{escape(i["constat"])}</p><p class="i-piste"><strong>Piste :</strong> {escape(i["piste"])}</p></article>'
        for i in liste)
    return (f'<h2>Insights RH</h2><div class="insights">{cartes}</div>'
            '<p class="note">Constats calculés automatiquement à partir des données, présentés de façon agrégée. '
            "Les pistes sont des suggestions : la décision appartient au responsable RH.</p>")


def construire(tdb, liste_insights=None):
    jour = tdb["jour"]
    if liste_insights is None:
        liste_insights = ins.calculer_insights(jour)
    stg, ab = tdb["stagiaires"], tdb["absences"]
    nb_retard = sum(a["urgence"] == tb.EN_RETARD for a in tdb["actions"])

    tuiles = "".join([
        tuile("Effectif actif", tdb["effectif_total"],
              f"sur {tdb['collaborateurs_enregistres']} collaborateurs enregistrés · {tdb['part_cdd_pct']} % en CDD", hero=True),
        tuile("CDD à échéance sous 30 jours", len(tdb["contrats_30"]),
              f"{tdb['contrats_echus']} contrat(s) échu(s) non régularisé(s)"),
        tuile("Stagiaires suivis", sum(stg.values()),
              f"{stg['En cours']} en cours · {stg['À venir']} à venir · {stg['Terminé']} terminés"),
        tuile("Absences enregistrées", ab["enregistrees"],
              f"{ab['realisees']} réalisées ({ab['jours_realises']} jours ouvrables) · {ab['en_attente']} demande(s) en attente"),
        tuile("Candidatures", tdb["candidatures_total"], f"{len(tdb['offres'])} offres en cours de suivi"),
        tuile("Actions à effectuer", len(tdb["actions"]), f"dont {nb_retard} en retard"),
    ])

    # Effectifs par département (CDI / CDD)
    deps = tdb["effectifs_departements"]
    series_contrat = [("CDI", SERIE_1), ("CDD", SERIE_2)]
    carte_dep = (f'<h2>Effectifs par département</h2>{legende(series_contrat)}'
                 + barres([(d, [v["CDI"], v["CDD"]]) for d, v in deps.items()], series_contrat)
                 + table_donnees(["Département", "CDI", "CDD", "Total"],
                                 [[d, v["CDI"], v["CDD"], v["CDI"] + v["CDD"]] for d, v in deps.items()]))

    # Recrutement : candidatures ayant franchi chaque étape, par offre
    offres = list(tdb["offres"])
    series_offres = [(f"{tdb['offres'][o]} ({o})", var) for o, var in zip(offres, (SERIE_1, SERIE_2))]
    lignes_rec = [(f"{k}. {lib}", [tdb["entonnoir"][o][k] for o in offres]) for k, lib in rc.ETAPES.items()]
    carte_rec = (f'<h2>Candidatures par étape du recrutement</h2>{legende(series_offres)}'
                 + barres(lignes_rec, series_offres)
                 + '<p class="note">Nombre de candidatures ayant franchi chaque étape (un désistement ne compte pas). '
                   'Les décisions sont prises par des personnes ; ce graphique ne classe pas les candidats.</p>'
                 + table_donnees(["Étape"] + [tdb["offres"][o] for o in offres] + ["Total", "Dossiers en cours à cette étape"],
                                 [[f"{k}. {lib}"] + [tdb["entonnoir"][o][k] for o in offres]
                                  + [sum(tdb["entonnoir"][o][k] for o in offres), tdb["en_cours_par_etape"][k]]
                                  for k, lib in rc.ETAPES.items()]))

    # Absences : jours ouvrables par catégorie
    cats = ab["jours_par_categorie"]
    carte_abs = (f'<h2>Absences : jours ouvrables par catégorie</h2>'
                 + barres([(c, [n]) for c, n in cats.items()], [("Jours", SERIE_1)])
                 + f'<p class="note">Absences approuvées ou constatées du 01/01/{jour.year} au {jour:%d/%m/%Y}. '
                   'Les motifs de santé sont regroupés sous une catégorie confidentielle.</p>'
                 + table_donnees(["Catégorie", "Jours ouvrables"], [[c, n] for c, n in cats.items()]))

    # Contrats à échéance sous 30 jours
    lignes_ctr = "".join(
        f'<tr><td>{escape(l["matricule"])}</td><td>{escape(l["nom"])}</td><td>{escape(l["poste"])}</td>'
        f'<td>{fdate(l["date_fin"])}</td><td class="num">{l["jours_restants"]}</td></tr>' for l in tdb["contrats_30"])
    carte_ctr = ('<h2>CDD à échéance sous 30 jours</h2>'
                 + ('<div class="defile"><table><thead><tr><th scope="col">Matricule</th><th scope="col">Nom</th>'
                    '<th scope="col">Poste</th><th scope="col">Fin</th><th scope="col" class="num">Jours</th></tr></thead>'
                    f'<tbody>{lignes_ctr}</tbody></table></div>' if tdb["contrats_30"] else '<p>Aucun contrat concerné.</p>')
                 + '<p class="note decision">Alerte indicative : toute décision contractuelle (renouvellement, '
                   'fin de contrat) appartient au responsable RH.</p>')

    # Actions administratives
    lignes_act = "".join(
        f'<tr><td>{badge(a["urgence"])}</td><td>{fdate(a["echeance"])}</td><td>{escape(a["domaine"])}</td>'
        f'<td>{escape(a["objet"])}</td><td class="texte">{escape(a["action"])}</td><td>{escape(a["responsable"])}</td></tr>'
        for a in tdb["actions"])
    legende_urgence = '<ul class="legende">' + "".join(f"<li>{badge(u)}</li>" for u in tb.ORDRE_URGENCE) + "</ul>"

    return GABARIT.format(
        mention=escape(MENTION_FICTIVE), jour=f"{jour:%d/%m/%Y}", tuiles=tuiles,
        carte_dep=carte_dep, carte_rec=carte_rec, carte_abs=carte_abs, carte_ctr=carte_ctr,
        carte_insights=carte_insights(liste_insights),
        legende_urgence=legende_urgence, lignes_act=lignes_act,
        # Fins de ligne simples dans la page (le navigateur les remet en CRLF à l'export) :
        # un CRLF intégré deviendrait CR CR LF une fois le fichier écrit sous Windows.
        csv_actions=escape(tb.export_actions_csv(tdb).replace("\r\n", "\n")),
        csv_indicateurs=escape(tb.export_indicateurs_csv(tdb).replace("\r\n", "\n")),
        date_iso=jour.isoformat())


GABARIT = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tableau de bord RH</title>
<style>
:root {{
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --encre: #0b0b0b; --encre-2: #52514e; --discret: #898781;
  --grille: #e1e0d9; --bord: rgba(11,11,11,0.10); --accent: #2a78d6; --bandeau: #fff4d6; --bandeau-trait: #e0b44a;
  --serie-1: #2a78d6; --serie-2: #eb6834;
  --critique: #d03b3b; --serieux: #ec835a; --vigilance: #fab219; --neutre: #898781;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19; --encre: #f0efec; --encre-2: #c3c2b7; --grille: #2c2c2a;
    --bord: rgba(255,255,255,0.10); --accent: #3987e5; --bandeau: #3a3220; --bandeau-trait: #b48a2c;
    --serie-1: #3987e5; --serie-2: #d95926;
  }}
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--page); color: var(--encre);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
.fictif {{ background: var(--bandeau); border-bottom: 2px solid var(--bandeau-trait); padding: 8px 16px;
  text-align: center; font-weight: 600; }}
.conteneur {{ max-width: 1240px; margin: 0 auto; padding: 0 16px 32px; }}
header {{ display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 12px; margin: 20px 0 16px; }}
h1 {{ font-size: 1.6rem; margin: 0; }}
.sous-titre {{ color: var(--encre-2); margin: 2px 0 0; }}
.exports {{ display: flex; flex-wrap: wrap; gap: 8px; }}
button {{ font: inherit; font-size: .88rem; padding: 7px 12px; border-radius: 6px; cursor: pointer;
  border: 1px solid var(--bord); background: var(--surface); color: var(--encre); }}
button.principal {{ background: var(--accent); border-color: var(--accent); color: #fff; }}
button:focus-visible, .barre:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
.tuiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 16px; }}
.tuile {{ background: var(--surface); border: 1px solid var(--bord); border-radius: 10px; padding: 14px 16px; }}
.tuile.hero {{ grid-column: span 2; }}
.t-lib {{ color: var(--encre-2); font-size: .85rem; }}
.t-val {{ font-size: 2rem; font-weight: 600; line-height: 1.15; margin: 4px 0; }}
.hero .t-val {{ font-size: 3.2rem; }}
.t-det {{ color: var(--encre-2); font-size: .8rem; }}
.grille {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 480px), 1fr)); gap: 16px; }}
.carte {{ background: var(--surface); border: 1px solid var(--bord); border-radius: 10px; padding: 16px; min-width: 0; }}
.carte.large {{ grid-column: 1 / -1; }}
h2 {{ font-size: 1.02rem; margin: 0 0 10px; }}
.legende {{ list-style: none; display: flex; flex-wrap: wrap; gap: 6px 16px; padding: 0; margin: 0 0 12px;
  font-size: .85rem; color: var(--encre-2); }}
.legende li {{ display: flex; align-items: center; gap: 6px; }}
.pastille {{ width: 12px; height: 12px; border-radius: 3px; display: inline-block; }}
.barres {{ display: grid; gap: 6px; }}
.barre {{ display: grid; grid-template-columns: minmax(96px, 40%) 1fr 2.5em; align-items: center; gap: 10px;
  padding: 3px 4px; border-radius: 6px; font-size: .88rem; }}
.barre:hover {{ background: var(--grille); }}
.b-lib {{ color: var(--encre-2); line-height: 1.25; }}
.b-piste {{ display: flex; height: 14px; border-left: 1px solid var(--grille); }}
.seg {{ height: 100%; min-width: 3px; }}
.seg + .seg {{ border-left: 2px solid var(--surface); }}
.seg:last-child {{ border-radius: 0 4px 4px 0; }}
.b-val {{ font-variant-numeric: tabular-nums; text-align: right; font-weight: 600; }}
.note {{ color: var(--encre-2); font-size: .82rem; margin: 10px 0 0; }}
.note.decision {{ color: var(--encre); border-left: 4px solid var(--accent); padding: 6px 10px; background: var(--page); border-radius: 4px; }}
details.donnees {{ margin-top: 10px; font-size: .85rem; }}
details.donnees summary {{ cursor: pointer; color: var(--accent); }}
.defile {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-size: .86rem; }}
th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--grille); white-space: nowrap; vertical-align: top; }}
th {{ color: var(--encre-2); font-weight: 600; }}
td.texte {{ white-space: normal; min-width: 260px; }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.badge {{ display: inline-block; padding: 1px 8px 1px 6px; border-radius: 4px; border-left: 4px solid var(--neutre);
  background: color-mix(in srgb, var(--neutre) 12%, transparent); white-space: nowrap; }}
.badge.critique {{ border-color: var(--critique); background: color-mix(in srgb, var(--critique) 14%, transparent); }}
.badge.serieux {{ border-color: var(--serieux); background: color-mix(in srgb, var(--serieux) 16%, transparent); }}
.badge.vigilance {{ border-color: var(--vigilance); background: color-mix(in srgb, var(--vigilance) 18%, transparent); }}
.insights {{ display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr)); }}
.insight {{ border: 1px solid var(--bord); border-radius: 8px; padding: 12px 14px; background: var(--page); }}
.insight h3 {{ font-size: .95rem; margin: 8px 0 2px; }}
.insight p {{ font-size: .86rem; margin: 6px 0 0; }}
.i-tete {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; font-size: .8rem; }}
.i-theme {{ color: var(--encre-2); }}
.i-val {{ font-size: 1.6rem; font-weight: 600; line-height: 1.2; }}
.i-piste {{ color: var(--encre-2); }}
#infobulle {{ position: fixed; z-index: 10; pointer-events: none; max-width: 280px; padding: 6px 10px; border-radius: 6px;
  background: var(--encre); color: var(--page); font-size: .82rem; box-shadow: 0 2px 8px rgba(0,0,0,.25); }}
footer {{ color: var(--encre-2); font-size: .8rem; margin-top: 24px; }}
@media (max-width: 560px) {{
  .tuile.hero {{ grid-column: auto; }}
  .hero .t-val {{ font-size: 2.6rem; }}
  .barre {{ grid-template-columns: 1fr 2.5em; }}
  .b-lib {{ grid-column: 1 / -1; }}
}}
@media print {{
  .exports, #infobulle {{ display: none !important; }}
  body {{ background: #fff; }}
  .carte, .tuile {{ break-inside: avoid; }}
}}
</style>
</head>
<body>
<div class="fictif" role="note">{mention}</div>
<div class="conteneur">
<header>
  <div>
    <h1>Tableau de bord RH</h1>
    <p class="sous-titre">NURU HR DIGITAL PORTFOLIO · situation au <strong>{jour}</strong> · indicateurs calculés automatiquement à partir des données sources</p>
  </div>
  <div class="exports">
    <button class="principal" type="button" data-export="csv-indicateurs" data-fichier="indicateurs_rh_{date_iso}.csv">Exporter les indicateurs (CSV)</button>
    <button type="button" data-export="csv-actions" data-fichier="actions_rh_{date_iso}.csv">Exporter les actions (CSV)</button>
    <button type="button" id="imprimer">Imprimer / PDF</button>
  </div>
</header>
<main>
  <section class="tuiles" aria-label="Indicateurs clés">{tuiles}</section>
  <div class="grille">
    <section class="carte">{carte_dep}</section>
    <section class="carte">{carte_rec}</section>
    <section class="carte">{carte_abs}</section>
    <section class="carte">{carte_ctr}</section>
    <section class="carte large">{carte_insights}</section>
    <section class="carte large">
      <h2>Actions administratives à effectuer</h2>
      {legende_urgence}
      <div class="defile"><table>
        <thead><tr><th scope="col">Urgence</th><th scope="col">Échéance</th><th scope="col">Domaine</th>
        <th scope="col">Objet</th><th scope="col">Action</th><th scope="col">Responsable</th></tr></thead>
        <tbody>{lignes_act}</tbody>
      </table></div>
      <p class="note">Tâches issues des contrats, des congés, des stagiaires et du recrutement, triées par urgence.
      Elles préparent des décisions qui restent humaines.</p>
    </section>
  </div>
</main>
<footer>
  <p>Méthode : chaque chiffre est recalculé à partir des fichiers de data/raw lors de la génération de la page
  (python dashboard/generer_tableau_de_bord.py). Ce fichier contient des données personnelles, ici fictives ;
  en situation réelle, il doit être conservé sur un espace à accès restreint.</p>
</footer>
</div>
<div id="infobulle" role="tooltip" hidden></div>
<script type="text/plain" id="csv-indicateurs">{csv_indicateurs}</script>
<script type="text/plain" id="csv-actions">{csv_actions}</script>
<script>
// Export CSV : le contenu est préparé par Python ; le navigateur le propose en téléchargement.
document.querySelectorAll('[data-export]').forEach(b => b.addEventListener('click', () => {{
  const texte = document.getElementById(b.dataset.export).textContent.replace(/\\r?\\n/g, '\\r\\n');
  const blob = new Blob(['\\ufeff' + texte], {{ type: 'text/csv;charset=utf-8' }});
  const lien = document.createElement('a');
  lien.href = URL.createObjectURL(blob);
  lien.download = b.dataset.fichier;
  document.body.appendChild(lien); lien.click(); lien.remove();
  setTimeout(() => URL.revokeObjectURL(lien.href), 1000);
}}));
document.getElementById('imprimer').addEventListener('click', () => {{
  document.querySelectorAll('details').forEach(d => d.open = true);
  window.print();
}});
// Infobulle au survol ou au focus clavier d'une barre
const bulle = document.getElementById('infobulle');
function montrer(el, x, y) {{
  bulle.textContent = el.dataset.info; bulle.hidden = false;
  const l = Math.min(x + 12, window.innerWidth - bulle.offsetWidth - 8);
  bulle.style.left = Math.max(8, l) + 'px'; bulle.style.top = (y + 14) + 'px';
}}
document.querySelectorAll('.barre').forEach(el => {{
  el.addEventListener('mousemove', e => montrer(el, e.clientX, e.clientY));
  el.addEventListener('mouseleave', () => bulle.hidden = true);
  el.addEventListener('focus', () => {{ const r = el.getBoundingClientRect(); montrer(el, r.left + r.width / 2, r.bottom - 10); }});
  el.addEventListener('blur', () => bulle.hidden = true);
}});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Génère le tableau de bord RH.")
    parser.add_argument("--date", help="date de situation AAAA-MM-JJ (par défaut : 2026-10-31)")
    args = parser.parse_args()
    jour = date.fromisoformat(args.date) if args.date else DATE_REFERENCE
    problemes = rc.verifier_donnees(rc.charger_donnees())
    if problemes:
        print("Données de recrutement incohérentes, tableau de bord non généré :")
        print("\n".join(f"  - {p}" for p in problemes))
        sys.exit(1)
    tdb = tb.donnees_tableau_de_bord(jour)
    suffixe = "" if jour == DATE_REFERENCE else f"_test_{jour}"
    page = DOSSIER / f"tableau_de_bord_rh{suffixe}.html"
    page.write_text(construire(tdb), encoding="utf-8")
    print(f"Tableau de bord généré : dashboard/{page.name} (situation au {jour:%d/%m/%Y})")
    if jour == DATE_REFERENCE:
        exports = DOSSIER / "exports"
        exports.mkdir(exist_ok=True)
        (exports / f"indicateurs_rh_{jour}.csv").write_text(tb.export_indicateurs_csv(tdb), encoding="utf-8-sig", newline="")
        (exports / f"actions_rh_{jour}.csv").write_text(tb.export_actions_csv(tdb), encoding="utf-8-sig", newline="")
        print(f"Exports : dashboard/exports/indicateurs_rh_{jour}.csv, dashboard/exports/actions_rh_{jour}.csv")
