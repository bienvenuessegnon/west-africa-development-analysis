"""Chiffres clés et figures d'analyse exploratoire, calculés depuis le panel.

Usage : python -m src.report   (écrit reports/key_figures.json et reports/figures/0[1-5]_*.png)
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import plots
from .analysis import cagr, change, correlations, latest, rank_of, value_at
from .config import COUNTRIES, FIGURES_DIR, ROOT
from .data import load_panel

CORR_COLUMNS = ["life_expectancy", "gdp_pc", "electricity", "internet", "water",
                "urban_pct", "fertility", "under5_mortality"]


def compute(panel=None) -> dict:
    panel = load_panel() if panel is None else panel
    countries = panel[panel.iso3.isin(COUNTRIES)]
    last_year = int(countries.dropna(subset=["life_expectancy", "gdp_pc", "electricity", "internet"])
                    .groupby("year").size().loc[lambda s: s == len(COUNTRIES)].index.max())
    ben = panel[panel.iso3 == "BEN"].set_index("year")
    figures = {"reference_year": last_year, "indicators": {}}
    for col in ["life_expectancy", "gdp_pc", "electricity", "internet", "fertility",
                "under5_mortality", "urban_pct", "water"]:
        snap = countries[countries.year == last_year][["iso3", "country", col]].dropna()
        figures["indicators"][col] = {
            "benin": float(ben.loc[last_year, col]),
            "benin_rank_of_16": rank_of(snap, col, "BEN"),
            "west_africa_median": float(snap[col].median()),
            "ssf": float(value_at(panel, col, last_year).get("SSF")),
            "max": [snap.loc[snap[col].idxmax(), "country"], float(snap[col].max())],
            "min": [snap.loc[snap[col].idxmin(), "country"], float(snap[col].min())],
            "benin_2000": float(ben.loc[2000, col]) if 2000 in ben.index else None,
        }
    figures["benin_gdp_pc_cagr_2000_last"] = cagr(ben.loc[2000, "gdp_pc"], ben.loc[last_year, "gdp_pc"],
                                                  last_year - 2000)
    figures["benin_population"] = {"2000": float(ben.loc[2000, "population"]),
                                   str(last_year): float(ben.loc[last_year, "population"])}
    le = change(countries, "life_expectancy", 2000, last_year)
    figures["life_expectancy_gain_2000_last"] = {
        "benin": float(le.loc["BEN", "change"]), "median": float(le["change"].median()),
        "max": [le.iloc[0]["country"], float(le.iloc[0]["change"])],
        "min": [le.iloc[-1]["country"], float(le.iloc[-1]["change"])],
    }
    el = change(countries, "electricity", 2000, last_year)
    figures["electricity_gain_2000_last"] = {
        "benin": float(el.loc["BEN", "change"]), "median": float(el["change"].median()),
        "n_countries": int(el["change"].notna().sum()),
    }
    corr = correlations(countries, CORR_COLUMNS)
    figures["spearman_with_life_expectancy"] = corr["life_expectancy"].drop("life_expectancy") \
        .sort_values().round(3).to_dict()
    figures["n_country_years_corr"] = int(countries[CORR_COLUMNS].dropna().shape[0])
    return figures, corr


def make_figures(panel=None) -> dict:
    panel = load_panel() if panel is None else panel
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    figures, corr = compute(panel)
    year = figures["reference_year"]
    countries = panel[panel.iso3.isin(COUNTRIES)]
    plots.trend(panel, "life_expectancy", "Espérance de vie à la naissance, 1990–" + str(year),
                FIGURES_DIR / "01_esperance_de_vie.png", ylabel="Années")
    gdp = latest(panel[(panel.year <= year) & (panel.iso3.isin(list(COUNTRIES) + ["SSF"]))], "gdp_pc")
    plots.ranking(gdp, "gdp_pc", f"PIB par habitant en {year} (USD constants 2015)",
                  FIGURES_DIR / "02_pib_par_habitant.png")
    el_all = change(panel[panel.iso3.isin(list(COUNTRIES) + ["SSF"])], "electricity", 2000, year)
    missing = ", ".join(el_all[el_all["start"].isna()]["country"])
    plots.dumbbell(el_all.dropna(), f"Accès à l'électricité : 2000 → {year}", "% de la population",
                   FIGURES_DIR / "03_electricite.png", start_label="2000", end_label=str(year),
                   note=f"Pas de donnée en 2000 : {missing}" if missing else "")
    plots.trend(panel, "internet", f"Utilisateurs d'Internet, 2000–{year}",
                FIGURES_DIR / "04_internet.png", start=2000, ylabel="% de la population")
    plots.heatmap(corr, "Corrélations entre indicateurs (16 pays, toutes années)",
                  FIGURES_DIR / "05_correlations.png")
    plt.close("all")
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "key_figures.json").write_text(json.dumps(figures, indent=2, ensure_ascii=False))
    return figures


if __name__ == "__main__":
    print(json.dumps(make_figures(), indent=2, ensure_ascii=False))
