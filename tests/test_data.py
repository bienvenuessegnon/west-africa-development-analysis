import pandas as pd
import pytest

from src.config import COLUMNS, COUNTRIES, PANEL_FILE
from src.data import build_panel, fetch_indicator


def test_build_panel_pivots_long_to_wide():
    raw = pd.DataFrame({
        "iso3": ["BEN", "BEN", "TGO"], "year": [2020, 2020, 2020],
        "indicator": ["SP.DYN.LE00.IN", "NY.GDP.PCAP.KD", "SP.DYN.LE00.IN"],
        "value": [60.0, 1300.0, 61.0],
    })
    panel = build_panel(raw)
    ben = panel.set_index("iso3").loc["BEN"]
    assert ben["life_expectancy"] == 60.0 and ben["gdp_pc"] == 1300.0
    assert ben["country"] == "Bénin" and not ben["is_aggregate"]
    assert set(COLUMNS.values()) <= set(panel.columns)


def test_build_panel_rejects_duplicates():
    raw = pd.DataFrame({"iso3": ["BEN"] * 2, "year": [2020] * 2,
                        "indicator": ["SP.DYN.LE00.IN"] * 2, "value": [1.0, 2.0]})
    with pytest.raises(ValueError):
        build_panel(raw)


class FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return [{"lastupdated": "2026-10-08"},
                [{"countryiso3code": "BEN", "date": "2023", "value": 60.7},
                 {"countryiso3code": "BEN", "date": "2024", "value": None}]]


class FakeSession:
    def get(self, *args, **kwargs):
        return FakeResponse()


def test_fetch_indicator_parses_api_and_drops_nulls():
    rows, updated = fetch_indicator("SP.DYN.LE00.IN", ["BEN"], session=FakeSession())
    assert rows == [{"iso3": "BEN", "year": 2023, "indicator": "SP.DYN.LE00.IN", "value": 60.7}]
    assert updated == "2026-10-08"


@pytest.mark.skipif(not PANEL_FILE.exists(), reason="instantané de données absent")
def test_committed_snapshot_covers_16_countries():
    panel = pd.read_csv(PANEL_FILE)
    countries = panel[~panel["is_aggregate"]]
    assert set(countries["iso3"]) == set(COUNTRIES)
    assert not panel.duplicated(["iso3", "year"]).any()
    assert countries["life_expectancy"].between(30, 90).all()
