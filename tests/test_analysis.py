import pytest

from src.analysis import cagr, change, latest, rank_of


def test_cagr():
    assert cagr(100, 121, 2) == pytest.approx(10.0)
    with pytest.raises(ValueError):
        cagr(0, 10, 2)


def test_change_and_latest(synthetic_panel):
    ch = change(synthetic_panel, "life_expectancy", 2000, 2010)
    assert ch["change"].tolist() == pytest.approx([4.0] * 4)
    last = latest(synthetic_panel, "life_expectancy")
    assert set(last["year"]) == {2024}
    assert last.iloc[0]["iso3"] == "DDD"


def test_rank_of(synthetic_panel):
    snap = synthetic_panel[synthetic_panel.year == 2024]
    assert rank_of(snap, "life_expectancy", "DDD") == 1
    assert rank_of(snap, "life_expectancy", "AAA") == 4
