"""
Génère le classeur Excel d'analyse RH : dashboard/tableau_de_bord_rh.xlsx

Le classeur est un tableau de bord manipulable : on choisit une date de situation,
un département et un bureau (cellules jaunes), et tous les indicateurs, tableaux et
graphiques se recalculent. Aucun indicateur n'est écrit en dur : chaque valeur est une
formule Excel calculée à partir des feuilles de données, elles-mêmes copiées de data/raw.

Compatibilité : Excel 2010 et suivants (pas de MAXIFS, FILTER ni XLOOKUP).

Protection des données (minimisation) : pas de date de naissance, e-mail, salaire, genre,
motif de sortie, note de stage, ni nom de candidat. Les motifs de santé sont regroupés sous
« Absence justifiée (motif confidentiel) ».

Lancement (depuis la racine du projet) :  python dashboard/generer_classeur_excel.py

DONNÉES FICTIVES - Portfolio personnel, non officiel de Nuru.
"""
import sys
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "analysis"))
import recrutement as rc  # noqa: E402
import suivi_rh as rh  # noqa: E402
from commun import DATE_REFERENCE, DEBUT_ANNEE, RACINE  # noqa: E402

SORTIE = RACINE / "dashboard" / "tableau_de_bord_rh.xlsx"
MENTION = "Données fictives – Portfolio personnel, non officiel de Nuru"

# --- Mise en forme (palette de référence, police Arial) -------------------------------
POLICE = "Arial"
BLEU, ORANGE = "2A78D6", "EB6834"                 # séries : CDI / CDD, offre 1 / offre 2
ENCRE, ENCRE_2, GRILLE = "0B0B0B", "52514E", "D9D8D4"
FOND_TITRE, FOND_SECTION, FOND_TUILE = "1C5CAB", "E8EFF8", "F4F7FB"
JAUNE = "FFF2B3"                                  # cellules modifiables
ETATS = {rh.ECHU: "F6D3D3", rh.URGENT: "FBE0D4", rh.A_PREPARER: "FEF0CC"}  # critique / sérieux / attention

FMT_DATE, FMT_MOIS = "dd/mm/yyyy", "mmmm yyyy"
FMT_ENTIER, FMT_PCT = "#,##0", "0.0%"
FMT_DATE_OU_VIDE = "dd/mm/yyyy;;"                 # 0 (aucun contrat) affiché vide

fin = Side(style="thin", color=GRILLE)
BORDURE = Border(left=fin, right=fin, top=fin, bottom=fin)


def police(**kw):
    return Font(name=POLICE, color=kw.pop("color", ENCRE), **kw)


def remplir(couleur):
    return PatternFill("solid", start_color=couleur, end_color=couleur)


def d(texte):
    return datetime.fromisoformat(texte) if texte else None


# --- Outils d'écriture ------------------------------------------------------------------
def nommer(wb, nom, feuille, plage):
    wb.defined_names[nom] = DefinedName(nom, attr_text=f"'{feuille}'!{plage}")


def entete_feuille(ws, titre, largeurs):
    ws["A1"] = titre
    ws["A1"].font = police(bold=True, size=14, color=FOND_TITRE)
    ws["A2"] = MENTION
    ws["A2"].font = police(italic=True, size=9, color=ENCRE_2)
    for i, l in enumerate(largeurs, 1):
        ws.column_dimensions[get_column_letter(i)].width = l
    ws.sheet_view.showGridLines = False


