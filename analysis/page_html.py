"""
Éléments communs des pages de consultation (modules RH et recrutement) :
gabarit de page à onglets, tableaux, tuiles d'indicateurs, badges.

Les pages sont autonomes : aucune connexion Internet, aucune bibliothèque externe.
"""
from html import escape

MENTION_FICTIVE = "Données fictives. Portfolio personnel, ce n'est pas un outil officiel de Nuru."
PIED_DEFAUT = ("Ce fichier contient des données personnelles (ici fictives). En situation réelle, il doit être "
               "conservé sur un espace à accès restreint et ne doit pas être diffusé par e-mail ni sur un support partagé.")


def fdate(iso):
    """'2026-10-31' -> '31/10/2026' (vide si pas de date)."""
    iso = str(iso) if iso else ""
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}" if iso else ""


def badge(texte, classe, icone):
    """Badge d'état : l'icône et le libellé portent le sens, la couleur n'est qu'un renfort."""
    return f'<span class="badge {classe}"><span aria-hidden="true">{icone}</span> {escape(texte)}</span>'


def tableau(entetes, lignes, num=(), pied=None):
    """Construit un tableau HTML. 'num' = indices des colonnes numériques."""
    def cellule(i, v):
        return f'<td{" class=num" if i in num else ""}>{v}</td>'
    th = "".join(f'<th scope="col"{" class=num" if i in num else ""}>{escape(e)}</th>'
                 for i, e in enumerate(entetes))
    corps = "".join("<tr>" + "".join(cellule(i, v) for i, v in enumerate(l)) + "</tr>" for l in lignes)
    tfoot = f"<tfoot><tr>{''.join(cellule(i, v) for i, v in enumerate(pied))}</tr></tfoot>" if pied else ""
    return f'<div class="defile"><table><thead><tr>{th}</tr></thead><tbody>{corps}</tbody>{tfoot}</table></div>'


def tuile(libelle, valeur, detail=""):
    return (f'<div class="tuile"><div class="t-lib">{escape(libelle)}</div>'
            f'<div class="t-val">{valeur}</div><div class="t-det">{escape(detail)}</div></div>')


def recherche(cible, exemple="nom, matricule, département…"):
    return (f'<label class="recherche">Rechercher <input type="search" data-cible="{cible}" '
            f'placeholder="{escape(exemple)}"></label>')


def page(titre, sous_titre, onglets, avant_onglets="", pied=PIED_DEFAUT):
    """Page complète. 'onglets' = liste de (identifiant, libellé, contenu HTML)."""
    boutons = "".join(
        f'<button role="tab" id="tab-{i}" aria-controls="pan-{i}" aria-selected="{str(n == 0).lower()}">{escape(t)}</button>'
        for n, (i, t, _) in enumerate(onglets))
    panneaux = "".join(
        f'<section role="tabpanel" id="pan-{i}" aria-labelledby="tab-{i}" data-panneau="{i}"'
        f'{"" if n == 0 else " hidden"}>{c}</section>'
        for n, (i, _, c) in enumerate(onglets))
    return GABARIT.format(titre=escape(titre), sous_titre=sous_titre, avant_onglets=avant_onglets,
                          boutons=boutons, panneaux=panneaux, pied=escape(pied), mention=escape(MENTION_FICTIVE))


GABARIT = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titre}</title>
<style>
:root {{
  --fond: #f7f7f5; --surface: #ffffff; --encre: #1f1f1d; --encre-2: #55554f; --trait: #e1e0da;
  --accent: #1f5f8b; --bandeau: #fff4d6; --bandeau-trait: #e0b44a;
  --critique: #d03b3b; --serieux: #ec835a; --vigilance: #fab219; --bon: #0ca30c; --neutre: #9a9a92;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --fond: #1a1a19; --surface: #242422; --encre: #ecebe6; --encre-2: #b3b2ab; --trait: #3a3a37;
    --accent: #7db7e0; --bandeau: #3a3220; --bandeau-trait: #b48a2c;
  }}
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--fond); color: var(--encre);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
header, main, footer {{ max-width: 1200px; margin: 0 auto; padding: 0 16px; }}
.fictif {{ background: var(--bandeau); border-bottom: 2px solid var(--bandeau-trait); padding: 8px 16px;
  text-align: center; font-weight: 600; }}
h1 {{ font-size: 1.5rem; margin: 20px 0 2px; }}
h2 {{ font-size: 1.05rem; margin: 24px 0 8px; }}
h3 {{ font-size: .95rem; margin: 16px 0 6px; }}
.sous-titre {{ color: var(--encre-2); margin: 0 0 16px; }}
[role=tablist] {{ display: flex; flex-wrap: wrap; gap: 4px; border-bottom: 1px solid var(--trait); }}
[role=tab] {{ font: inherit; background: none; border: 0; border-bottom: 3px solid transparent;
  padding: 8px 12px; color: var(--encre-2); cursor: pointer; }}
