import numpy as np
import pytest

from src.model import (TARGET, TrendPlusRidge, evaluate_country_holdout, evaluate_temporal,
                       make_dataset, persistence_baseline, temporal_split, trend_baseline)


def test_temporal_split_has_no_overlap(synthetic_panel):
    df = make_dataset(synthetic_panel)
    train, test = temporal_split(df, train_end=2016)
    assert train["year"].max() == 2016 and test["year"].min() == 2017
    assert len(train) + len(test) == len(df)


def test_baselines_on_linear_data(synthetic_panel):
    train, test = temporal_split(make_dataset(synthetic_panel), train_end=2016)
    assert np.allclose(trend_baseline(train, test), test[TARGET])          # tendance exacte
    gap = test[TARGET] - persistence_baseline(train, test)
    assert np.allclose(gap, 0.4 * (test["year"] - 2016))                   # retard attendu


def test_hybrid_model_recovers_linear_trend(synthetic_panel):
    train, test = temporal_split(make_dataset(synthetic_panel), train_end=2016)
    pred = TrendPlusRidge().fit(train).predict(test)
    assert np.abs(pred - test[TARGET]).max() < 0.5


def test_evaluations_return_all_models(synthetic_panel):
    df = make_dataset(synthetic_panel)
    temporal, detail = evaluate_temporal(df)
    assert len(temporal) == 5 and len(detail) == (df.year > 2016).sum()
    holdout, _ = evaluate_country_holdout(df)
    assert {"MAE", "RMSE", "R2"} <= set(holdout.columns) and len(holdout) == 3
    assert (temporal["MAE"] >= 0).all()
