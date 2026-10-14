# documents : procédures, courriers et rapports

> Documents rédigés pour un cas fictif. Portfolio personnel, non officiel de Nuru.
> Les références au Code du travail de la RDC doivent être vérifiées dans le texte en vigueur.

| Sous-dossier | Contenu prévu |
|---|---|
| `procedures/` | Procédures RH : gestion des congés, archivage des dossiers, accueil des stagiaires, recrutement |
| `modeles_courriers/` | Modèles : attestation de travail, notification de fin ou de renouvellement de CDD, lettre d'acceptation de stage |
| `rapports/` | Rapport mensuel RH (octobre 2026) ; **rapport de projet complet** en Word et PDF (`Rapport_projet_NURU_HR_Portfolio.docx` / `.pdf`) ; **présentation PowerPoint** de 14 diapositives avec notes d'orateur (`Presentation_NURU_HR_Portfolio.pptx`) |

Régénérer le rapport de projet et la présentation (après avoir complété `portfolio/profil.json`) :
```bash
python documents/rapports/generer_rapport_complet.py   # Word + PDF
python documents/rapports/generer_presentation.py      # PowerPoint (+ aperçus de contrôle)
```
Tous les chiffres sont recalculés à partir des données et les tests sont exécutés à chaque génération.