[role=tab][aria-selected=true] {{ color: var(--encre); border-bottom-color: var(--accent); font-weight: 600; }}
[role=tab]:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
section {{ padding: 16px 0 32px; }}
.tuiles {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }}
.tuile {{ background: var(--surface); border: 1px solid var(--trait); border-radius: 8px; padding: 12px 14px; }}
.t-lib {{ color: var(--encre-2); font-size: .85rem; }}
.t-val {{ font-size: 1.9rem; font-weight: 600; line-height: 1.2; }}
.t-det {{ color: var(--encre-2); font-size: .8rem; }}
.defile {{ overflow-x: auto; background: var(--surface); border: 1px solid var(--trait); border-radius: 8px; }}
table {{ border-collapse: collapse; width: 100%; font-size: .9rem; }}
th, td {{ text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--trait); white-space: nowrap; }}
.texte {{ white-space: normal; display: inline-block; min-width: 240px; }}
th {{ color: var(--encre-2); font-weight: 600; position: sticky; top: 0; background: var(--surface); }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
tfoot td {{ font-weight: 600; border-bottom: 0; }}
.badge {{ display: inline-block; padding: 1px 8px 1px 6px; border-radius: 4px; border-left: 4px solid var(--neutre);
  background: color-mix(in srgb, var(--neutre) 12%, transparent); }}
.badge.critique {{ border-color: var(--critique); background: color-mix(in srgb, var(--critique) 14%, transparent); }}
.badge.serieux {{ border-color: var(--serieux); background: color-mix(in srgb, var(--serieux) 16%, transparent); }}
.badge.vigilance {{ border-color: var(--vigilance); background: color-mix(in srgb, var(--vigilance) 18%, transparent); }}
.badge.bon {{ border-color: var(--bon); background: color-mix(in srgb, var(--bon) 12%, transparent); }}
.badge.info {{ border-color: var(--accent); background: color-mix(in srgb, var(--accent) 12%, transparent); }}
.note {{ color: var(--encre-2); font-size: .88rem; }}
.note.decision, .note.attention {{ color: var(--encre); background: var(--surface); border: 1px solid var(--trait);
  border-left: 4px solid var(--accent); border-radius: 6px; padding: 10px 12px; }}
.note.attention {{ border-left-color: var(--vigilance); }}
.recherche {{ display: block; margin: 0 0 10px; color: var(--encre-2); font-size: .9rem; }}
.recherche input {{ font: inherit; margin-left: 6px; padding: 5px 8px; width: min(320px, 100%);
  border: 1px solid var(--trait); border-radius: 6px; background: var(--surface); color: var(--encre); }}
pre.modele {{ background: var(--surface); border: 1px solid var(--trait); border-radius: 8px; padding: 12px 14px;
  white-space: pre-wrap; font: .88rem/1.5 ui-monospace, Consolas, monospace; }}
details {{ background: var(--surface); border: 1px solid var(--trait); border-radius: 8px; padding: 8px 12px; margin: 0 0 8px; }}
summary {{ cursor: pointer; font-weight: 600; }}
ul.liste-controle {{ list-style: none; padding-left: 0; }}
ul.liste-controle li {{ padding: 4px 0; border-bottom: 1px solid var(--trait); }}
footer {{ color: var(--encre-2); font-size: .8rem; padding-bottom: 24px; }}
@media print {{ [role=tablist], .recherche {{ display: none; }} section[hidden] {{ display: block; }} }}
</style>
</head>
<body>
<div class="fictif" role="note">{mention}</div>
<header>
  <h1>{titre}</h1>
  <p class="sous-titre">{sous_titre}</p>
  {avant_onglets}
  <nav role="tablist" aria-label="Rubriques">{boutons}</nav>
</header>
<main>{panneaux}</main>
<footer><p>{pied}</p></footer>
<script>
// Onglets (un onglet peut aussi être ouvert par l'adresse, ex. page.html#echeances)
const onglets = document.querySelectorAll('[role=tab]');
function ouvrir(b) {{
  onglets.forEach(x => x.setAttribute('aria-selected', x === b));
  document.querySelectorAll('[role=tabpanel]').forEach(p => p.hidden = p.id !== b.getAttribute('aria-controls'));
}}
onglets.forEach(b => b.addEventListener('click', () => {{ ouvrir(b); history.replaceState(null, '', '#' + b.id.slice(4)); }}));
const depuisAdresse = document.getElementById('tab-' + location.hash.slice(1));
if (depuisAdresse) ouvrir(depuisAdresse);
// Recherche : masque les lignes qui ne contiennent pas le texte saisi
document.querySelectorAll('input[data-cible]').forEach(champ => champ.addEventListener('input', () => {{
  const texte = champ.value.toLowerCase();
  const panneau = document.querySelector('[data-panneau="' + champ.dataset.cible + '"]');
  panneau.querySelectorAll('tbody tr').forEach(tr => {{ tr.hidden = !tr.textContent.toLowerCase().includes(texte); }});
}}));
</script>
</body>
</html>
"""
