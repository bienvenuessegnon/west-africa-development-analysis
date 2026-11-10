"""Statistiques descriptives réutilisées par les notebooks, le rapport et les tests."""
from __future__ import annotations

import numpy as np
import pandas as pd


def latest(panel: pd.DataFrame, column: str) -> pd.DataFrame:
    """Dernière valeur disponible de ``column`` pour chaque entité, avec son année."""
    rows = panel.dropna(subset=[column]).sort_values("year").groupby("iso3").tail(1)
    return (rows[["iso3", "country", "year", column]]
            .sort_values(column, ascending=False).reset_index(drop=True))


def value_at(panel: pd.DataFrame, column: str, year: int) -> pd.Series:
    """Valeur de ``column`` pour une année donnée, indexée par code ISO3."""
    return panel.loc[panel["year"] == year].set_index("iso3")[column]


def change(panel: pd.DataFrame, column: str, start: int, end: int) -> pd.DataFrame:
    """Valeurs en ``start`` et ``end`` et variation absolue, par entité."""
    out = pd.DataFrame({"start": value_at(panel, column, start), "end": value_at(panel, column, end)})
    out["change"] = out["end"] - out["start"]
    names = panel.drop_duplicates("iso3").set_index("iso3")["country"]
    out.insert(0, "country", names.reindex(out.index))
    return out.sort_values("change", ascending=False)


def cagr(start: float, end: float, years: int) -> float:
    """Taux de croissance annuel moyen (en %)."""
    if start <= 0 or years <= 0:
        raise ValueError("start doit être > 0 et years > 0")
    return float(((end / start) ** (1 / years) - 1) * 100)


def rank_of(table: pd.DataFrame, column: str, iso3: str) -> int:
    """Rang (1 = valeur la plus élevée) d'un pays dans une table triée ou non."""
    ordered = table.sort_values(column, ascending=False).reset_index(drop=True)
    return int(ordered.index[ordered["iso3"] == iso3][0]) + 1


def correlations(panel: pd.DataFrame, columns: list[str], method: str = "spearman") -> pd.DataFrame:
    """Corrélations entre indicateurs sur l'ensemble des observations pays-année."""
    return panel[columns].corr(method=method)


def log_gdp(panel: pd.DataFrame) -> pd.Series:
    return np.log(panel["gdp_pc"])
