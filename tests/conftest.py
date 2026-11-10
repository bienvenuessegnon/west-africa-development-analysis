import numpy as np
import pandas as pd
import pytest

from src.config import COLUMNS


@pytest.fixture
def synthetic_panel() -> pd.DataFrame:
    """Panel synthétique : espérance de vie strictement linéaire par pays, indicateurs bruités."""
    rng = np.random.default_rng(0)
    rows = []
    for k, iso3 in enumerate(["AAA", "BBB", "CCC", "DDD"]):
        for year in range(2000, 2025):
            t = year - 2000
            row = {c: np.nan for c in COLUMNS.values()}
            row.update({
                "iso3": iso3, "country": f"Pays {iso3}", "is_aggregate": False, "year": year,
                "life_expectancy": 50 + 2 * k + 0.4 * t,
                "gdp_pc": 600 * (1 + k) * 1.02 ** t, "electricity": 10 + 2 * t + k,
                "water": 50 + t + rng.normal(0, 0.5), "fertility": 6 - 0.05 * t - 0.2 * k,
                "urban_pct": 30 + 0.5 * t + k, "internet": 0.1 + 1.5 * t,
            })
            rows.append(row)
    return pd.DataFrame(rows)
