"""Graphiques du projet (matplotlib), enregistrés en PNG dans reports/figures."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import FOCUS, LABELS

ACCENT = "#7C3AED"      # Bénin
GOLD = "#E0A800"
INK = "#1A1A2E"
GREY = "#B8B8C8"
SOURCE = "Source : Banque mondiale, World Development Indicators (CC BY 4.0)"
LINE_COLORS = ["#0E7490", "#DC2626", "#16A34A", "#EA580C", "#2563EB", "#DB2777", "#65A30D"]

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 150, "font.size": 10.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "axes.titlesize": 12.5, "axes.grid": True,
    "grid.alpha": 0.25, "axes.edgecolor": "#555", "legend.frameon": False,
})


def _finish(fig, path: Path | None):
    fig.text(0.01, 0.005, SOURCE, fontsize=7.5, color="#777")
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    if path is not None:
        fig.savefig(path, bbox_inches="tight")
    return fig


def trend(panel: pd.DataFrame, column: str, title: str, path: Path | None = None,
          start: int = 1990, ylabel: str | None = None):
    """Évolution d'un indicateur : Bénin en couleur, voisins, moyenne Afrique subsaharienne."""
    fig, ax = plt.subplots(figsize=(9, 5))
    data = panel[panel["year"] >= start]
    for color, iso3 in zip(LINE_COLORS, [c for c in FOCUS if c != "BEN"]):
        s = data[data.iso3 == iso3].dropna(subset=[column])
        ax.plot(s.year, s[column], color=color, lw=1.4, alpha=0.75, label=s.country.iloc[0])
    ssf = data[data.iso3 == "SSF"].dropna(subset=[column])
    ax.plot(ssf.year, ssf[column], color=INK, lw=1.6, ls="--", label="Afrique subsaharienne")
    ben = data[data.iso3 == "BEN"].dropna(subset=[column])
    ax.plot(ben.year, ben[column], color=ACCENT, lw=3.2, label="Bénin", zorder=5)
    ax.annotate(f"{ben[column].iloc[-1]:.1f}", (ben.year.iloc[-1], ben[column].iloc[-1]),
                xytext=(5, 0), textcoords="offset points", color=ACCENT, fontweight="bold", va="center")
    ax.set_title(title)
    ax.set_ylabel(ylabel or LABELS.get(column, column))
    ax.legend(ncol=3, fontsize=8.5, loc="best")
    return _finish(fig, path)


def ranking(table: pd.DataFrame, column: str, title: str, path: Path | None = None, fmt="{:,.0f}"):
    """Barres horizontales triées, Bénin mis en évidence."""
    t = table.sort_values(column)
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = [ACCENT if i == "BEN" else (INK if i == "SSF" else GREY) for i in t.iso3]
    ax.barh(t.country, t[column], color=colors)
    for y, v in enumerate(t[column]):
        ax.text(v, y, " " + fmt.format(v).replace(",", " "), va="center", fontsize=8.5)
    ax.set_title(title)
    ax.set_xlabel(LABELS.get(column, column))
    ax.grid(axis="y", visible=False)
    return _finish(fig, path)


def dumbbell(change_table: pd.DataFrame, title: str, xlabel: str, path: Path | None = None,
             start_label="", end_label="", note: str = ""):
    """Comparaison avant / après pour chaque pays."""
    t = change_table.sort_values("end")
    fig, ax = plt.subplots(figsize=(8, 6))
    y = np.arange(len(t))
    ax.hlines(y, t["start"], t["end"], color=GREY, lw=2.5)
    ax.scatter(t["start"], y, color=GREY, s=45, label=start_label, zorder=3)
    colors = [ACCENT if i == "BEN" else (INK if i == "SSF" else GOLD) for i in t.index]
    ax.scatter(t["end"], y, color=colors, s=60, label=end_label, zorder=4)
    ax.set_yticks(y, t["country"])
    for yy, (iso3, row) in zip(y, t.iterrows()):
        ax.text(row["end"] + 1.2, yy, f"{row['end']:.0f}", va="center", fontsize=8.5,
                color=ACCENT if iso3 == "BEN" else INK)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.grid(axis="y", visible=False)
    ax.legend(loc="upper left")
    if note:
        ax.text(0.99, 0.02, note, transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color="#666")
    return _finish(fig, path)


def heatmap(corr: pd.DataFrame, title: str, path: Path | None = None):
    labels = [LABELS.get(c, c).split(" (")[0] for c in corr.columns]
    fig, ax = plt.subplots(figsize=(8.5, 7))
    im = ax.imshow(corr.to_numpy(), cmap="PuOr_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(labels)), labels, rotation=40, ha="right")
    ax.set_yticks(range(len(labels)), labels)
    for i in range(len(labels)):
        for j in range(len(labels)):
            v = corr.iat[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8,
                    color="white" if abs(v) > 0.6 else INK)
    ax.grid(False)
    fig.colorbar(im, ax=ax, shrink=0.8, label="corrélation de Spearman")
    ax.set_title(title)
    return _finish(fig, path)


def plot_temporal_benin(detail: pd.DataFrame, path: Path | None = None, history: pd.DataFrame | None = None):
    """Prédictions 2017–2024 pour le Bénin, comparées aux valeurs observées."""
    b = detail[detail.iso3 == "BEN"]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(b.year, b["life_expectancy"], color=INK, lw=3, marker="o", label="Observé")
    styles = {"Référence : dernière valeur connue": (GREY, ":"),
              "Référence : tendance par pays": (GOLD, "--"),
              "Régression ridge": ("#0E7490", "-"), "Forêt aléatoire": ("#16A34A", "-"),
              "Tendance par pays + correction ridge": (ACCENT, "-")}
    for name, (color, ls) in styles.items():
        ax.plot(b.year, b[name], color=color, ls=ls, lw=2, marker=".", label=name)
    ax.set_title("Bénin — espérance de vie 2017–2024 : observé vs prédit (modèles appris sur 2000–2016)")
    ax.set_ylabel("Années")
    ax.legend(fontsize=8.5)
    return _finish(fig, path)


def plot_holdout(holdout: pd.DataFrame, temporal: pd.DataFrame, path: Path | None = None):
    """MAE des modèles et des références pour les deux protocoles."""
    fig, axes = plt.subplots(2, 1, figsize=(9, 7))
    for ax, table, title in [(axes[0], temporal, "Split temporel (test 2017–2024)"),
                             (axes[1], holdout, "Pays jamais vu (leave-one-country-out)")]:
        t = table.sort_values("MAE", ascending=False)
        colors = [GREY if m.startswith("Référence") else (ACCENT if "Tendance" in m else "#0E7490")
                  for m in t.modele]
        ax.barh(t.modele, t.MAE, color=colors)
        for y, v in enumerate(t.MAE):
            ax.text(v, y, f" {v:.2f}", va="center", fontsize=9)
        ax.set_title(title)
        ax.set_xlabel("MAE (années, plus bas = mieux)")
        ax.grid(axis="y", visible=False)
    return _finish(fig, path)


def plot_importance(imp: pd.DataFrame, path: Path | None = None):
    t = imp.sort_values("importance_permutation_mae")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(t.variable, t.importance_permutation_mae, color=ACCENT)
    ax.set_title("Modèle hybride : importance par permutation (test 2017–2024)")
    ax.set_xlabel("Hausse de la MAE quand la variable est mélangée (années)")
    ax.grid(axis="y", visible=False)
    return _finish(fig, path)
