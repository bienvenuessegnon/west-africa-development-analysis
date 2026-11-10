"""Génère et exécute les notebooks (les sorties sont enregistrées dans les .ipynb).

Usage : python scripts/build_notebooks.py
"""
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks"
SETUP = """import sys
from pathlib import Path
ROOT = Path.cwd().resolve().parent if Path.cwd().name == "notebooks" else Path.cwd().resolve()
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
%matplotlib inline
pd.set_option("display.precision", 2)
from src.config import COUNTRIES, FOCUS, LABELS
from src.data import load_panel
from src import analysis, plots
panel = load_panel()
countries = panel[~panel.is_aggregate]
"""

EDA = [
    ("md", "# 01 — Exploration : le Bénin et l'Afrique de l'Ouest (1990–2024)\n\n"
           "Données : **World Development Indicators** (Banque mondiale, CC BY 4.0), 16 pays d'Afrique de l'Ouest "
           "+ agrégats Afrique subsaharienne et Monde. Instantané téléchargé via l'API (voir `data/raw/metadata.json`).\n\n"
           "**Questions**\n1. Où se situe le Bénin face à ses voisins aujourd'hui ?\n"
           "2. Comment la santé, l'électricité et Internet ont-ils évolué depuis 2000 ?\n"
           "3. Quels indicateurs évoluent avec l'espérance de vie ?"),
    ("code", SETUP + "print(panel.shape)\nprint(panel.year.min(), '–', panel.year.max(), '·', countries.iso3.nunique(), 'pays')\npanel.head()"),
    ("md", "## 1. Qualité des données\nPart de valeurs manquantes par indicateur (pays uniquement, 1990–2024). "
           "L'achèvement du primaire est très lacunaire : il est exclu des analyses principales."),
    ("code", "(countries[list(LABELS)].isna().mean() * 100).round(1).sort_values().rename('% manquant').to_frame()"),
    ("md", "## 2. Le Bénin face à ses voisins (dernière année complète)"),
    ("code", "from src.report import compute\nkey, corr = compute(panel)\nyear = key['reference_year']\n"
             "snap = countries[countries.year == year]\n"
             "cols = ['life_expectancy', 'gdp_pc', 'electricity', 'internet', 'water', 'fertility', 'under5_mortality', 'urban_pct']\n"
             "table = snap.set_index('country')[cols].rename(columns=lambda c: LABELS[c].split(' (')[0])\n"
             "print('Année de référence :', year)\n"
             "table.loc[['Bénin', 'Togo', 'Nigeria', 'Niger', 'Burkina Faso', 'Ghana', \"Côte d'Ivoire\", 'Sénégal']].round(1)"),
    ("code", "pd.DataFrame({c: {'Bénin': v['benin'], 'rang Bénin /16': v['benin_rank_of_16'], 'médiane Afrique de l\\'Ouest': v['west_africa_median'],\n"
             "                   'Afrique subsaharienne': v['ssf']} for c, v in key['indicators'].items()}).T.round(1)"),
    ("code", "gdp = analysis.latest(panel[(panel.year <= year) & panel.iso3.isin(list(COUNTRIES) + ['SSF'])], 'gdp_pc')\n"
             "plots.ranking(gdp, 'gdp_pc', f'PIB par habitant en {year} (USD constants 2015)');\n"
             "print(f\"Croissance annuelle moyenne du PIB/hab. du Bénin 2000–{year} : {key['benin_gdp_pc_cagr_2000_last']:.2f} %\")"),
    ("md", "## 3. Trajectoires depuis 1990"),
    ("code", "plots.trend(panel, 'life_expectancy', f'Espérance de vie à la naissance, 1990–{year}', ylabel='Années');"),
    ("code", "le = analysis.change(countries, 'life_expectancy', 2000, year)\nle.round(1)"),
    ("md", "Le Bénin partait d'un niveau relativement élevé en 2000, mais affiche le **plus petit gain** des 16 pays sur la période : "
           "les pays qui partaient de très bas (Sierra Leone, Guinée-Bissau, Niger…) ont rattrapé une partie de leur retard."),
    ("code", "el = analysis.change(panel[panel.iso3.isin(list(COUNTRIES) + ['SSF'])], 'electricity', 2000, year)\n"
             "plots.dumbbell(el.dropna(), f\"Accès à l'électricité : 2000 → {year}\", '% de la population', start_label='2000', end_label=str(year));\n"
             "el.round(1)"),
    ("code", "plots.trend(panel, 'internet', f\"Utilisateurs d'Internet, 2000–{year}\", start=2000, ylabel='% de la population');"),
    ("code", "ben = panel[panel.iso3 == 'BEN'].set_index('year')\n"
             "ben.loc[[2000, 2010, 2020, year], ['population', 'urban_pct', 'fertility', 'under5_mortality', 'electricity', 'internet']].round(1)"),
    ("md", "## 4. Corrélations entre indicateurs\nCorrélation de Spearman sur toutes les observations pays-année complètes. "
           "Attention : ces indicateurs progressent tous avec le temps, une partie des corrélations reflète donc une tendance commune."),
    ("code", "plots.heatmap(corr, 'Corrélations entre indicateurs (16 pays, toutes années)');\n"
             "print('Observations complètes :', key['n_country_years_corr'])\n"
             "pd.Series(key['spearman_with_life_expectancy'], name='Spearman avec l\\'espérance de vie')"),
    ("md", "## À retenir\n- Le Bénin est dans le milieu du peloton pour le PIB par habitant et l'électricité, mais en dessous de la médiane régionale pour l'espérance de vie, Internet et l'eau potable.\n"
           "- Les progrès d'accès à l'électricité et à Internet sont massifs dans toute la région depuis 2000.\n"
           "- L'espérance de vie est très liée à la mortalité infantile et à la fécondité (corrélations négatives fortes) ; le PIB par habitant n'y est que modérément associé.\n"
           "- Corrélation ≠ causalité : ces liens sont descriptifs."),
]