def feuille_donnees(wb, nom, titre, colonnes, lignes, nom_table, formats, largeurs):
    """Écrit un tableau Excel (ligne 3 = en-têtes) ; une valeur commençant par '=' est une formule.
    'lignes' est une liste de listes ; une fonction f(ligne_excel) génère une formule."""
    ws = wb.create_sheet(nom)
    entete_feuille(ws, titre, largeurs)
    for j, c in enumerate(colonnes, 1):
        ws.cell(3, j, c)
    for i, valeurs in enumerate(lignes):
        r = 4 + i
        for j, v in enumerate(valeurs, 1):
            cellule = ws.cell(r, j, v(r) if callable(v) else v)
            cellule.font = police(size=10)
            if formats.get(j):
                cellule.number_format = formats[j]
    for j in range(1, len(colonnes) + 1):
        h = ws.cell(3, j)
        h.font = police(bold=True, size=10, color="FFFFFF")
        h.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[3].height = 30
    derniere = 3 + max(len(lignes), 1)
    table = Table(displayName=nom_table, ref=f"A3:{get_column_letter(len(colonnes))}{derniere}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(table)
    ws.freeze_panes = "B4"
    return ws, derniere


def plage(feuille, col, derniere):
    return f"${col}$4:${col}${derniere}"


# --- Construction du classeur -------------------------------------------------------------
def construire():
    d_rh, d_rec = rh.charger_donnees(), rc.charger_donnees()
    collabs = sorted(d_rh["collaborateurs"], key=lambda c: c["matricule"])
    noms = {c["matricule"]: rh.nom_complet(c) for c in collabs}
    bureaux_collab = {c["matricule"]: c["bureau"] for c in collabs}
    departements = sorted({c["departement"] for c in collabs})
    bureaux = sorted({c["bureau"] for c in collabs})
    categories = list(dict.fromkeys(rh.CATEGORIE_AFFICHEE.values()))
    niveaux = [rh.ECHU, rh.URGENT, rh.A_PREPARER, rh.A_SURVEILLER, rh.RAS, rh.SANS_ECHEANCE]
    statuts_stage = ["En cours", "À venir", "Terminé"]
    offres = sorted(d_rec["offres_emploi"], key=lambda o: o["offre_id"])
    offre_de = {c["candidature_id"]: c["offre_id"] for c in d_rec["candidatures"]}
    annee = DEBUT_ANNEE.year

    wb = Workbook()
    wb.remove(wb.active)
    ws_lire = wb.create_sheet("Lisez-moi")
    tb = wb.create_sheet("Tableau de bord")

    # ---------- Paramètres et listes ----------
    pa = wb.create_sheet("Paramètres")
    entete_feuille(pa, "Paramètres et listes de référence", [34, 12, 52, 3, 30, 14, 40, 30, 34])
    pa["A3"], pa["B3"], pa["C3"] = "Paramètre", "Valeur", "Commentaire"
    seuils = [("Seuil « Urgent » (jours)", rh.SEUILS_ALERTE[0], "SeuilUrgent"),
              ("Seuil « À préparer » (jours)", rh.SEUILS_ALERTE[1], "SeuilPreparer"),
              ("Seuil « À surveiller » (jours)", rh.SEUILS_ALERTE[2], "SeuilSurveiller")]
    for i, (lib, val, nom) in enumerate(seuils):
        r = 4 + i
        pa.cell(r, 1, lib).font = police(size=10)
        c = pa.cell(r, 2, val)
        c.font, c.fill = police(size=10, color="0000FF"), remplir(JAUNE)
        pa.cell(r, 3, "Seuil d'alerte interne au projet (repris de analysis/suivi_rh.py), "
                      "pas une règle juridique.").font = police(size=9, color=ENCRE_2)
        nommer(wb, nom, "Paramètres", f"$B${r}")
    listes = {
        "E": ("Départements", ["Tous"] + departements, "ListeDep"),
        "F": ("Bureaux", ["Tous"] + bureaux, "ListeBur"),
        "G": ("Catégories d'absence", categories, None),
        "H": ("Statuts des stages", statuts_stage, None),
        "I": ("Niveaux d'alerte des contrats", niveaux, None),
    }
    for col, (titre, valeurs, nom) in listes.items():
        pa[f"{col}3"] = titre
        for i, v in enumerate(valeurs):
            pa[f"{col}{4 + i}"] = v
            pa[f"{col}{4 + i}"].font = police(size=10)
        if nom:
            nommer(wb, nom, "Paramètres", f"${col}$4:${col}${3 + len(valeurs)}")
    for col in "ABCEFGHI":
        pa[f"{col}3"].font = police(bold=True, size=10)
    noms_niveaux = ["NivEchu", "NivUrgent", "NivPreparer", "NivSurveiller", "NivRas", "NivSans"]
    for i, nom in enumerate(noms_niveaux):
        nommer(wb, nom, "Paramètres", f"$I${4 + i}")

    # ---------- Filtres (noms utilisés par toutes les formules) ----------
    nommer(wb, "DateSit", "Tableau de bord", "$D$4")
    nommer(wb, "FiltreDep", "Tableau de bord", "$D$5")
    nommer(wb, "FiltreBur", "Tableau de bord", "$D$6")
    perimetre = 'IF(AND(OR(FiltreDep="Tous",{d}=FiltreDep),OR(FiltreBur="Tous",{b}=FiltreBur)),1,0)'

    # ---------- Contrats ----------
    contrats = sorted(d_rh["contrats"], key=lambda c: (c["matricule"], c["date_debut"]))
    lignes = [[c["contrat_id"], c["matricule"], c["type_contrat"],
               int(c["duree_mois"]) if c["duree_mois"] else None, d(c["date_debut"]), d(c["date_fin"]),
               c["motif"], lambda r: f"=B{r}&\"|\"&E{r}"] for c in contrats]
    _, der_ct = feuille_donnees(
        wb, "Contrats", "Contrats de travail (sans rémunération)",
        ["Contrat", "Matricule", "Type", "Durée (mois)", "Début", "Fin", "Motif", "Clé (calcul)"],
        lignes, "tContrats", {5: FMT_DATE, 6: FMT_DATE}, [12, 11, 8, 10, 12, 12, 40, 18])
    for nom, col in (("ct_mat", "B"), ("ct_type", "C"), ("ct_deb", "E"), ("ct_fin", "F"), ("ct_cle", "H")):
        nommer(wb, nom, "Contrats", plage("Contrats", col, der_ct))

    # ---------- Collaborateurs ----------
    def ligne_collab(c):
        return [
            c["matricule"], rh.nom_complet(c), c["poste"], c["departement"], c["bureau"],
            d(c["date_embauche"]), d(c["date_sortie"]),
            lambda r: "=" + perimetre.format(d=f"D{r}", b=f"E{r}"),
            lambda r: f'=IF(AND(F{r}<=DateSit,OR(G{r}="",G{r}>DateSit)),1,0)',
            lambda r: f"=SUMPRODUCT(MAX((ct_mat=A{r})*(ct_deb<=DateSit)*ct_deb))",
            lambda r: f'=IF(I{r}=0,"",INDEX(ct_type,MATCH(A{r}&"|"&J{r},ct_cle,0)))',
            lambda r: (f'=IF(I{r}=0,"",IF(INDEX(ct_fin,MATCH(A{r}&"|"&J{r},ct_cle,0))="","",'
                       f'INDEX(ct_fin,MATCH(A{r}&"|"&J{r},ct_cle,0))))'),
            lambda r: f'=IF(OR(I{r}=0,L{r}=""),"",L{r}-DateSit)',
            lambda r: (f'=IF(I{r}=0,"",IF(L{r}="",NivSans,IF(M{r}<0,NivEchu,IF(M{r}<=SeuilUrgent,NivUrgent,'
                       f'IF(M{r}<=SeuilPreparer,NivPreparer,IF(M{r}<=SeuilSurveiller,NivSurveiller,NivRas))))))'),
        ]
    ws_cl, der_cl = feuille_donnees(
        wb, "Collaborateurs", "Registre du personnel et échéances des contrats",
        ["Matricule", "Nom", "Poste", "Département", "Bureau", "Date d'embauche", "Date de sortie",
         "Dans le filtre (1/0)", "En poste à la date (1/0)", "Début du contrat en vigueur",
         "Type de contrat", "Fin du contrat", "Jours restants", "Niveau d'alerte"],
        [ligne_collab(c) for c in collabs], "tCollaborateurs",
        {6: FMT_DATE, 7: FMT_DATE, 10: FMT_DATE_OU_VIDE, 12: FMT_DATE, 13: "0"},
        [11, 24, 34, 28, 10, 12, 12, 10, 10, 13, 9, 12, 10, 28])
    for nom, col in (("cl_mat", "A"), ("cl_dep", "D"), ("cl_bur", "E"), ("cl_emb", "F"), ("cl_sortie", "G"),
                     ("cl_perim", "H"), ("cl_present", "I"), ("cl_type", "K"), ("cl_alerte", "N")):
        nommer(wb, nom, "Collaborateurs", plage("Collaborateurs", col, der_cl))
    zone = f"N4:N{der_cl}"
    for niveau, couleur in ETATS.items():
        ws_cl.conditional_formatting.add(zone, CellIsRule(operator="equal", formula=[f'"{niveau}"'],
                                                          fill=remplir(couleur)))

    # ---------- Absences ----------
    def realisee(r):
        conditions = ",".join(f'H{r}="{s}"' for s in rh.STATUTS_REALISES)
        return f"=IF(OR({conditions}),1,0)"

    def ligne_absence(a):
        ligne = [a["absence_id"], a["matricule"], noms[a["matricule"]], rh.categorie_affichee(a["type_absence"]),
                 d(a["date_debut"]), d(a["date_fin"]), int(a["nb_jours_ouvrables"]), a["statut"],
                 lambda r: f"=INDEX(cl_dep,MATCH(B{r},cl_mat,0))",
                 lambda r: f"=INDEX(cl_bur,MATCH(B{r},cl_mat,0))",
                 lambda r: "=" + perimetre.format(d=f"I{r}", b=f"J{r}"),
                 realisee]
        for k in range(1, 13):
            debut_mois = f"DATE(YEAR(DateSit),{k},1)"
            ligne.append(lambda r, m=debut_mois: (
                f"=IF($L{r}=0,0,MAX(0,NETWORKDAYS(MAX($E{r},{m}),MIN($F{r},EOMONTH({m},0),DateSit))))"))
        ligne.append(lambda r: f"=SUM(M{r}:X{r})")
        return ligne

    absences = sorted(d_rh["absences"], key=lambda a: a["absence_id"])
    _, der_ab = feuille_donnees(
        wb, "Absences", "Absences et congés (motifs de santé regroupés, catégorie confidentielle)",
        ["Absence", "Matricule", "Collaborateur", "Catégorie", "Début", "Fin", "Jours ouvrables",
         "Statut", "Département", "Bureau", "Dans le filtre (1/0)", "Réalisée (1/0)"]
        + [f"Jours {datetime(annee, k, 1):%m}" for k in range(1, 13)] + ["Jours année"],
        [ligne_absence(a) for a in absences], "tAbsences", {5: FMT_DATE, 6: FMT_DATE},
        [10, 10, 22, 34, 11, 11, 9, 11, 26, 10, 9, 9] + [7] * 12 + [8])
    for nom, col in (("ab_cat", "D"), ("ab_statut", "H"), ("ab_perim", "K"), ("ab_total", "Y")):
        nommer(wb, nom, "Absences", plage("Absences", col, der_ab))
    nommer(wb, "ab_mois", "Absences", f"$M$4:$X${der_ab}")

    # ---------- Stagiaires ----------
    def ligne_stage(s):
        return [s["stagiaire_id"], rh.nom_complet(s), s["filiere"], s["niveau"], s["departement"],
                noms[s["encadreur_matricule"]], bureaux_collab[s["encadreur_matricule"]],
                d(s["date_debut"]), d(s["date_fin"]), "Oui" if s["note_evaluation_sur_20"] else "Non",
                lambda r: "=" + perimetre.format(d=f"E{r}", b=f"G{r}"),
                lambda r: f'=IF(I{r}<DateSit,"Terminé",IF(H{r}>DateSit,"À venir","En cours"))',
                lambda r: f'=IF(L{r}="En cours",I{r}-DateSit,"")',
                lambda r: f'=IF(L{r}="Terminé",IF(J{r}="Oui","Réalisée","À faire"),"")']
    stages = sorted(d_rh["stagiaires"], key=lambda s: s["stagiaire_id"])
    _, der_st = feuille_donnees(
        wb, "Stagiaires", "Suivi des stagiaires (sans note ni indemnité)",
        ["Stagiaire", "Nom", "Filière", "Niveau", "Département", "Encadreur", "Bureau de l'encadreur",
         "Début", "Fin", "Évaluation enregistrée", "Dans le filtre (1/0)", "Statut à la date",
         "Jours avant la fin", "Évaluation finale"],
        [ligne_stage(s) for s in stages], "tStagiaires", {8: FMT_DATE, 9: FMT_DATE, 13: "0"},
        [10, 22, 30, 10, 26, 22, 11, 11, 11, 11, 9, 11, 10, 12])
    for nom, col in (("st_perim", "K"), ("st_statut", "L")):
        nommer(wb, nom, "Stagiaires", plage("Stagiaires", col, der_st))

    # ---------- Recrutement (numéro de dossier uniquement, sans note ni commentaire) ----------
    cands = sorted(d_rec["candidatures"], key=lambda c: c["candidature_id"])
    _, der_cd = feuille_donnees(
        wb, "Candidatures", "Candidatures (affichées par numéro de dossier)",
        ["Dossier", "Offre", "Date de candidature", "Source"],
        [[c["candidature_id"], c["offre_id"], d(c["date_candidature"]), c["source"]] for c in cands],
        "tCandidatures", {3: FMT_DATE}, [11, 13, 13, 24])
    nommer(wb, "cd_date", "Candidatures", plage("Candidatures", "C", der_cd))
    evts = sorted(d_rec["recrutement_etapes"], key=lambda e: e["evenement_id"])
    _, der_ev = feuille_donnees(
        wb, "Étapes recrutement", "Journal des étapes de recrutement (décisions humaines)",
        ["Événement", "Dossier", "Offre", "Étape", "Libellé de l'étape", "Date", "Résultat", "Enregistré par"],
        [[e["evenement_id"], e["candidature_id"], offre_de[e["candidature_id"]], int(e["etape"]),
          rc.ETAPES[int(e["etape"])], d(e["date"]), e["resultat"], e["intervenant"]] for e in evts],
        "tEtapes", {6: FMT_DATE}, [11, 10, 13, 7, 32, 11, 16, 24])
    for nom, col in (("ev_offre", "C"), ("ev_etape", "D"), ("ev_date", "F"), ("ev_res", "G")):
        nommer(wb, nom, "Étapes recrutement", plage("Étapes recrutement", col, der_ev))

    # ---------- Tableau de bord ----------
    construire_tableau_de_bord(tb, departements, categories, niveaux, statuts_stage, offres, annee)
    construire_lisez_moi(ws_lire, annee)

    wb.calculation.fullCalcOnLoad = True       # Excel recalcule tout à l'ouverture
    return wb


def titre_section(ws, cellule, texte, largeur=8):
    ws[cellule] = texte
    ws[cellule].font = police(bold=True, size=11, color=FOND_TITRE)
    r, c = ws[cellule].row, ws[cellule].column
    for j in range(c, c + largeur):
        ws.cell(r, j).border = Border(bottom=Side(style="medium", color=FOND_TITRE))


def ecrire_tableau(ws, r0, c0, entetes, lignes, formats=None):
    """Petit tableau mis en forme (en-tête bleu clair). Renvoie la dernière ligne écrite."""
    formats = formats or {}
    for j, h in enumerate(entetes):
        c = ws.cell(r0, c0 + j, h)
        c.font, c.fill, c.border = police(bold=True, size=10), remplir(FOND_SECTION), BORDURE
        c.alignment = Alignment(horizontal="center" if j else "left", vertical="center", wrap_text=True)
    for i, ligne in enumerate(lignes, 1):
        for j, v in enumerate(ligne):
            c = ws.cell(r0 + i, c0 + j, v)
            c.font, c.border = police(size=10), BORDURE
            if j in formats:
                c.number_format = formats[j]
            c.alignment = Alignment(horizontal="center" if j else "left")
    return r0 + len(lignes)


def graphique_barres(titre, donnees_ref, categories_ref, couleurs, horizontal=False, empile=False,
                     legende=True, hauteur=7.5, largeur=16, etiquettes=False):
    g = BarChart()
    g.type = "bar" if horizontal else "col"
    g.title = titre
    g.style = 2
    g.height, g.width = hauteur, largeur
    g.add_data(donnees_ref, titles_from_data=True)
    g.set_categories(categories_ref)
    if empile:
        g.grouping, g.overlap = "stacked", 100
    g.gapWidth = 60
    for serie, couleur in zip(g.series, couleurs):
        serie.graphicalProperties.solidFill = couleur
        serie.graphicalProperties.line.noFill = True
    if etiquettes:
        g.dataLabels = DataLabelList()
        g.dataLabels.showVal = True
        g.dataLabels.showSerName = g.dataLabels.showCatName = False
        g.dataLabels.showLegendKey = g.dataLabels.showPercent = False
    g.title.overlay = False
    g.y_axis.delete = False
    g.x_axis.delete = False
    g.y_axis.majorGridlines.spPr = GraphicalProperties(ln=LineProperties(solidFill=GRILLE, w=6350))
    if horizontal:
        g.x_axis.scaling.orientation = "maxMin"      # premier élément en haut
        g.y_axis.crosses = "max"                     # échelle des valeurs en bas, sous le graphique
    if not legende:
        g.legend = None
    else:
        g.legend.position = "r" if horizontal else "b"   # jamais sur l'échelle ni sur les barres
        g.legend.overlay = False
    return g


def construire_tableau_de_bord(ws, departements, categories, niveaux, statuts_stage, offres, annee):
    for col, l in zip("ABCDEFGHIJ", [2, 36, 14, 14, 14, 14, 14, 14, 14, 3]):
        ws.column_dimensions[col].width = l
    ws.sheet_view.showGridLines = False
    ws.merge_cells("B1:I1")
    ws["B1"] = "Tableau de bord RH – classeur d'analyse"
    ws["B1"].font = police(bold=True, size=18, color="FFFFFF")
    ws["B1"].fill = remplir(FOND_TITRE)
    ws["B1"].alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[1].height = 34
    ws["B2"] = MENTION
    ws["B2"].font = police(italic=True, size=9, color=ENCRE_2)

    # Filtres
    filtres = [("Date de situation", datetime.combine(DATE_REFERENCE, datetime.min.time()), FMT_DATE),
               ("Département", "Tous", None), ("Bureau", "Tous", None)]
    for i, (lib, val, fmt) in enumerate(filtres):
        r = 4 + i
        ws.merge_cells(f"B{r}:C{r}")
        ws[f"B{r}"] = lib
        ws[f"B{r}"].font = police(bold=True, size=10)
        c = ws[f"D{r}"]
        ws.merge_cells(f"D{r}:E{r}")
        c.value, c.fill, c.border = val, remplir(JAUNE), BORDURE
        c.font = police(bold=True, size=11, color="0000FF")
        c.alignment = Alignment(horizontal="center")
        if fmt:
            c.number_format = fmt
    ws.merge_cells("F4:I6")
    ws["F4"] = ("Modifiez les cellules jaunes : tous les indicateurs, tableaux et graphiques se "
                "recalculent. Date de situation : une date de l'année " + str(annee) + ". "
                "Le recrutement n'est pas filtré par département ni par bureau.")
    ws["F4"].font = police(size=9, color=ENCRE_2)
    ws["F4"].alignment = Alignment(wrap_text=True, vertical="center")

    v_date = DataValidation(type="date", operator="between", formula1=f"DATE({annee},1,1)",
                            formula2=f"DATE({annee},12,31)", showErrorMessage=True,
                            errorTitle="Date hors période", error=f"Saisissez une date de l'année {annee}.")
    v_dep = DataValidation(type="list", formula1="ListeDep", showErrorMessage=True)
    v_bur = DataValidation(type="list", formula1="ListeBur", showErrorMessage=True)
    for v, cellule in ((v_date, "D4"), (v_dep, "D5"), (v_bur, "D6")):
        ws.add_data_validation(v)
        v.add(cellule)

    # Registre mensuel (sert aussi aux tuiles) : lignes 33 à 44, total ligne 45
    R_MOIS = 33
    arret = "MIN(EOMONTH($B{r},0),DateSit)"
    present = 'COUNTIFS(cl_perim,1,cl_emb,"<="&{j})-COUNTIFS(cl_perim,1,cl_emb,"<="&{j},cl_sortie,"<="&{j})'
    lignes_mois = []
    for k in range(1, 13):
        r = R_MOIS + k
        a = arret.format(r=r)
        vide = f'IF($B{r}>DateSit,"",'
        lignes_mois.append([
            f"=DATE(YEAR(DateSit),{k},1)",
            f"={vide}{present.format(j=f'($B{r}-1)')})",
            f'={vide}COUNTIFS(cl_perim,1,cl_emb,">="&$B{r},cl_emb,"<="&{a}))',
            f'={vide}COUNTIFS(cl_perim,1,cl_sortie,">="&$B{r},cl_sortie,"<="&{a}))',
            f"={vide}{present.format(j=a)})",
            f"={vide}SUMIFS(INDEX(ab_mois,0,{k}),ab_perim,1))",
            f"={vide}F{r}*NETWORKDAYS($B{r},{a}))",
            f'=IF(OR(H{r}="",H{r}=0),"",G{r}/H{r})',
        ])
    r_tot = R_MOIS + 13
    lignes_mois.append(["Total année", "", f"=SUM(D{R_MOIS + 1}:D{R_MOIS + 12})",
                        f"=SUM(E{R_MOIS + 1}:E{R_MOIS + 12})", "",
                        f"=SUM(G{R_MOIS + 1}:G{R_MOIS + 12})", f"=SUM(H{R_MOIS + 1}:H{R_MOIS + 12})",
                        f'=IF(H{r_tot}=0,"",G{r_tot}/H{r_tot})'])

    # Tuiles d'indicateurs
    eff = "COUNTIFS(cl_perim,1,cl_present,1)"
    mois_f = f"F{R_MOIS + 1}:F{R_MOIS + 12}"
    tuiles = [
        [("Effectif actif", f"={eff}", FMT_ENTIER, "collaborateurs en poste"),
         ("Part de CDD", f'=IF({eff}=0,0,COUNTIFS(cl_perim,1,cl_present,1,cl_type,"CDD")/{eff})', "0%",
          "des collaborateurs en poste"),
         ("CDD à échéance ≤ 30 jours", "=COUNTIFS(cl_perim,1,cl_alerte,NivUrgent)", FMT_ENTIER,
          "dossier de fin de CDD à préparer"),
         ("Contrats échus", "=COUNTIFS(cl_perim,1,cl_alerte,NivEchu)", FMT_ENTIER, "à régulariser")],
        [("Jours d'absence réalisés", f"=G{r_tot}", FMT_ENTIER, "jours ouvrables depuis le 1er janvier"),
         ("Taux d'absentéisme", f"=IF(H{r_tot}=0,0,G{r_tot}/H{r_tot})", FMT_PCT,
          "jours d'absence / jours ouvrables × effectif"),
         ("Stagiaires en cours", '=COUNTIFS(st_perim,1,st_statut,"En cours")', FMT_ENTIER, "à la date de situation"),
         ("Demandes de congé en attente", '=COUNTIFS(ab_perim,1,ab_statut,"En attente")', FMT_ENTIER,
          "à traiter par le responsable")],
        [("Entrées depuis le 1er janvier", f"=D{r_tot}", FMT_ENTIER, "embauches"),
         ("Sorties depuis le 1er janvier", f"=E{r_tot}", FMT_ENTIER, "départs"),
         ("Taux de rotation", f"=IF(AVERAGE({mois_f})=0,0,E{r_tot}/AVERAGE({mois_f}))", FMT_PCT,
          "sorties / effectif moyen de fin de mois"),
         ("Candidatures reçues", '=COUNTIFS(cd_date,"<="&DateSit)', FMT_ENTIER, "toutes offres, sans filtre")],
    ]
    for i, rangee in enumerate(tuiles):
        r = 8 + 4 * i
        for j, (lib, formule, fmt, sous) in enumerate(rangee):
            c1, c2 = get_column_letter(2 + 2 * j), get_column_letter(3 + 2 * j)
            for rr, val, f in ((r, lib, police(bold=True, size=9, color=ENCRE_2)),
                               (r + 1, formule, police(bold=True, size=20, color=FOND_TITRE)),
                               (r + 2, sous, police(size=8, color=ENCRE_2))):
                ws.merge_cells(f"{c1}{rr}:{c2}{rr}")
                cel = ws[f"{c1}{rr}"]
                cel.value, cel.font = val, f
                cel.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                for col in (c1, c2):
                    ws[f"{col}{rr}"].fill = remplir(FOND_TUILE)
            ws[f"{c1}{r + 1}"].number_format = fmt
            ws.row_dimensions[r + 1].height = 30
        ws.row_dimensions[r + 2].height = 24

    # Effectif par département (filtre Bureau seulement) et échéances
    r0 = 21
    titre_section(ws, f"B{r0}", "Effectif en poste par département et type de contrat (filtre Bureau)", 4)
    lignes = []
    for i, dep in enumerate(departements):
        r = r0 + 2 + i
        base = f'COUNTIFS(cl_dep,$B{r},cl_present,1,cl_type,"{{t}}",cl_bur,IF(FiltreBur="Tous","*",FiltreBur))'
        lignes.append([dep, "=" + base.format(t="CDI"), "=" + base.format(t="CDD"), f"=C{r}+D{r}"])
    der_dep = ecrire_tableau(ws, r0 + 1, 2, ["Département", "CDI", "CDD", "Total"], lignes)
    for j, v in enumerate(["Total", f"=SUM(C{r0 + 2}:C{der_dep})", f"=SUM(D{r0 + 2}:D{der_dep})",
                           f"=SUM(E{r0 + 2}:E{der_dep})"]):
        c = ws.cell(der_dep + 1, 2 + j, v)
        c.font, c.border, c.fill = police(bold=True, size=10), BORDURE, remplir(FOND_SECTION)
        if j:
            c.alignment = Alignment(horizontal="center")

    titre_section(ws, f"G{r0}", "Échéances des contrats", 3)
    lignes = [[f"=Paramètres!$I${4 + i}", None, f"=COUNTIFS(cl_perim,1,cl_alerte,G{r0 + 2 + i})"]
              for i in range(len(niveaux))]
    ecrire_tableau(ws, r0 + 1, 7, ["Niveau d'alerte", "", "Contrats"], lignes)
    for i in range(len(niveaux)):
        ws.merge_cells(f"G{r0 + 2 + i}:H{r0 + 2 + i}")
        ws[f"G{r0 + 2 + i}"].alignment = Alignment(horizontal="left")
    ws.merge_cells(f"G{r0 + 1}:H{r0 + 1}")
    for niveau, couleur in ETATS.items():
        ws.conditional_formatting.add(f"G{r0 + 2}:I{r0 + 1 + len(niveaux)}",
                                      CellIsRule(operator="equal", formula=[f'"{niveau}"'], fill=remplir(couleur)))
    ws[f"G{r0 + 3 + len(niveaux)}"] = "Détail et filtres : feuille « Collaborateurs », colonne « Niveau d'alerte »."
    ws[f"G{r0 + 3 + len(niveaux)}"].font = police(italic=True, size=8, color=ENCRE_2)

    # Registre mensuel
    titre_section(ws, f"B{R_MOIS - 1}", f"Registre mensuel {annee} : effectifs et absentéisme (filtres appliqués)")
    ecrire_tableau(ws, R_MOIS, 2, ["Mois", "Effectif début", "Entrées", "Sorties", "Effectif fin",
                                   "Jours d'absence", "Jours ouvrables × effectif", "Taux d'absentéisme"],
                   lignes_mois, {0: FMT_MOIS, 6: FMT_ENTIER, 7: FMT_PCT})
    ws[f"B{r_tot}"].font = police(bold=True, size=10)
    ws.row_dimensions[R_MOIS].height = 42
    ws[f"B{r_tot + 1}"] = ("Taux d'absentéisme = jours d'absence réalisés / (effectif de fin de mois × jours "
                           "ouvrables du mois). Approximation : jours fériés non déduits.")
    ws[f"B{r_tot + 1}"].font = police(italic=True, size=8, color=ENCRE_2)

    # Absences par catégorie et stagiaires
    r1 = r_tot + 3
    titre_section(ws, f"B{r1}", "Jours d'absence réalisés par catégorie", 3)
    lignes = [[cat, f"=SUMIFS(ab_total,ab_perim,1,ab_cat,$B{r1 + 2 + i})",
               f'=IF(SUM($C${r1 + 2}:$C${r1 + 1 + len(categories)})=0,0,'
               f'C{r1 + 2 + i}/SUM($C${r1 + 2}:$C${r1 + 1 + len(categories)}))']
              for i, cat in enumerate(categories)]
    ecrire_tableau(ws, r1 + 1, 2, ["Catégorie", "Jours", "Part"], lignes, {1: FMT_ENTIER, 2: FMT_PCT})
    titre_section(ws, f"G{r1}", "Stagiaires par statut", 3)
    lignes = [[f"=Paramètres!$H${4 + i}", None, f"=COUNTIFS(st_perim,1,st_statut,G{r1 + 2 + i})"]
              for i in range(len(statuts_stage))]
    ecrire_tableau(ws, r1 + 1, 7, ["Statut", "", "Stagiaires"], lignes)
    for i in range(len(statuts_stage) + 1):
        ws.merge_cells(f"G{r1 + 1 + i}:H{r1 + 1 + i}")
        ws[f"G{r1 + 1 + i}"].alignment = Alignment(horizontal="left")

    # Entonnoir de recrutement
    r2 = r1 + 4 + len(categories)
    titre_section(ws, f"B{r2}", "Recrutement : candidatures ayant franchi chaque étape "
                                "(désistements exclus, sans filtre)", 2 + len(offres))
    lignes = []
    for i, (k, lib) in enumerate(rc.ETAPES.items()):
        r = r2 + 2 + i
        ligne = [f"{k}. {lib}"]
        for j in range(len(offres)):
            col = get_column_letter(3 + j)
            ligne.append(f'=COUNTIFS(ev_offre,{col}${r2 + 1},ev_etape,{k},'
                         f'ev_res,"<>{rc.DESISTEMENT}",ev_date,"<="&DateSit)')
        lignes.append(ligne)
    der_ent = ecrire_tableau(ws, r2 + 1, 2, ["Étape"] + [o["offre_id"] for o in offres], lignes)
    for j, o in enumerate(offres):
        ws.cell(der_ent + 1, 3 + j, o["intitule"]).font = police(italic=True, size=8, color=ENCRE_2)

    # Graphiques (à droite des tableaux, colonne K)
    g = graphique_barres("Effectif par département", Reference(ws, min_col=3, max_col=4, min_row=r0 + 1,
                                                                max_row=der_dep),
                         Reference(ws, min_col=2, min_row=r0 + 2, max_row=der_dep), [BLEU, ORANGE],
                         horizontal=True, empile=True, hauteur=8)
    ws.add_chart(g, "K3")
    g = graphique_barres("Effectif de fin de mois", Reference(ws, min_col=6, min_row=R_MOIS, max_row=R_MOIS + 12),
                         Reference(ws, min_col=2, min_row=R_MOIS + 1, max_row=R_MOIS + 12), [BLEU], legende=False)
    g.x_axis.number_format = "mmm"
    ws.add_chart(g, "K20")
    g = graphique_barres("Taux d'absentéisme mensuel", Reference(ws, min_col=9, min_row=R_MOIS,
                                                                  max_row=R_MOIS + 12),
                         Reference(ws, min_col=2, min_row=R_MOIS + 1, max_row=R_MOIS + 12), [BLEU], legende=False)
    g.x_axis.number_format = "mmm"
    g.y_axis.number_format = "0%"
    ws.add_chart(g, "K36")
    g = graphique_barres("Jours d'absence par catégorie", Reference(ws, min_col=3, min_row=r1 + 1,
                                                                     max_row=r1 + 1 + len(categories)),
                         Reference(ws, min_col=2, min_row=r1 + 2, max_row=r1 + 1 + len(categories)), [BLEU],
                         horizontal=True, legende=False, hauteur=6, etiquettes=True)
    ws.add_chart(g, "K52")
    g = graphique_barres("Recrutement : candidatures par étape",
                         Reference(ws, min_col=3, max_col=2 + len(offres), min_row=r2 + 1, max_row=der_ent),
                         Reference(ws, min_col=2, min_row=r2 + 2, max_row=der_ent), [BLEU, ORANGE],
                         horizontal=True, hauteur=9)
    ws.add_chart(g, "K65")
    ws.freeze_panes = "A7"


def construire_lisez_moi(ws, annee):
    entete_feuille(ws, "NURU HR Digital Portfolio – classeur d'analyse RH", [3, 110])
    ws["A1"].value = None
    ws["B1"] = "NURU HR Digital Portfolio – classeur d'analyse RH"
    ws["B1"].font = police(bold=True, size=16, color=FOND_TITRE)
    ws["A2"].value = None
    ws["B2"] = MENTION
    ws["B2"].font = police(bold=True, size=10, color="C00000")
    texte = [
        ("Objet", True),
        ("Tableau de bord RH manipulable : effectifs, contrats et échéances, absences, stagiaires et "
         "recrutement, calculés à partir des données fictives du projet (dossier data/raw).", False),
        ("Comment l'utiliser", True),
        ("1. Ouvrez la feuille « Tableau de bord ».", False),
        (f"2. Modifiez les cellules jaunes : date de situation (année {annee}), département, bureau.", False),
        ("3. Les tuiles, tableaux et graphiques se recalculent. Les feuilles de données ont des filtres "
         "(flèches des en-têtes) pour explorer le détail, par exemple les contrats « Urgent ».", False),
        ("4. Si les valeurs n'apparaissent pas, cliquez sur « Activer la modification » (mode protégé), "
         "puis appuyez sur F9.", False),
        ("Feuilles", True),
        ("Tableau de bord : indicateurs, registre mensuel, graphiques.", False),
        ("Paramètres : seuils d'alerte des contrats (modifiables) et listes de référence.", False),
        ("Collaborateurs, Contrats, Absences, Stagiaires, Candidatures, Étapes recrutement : données sources "
         "et colonnes de calcul (en-têtes « 1/0 », dates, niveaux d'alerte).", False),
        ("Règles de calcul", True),
        ("Une personne sortie le jour J ne compte plus dans l'effectif à la fin du jour J.", False),
        ("Le type de contrat est celui du dernier contrat commencé à la date de situation.", False),
        ("Jours d'absence : jours ouvrables du lundi au vendredi, absences approuvées ou constatées, du "
         "1er janvier à la date de situation. Jours fériés non déduits (simplification).", False),
        ("Taux d'absentéisme et taux de rotation : indicateurs d'analyse calculés sur données fictives, "
         "méthode indiquée sous chaque tableau.", False),
        ("Les seuils 30 / 60 / 90 jours sont des seuils d'alerte internes, pas des règles juridiques. "
         "Toute règle du Code du travail de la RDC (durée des CDD, préavis, congés) doit être vérifiée dans "
         "le texte en vigueur.", False),
        ("Protection des données", True),
        ("Aucune date de naissance, e-mail, salaire, genre individuel, motif de sortie, note de stage ou "
         "nom de candidat. Les motifs de santé sont regroupés sous « Absence justifiée (motif confidentiel) ».",
         False),
        ("Le classeur organise l'information : les décisions (fin de CDD, recrutement) restent prises par "
         "des personnes.", False),
        ("Origine", True),
        (f"Généré par dashboard/generer_classeur_excel.py le {date.today():%d/%m/%Y}. Ne pas modifier les "
         "données à la main : relancer le script après la chaîne de traitement.", False),
    ]
    r = 4
    for t, est_titre in texte:
        c = ws.cell(r, 2, t)
        c.font = police(bold=est_titre, size=11 if est_titre else 10,
                        color=FOND_TITRE if est_titre else ENCRE)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if est_titre:
            ws.row_dimensions[r].height = 22
        r += 1


if __name__ == "__main__":
    classeur = construire()
    classeur.active = classeur.sheetnames.index("Tableau de bord")
    classeur.save(SORTIE)
    print(f"  -> {SORTIE.relative_to(RACINE)}")