MODEL = [
    ("md", "# 02 — Modélisation : prédire l'espérance de vie\n\n"
           "Cible : espérance de vie à la naissance. Variables : log(PIB/hab.), électricité, eau potable, fécondité, urbanisation, Internet "
           "(la mortalité infantile est exclue : elle entre presque mécaniquement dans le calcul de l'espérance de vie).\n\n"
           "Deux protocoles, chacun avec une **référence** à battre :\n"
           "1. **Temporel** — apprendre sur 2000–2016, tester sur 2017–2024. Références : dernière valeur connue, tendance linéaire par pays. "
           "Le choix du modèle se fait sur une validation 2013–2016 (apprentissage 2000–2012), sans regarder le test.\n"
           "2. **Pays jamais vu** — leave-one-country-out. Référence : moyenne des autres pays la même année."),
    ("code", SETUP + "from src.model import (make_dataset, evaluate_validation, evaluate_temporal, evaluate_country_holdout,\n"
             "                       importances, FEATURES, TARGET, HYBRID)\n"
             "df = make_dataset(panel)\nprint(len(df), 'observations complètes,', df.iso3.nunique(), 'pays,', df.year.min(), '–', df.year.max())"),
    ("md", "## 1. Sélection sur la validation (2013–2016)"),
    ("code", "evaluate_validation(df).round(3)"),
    ("md", "La tendance par pays est déjà une référence très forte. Le modèle hybride (tendance + correction ridge) est le meilleur sur la validation : "
           "c'est lui que l'on retient avant de regarder le test."),
    ("md", "## 2. Test 2017–2024"),
    ("code", "temporal, detail = evaluate_temporal(df)\ntemporal.round(3)"),
    ("code", "plots.plot_temporal_benin(detail);\nben = detail[detail.iso3 == 'BEN']\n"
             "(ben[temporal.modele].sub(ben[TARGET], axis=0).abs().mean().rename('MAE Bénin (années)')).round(3)"),
    ("md", "## 3. Un pays jamais vu"),
    ("code", "holdout, holdout_detail = evaluate_country_holdout(df)\nholdout.round(3)"),
    ("code", "err = holdout_detail.assign(erreur=lambda d: (d['Régression ridge'] - d[TARGET]).abs())\n"
             "err.groupby('country').erreur.mean().sort_values(ascending=False).round(2).rename('MAE ridge par pays').to_frame()"),
    ("md", "Prédire le **niveau** d'espérance de vie d'un pays à partir de ses seuls indicateurs ne fait pas mieux que la moyenne des autres pays : "
           "les écarts entre pays tiennent à des facteurs absents des données (systèmes de santé, conflits, épidémies, paludisme…)."),
    ("md", "## 4. Diagnostic du modèle hybride"),
    ("code", "imp = importances(df)\nplots.plot_importance(imp);\nimp.round(3)"),
    ("md", "## Conclusions\n"
           "- Pour la prévision à court terme, **la trajectoire passée du pays** est l'information la plus utile : la tendance par pays est difficile à battre.\n"
           "- Le modèle hybride ne l'améliore que légèrement en moyenne, et pas pour le Bénin ; la correction repose surtout sur Internet, "
           "extrapolé hors de la plage d'apprentissage. Ce gain ne doit pas être sur-interprété.\n"
           "- Les modèles « en niveau » (ridge, forêt aléatoire) échouent à généraliser dans le temps et entre pays.\n"
           "- Limites : 16 pays seulement, données estimées et révisées par la Banque mondiale, choc de la COVID-19 (2020–2021) dans le test, corrélation ≠ causalité."),
]


def build(name, cells):
    nb = nbf.v4.new_notebook()
    nb.cells = [nbf.v4.new_markdown_cell(s) if kind == "md" else nbf.v4.new_code_cell(s) for kind, s in cells]
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    NotebookClient(nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(NB)}}).execute()
    nbf.write(nb, NB / name)
    print("exécuté :", NB / name)


if __name__ == "__main__":
    build("01_exploration.ipynb", EDA)
    build("02_modelisation.ipynb", MODEL)
