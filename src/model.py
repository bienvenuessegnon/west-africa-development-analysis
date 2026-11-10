"""Modélisation : prédire l'espérance de vie à partir d'indicateurs de développement.

Deux protocoles d'évaluation honnêtes :
1. **Temporel** : apprentissage 2000–2016, test 2017–2024 (les 16 pays) ;
   le modèle est choisi sur une validation 2013–2016 (apprentissage 2000–2012).
2. **Pays inconnu** : validation croisée « leave-one-country-out » (16 plis).

Usage : python -m src.model   (écrit reports/metrics_*.csv|md et des figures)
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .config import FIGURES_DIR, LABELS, ROOT
from .data import load_panel

TARGET = "life_expectancy"
FEATURES = ["log_gdp_pc", "electricity", "water", "fertility", "urban_pct", "internet"]
FEATURE_LABELS = {
    "log_gdp_pc": "log(PIB par habitant)", "electricity": "Accès à l'électricité",
    "water": "Eau potable de base", "fertility": "Fécondité",
    "urban_pct": "Population urbaine", "internet": "Internet",
}
TRAIN_END, TEST_START, TEST_END = 2016, 2017, 2024
SEED = 42
REPORTS = ROOT / "reports"


def make_dataset(panel: pd.DataFrame) -> pd.DataFrame:
    """Lignes pays-année complètes (pays uniquement, à partir de 2000)."""
    df = panel[~panel["is_aggregate"] & (panel["year"] >= 2000)].copy()
    df["log_gdp_pc"] = np.log(df["gdp_pc"])
    return df.dropna(subset=FEATURES + [TARGET]).reset_index(drop=True)


def temporal_split(df: pd.DataFrame, train_end: int = TRAIN_END, test_end: int = TEST_END):
    train = df[df["year"] <= train_end]
    test = df[(df["year"] > train_end) & (df["year"] <= test_end)]
    return train.reset_index(drop=True), test.reset_index(drop=True)


def models() -> dict:
    return {
        "Régression ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
        "Forêt aléatoire": RandomForestRegressor(n_estimators=300, min_samples_leaf=3,
                                                 random_state=SEED, n_jobs=-1),
    }


def metrics(y_true, y_pred) -> dict:
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
    }


def persistence_baseline(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """Dernière valeur observée de chaque pays dans l'apprentissage."""
    last = train.sort_values("year").groupby("iso3")[TARGET].last()
    return test["iso3"].map(last).to_numpy()


def trend_baseline(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """Tendance linéaire propre à chaque pays, prolongée sur la période de test."""
    preds = np.empty(len(test))
    for iso3, rows in test.groupby("iso3"):
        hist = train[train["iso3"] == iso3]
        fit = LinearRegression().fit(hist[["year"]], hist[TARGET])
        preds[rows.index] = fit.predict(rows[["year"]])
    return preds


class TrendPlusRidge:
    """Modèle hybride : tendance linéaire propre à chaque pays + correction ridge.

    1. Pour chaque pays, une tendance linéaire de l'espérance de vie est ajustée
       sur les années d'apprentissage.
    2. Une régression ridge apprend, à partir des indicateurs de l'année, l'écart
       (résidu) entre l'espérance de vie observée et cette tendance.
    Prédiction = tendance prolongée + résidu prédit. Les indicateurs de l'année
    à prédire sont supposés connus (exercice d'estimation, pas de prévision pure).
    """

    def __init__(self, alpha: float = 10.0):
        self.alpha = alpha

    def fit(self, train: pd.DataFrame) -> "TrendPlusRidge":
        self.trends_ = {iso3: LinearRegression().fit(g[["year"]], g[TARGET])
                        for iso3, g in train.groupby("iso3")}
        residual = train[TARGET] - self._trend(train)
        self.ridge_ = make_pipeline(StandardScaler(), Ridge(alpha=self.alpha))
        self.ridge_.fit(train[FEATURES], residual)
        return self

    def _trend(self, df: pd.DataFrame) -> np.ndarray:
        out = np.empty(len(df))
        for n, (iso3, year) in enumerate(zip(df["iso3"], df["year"])):
            out[n] = self.trends_[iso3].predict(pd.DataFrame({"year": [year]}))[0]
        return out

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return self._trend(df) + self.ridge_.predict(df[FEATURES])


HYBRID = "Tendance par pays + correction ridge"


def temporal_predictions(train: pd.DataFrame, test: pd.DataFrame) -> dict:
    preds = {
        "Référence : dernière valeur connue": persistence_baseline(train, test),
        "Référence : tendance par pays": trend_baseline(train, test),
    }
    for name, model in models().items():
        preds[name] = model.fit(train[FEATURES], train[TARGET]).predict(test[FEATURES])
    preds[HYBRID] = TrendPlusRidge().fit(train).predict(test)
    return preds


def evaluate_temporal(df: pd.DataFrame, train_end: int = TRAIN_END,
                      test_end: int = TEST_END) -> tuple[pd.DataFrame, pd.DataFrame]:
    train, test = temporal_split(df, train_end, test_end)
    preds = temporal_predictions(train, test)
    table = pd.DataFrame([{"modele": k, **metrics(test[TARGET], v)} for k, v in preds.items()])
    detail = test[["iso3", "country", "year", TARGET]].assign(**{k: v for k, v in preds.items()})
    return table, detail


def evaluate_validation(df: pd.DataFrame) -> pd.DataFrame:
    """Sélection du modèle sans toucher au test : apprentissage 2000–2012, validation 2013–2016."""
    table, _ = evaluate_temporal(df[df["year"] <= TRAIN_END], train_end=2012, test_end=TRAIN_END)
    return table


def evaluate_country_holdout(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Chaque pays est prédit par un modèle qui ne l'a jamais vu."""
    preds = {"Référence : moyenne des autres pays (même année)": np.empty(len(df))}
    for name in models():
        preds[name] = np.empty(len(df))
    for train_idx, test_idx in LeaveOneGroupOut().split(df, groups=df["iso3"]):
        train, test = df.iloc[train_idx], df.iloc[test_idx]
        year_mean = train.groupby("year")[TARGET].mean()
        preds["Référence : moyenne des autres pays (même année)"][test_idx] = test["year"].map(year_mean)
        for name, model in models().items():
            preds[name][test_idx] = model.fit(train[FEATURES], train[TARGET]).predict(test[FEATURES])
    table = pd.DataFrame([{"modele": k, **metrics(df[TARGET], v)} for k, v in preds.items()])
    detail = df[["iso3", "country", "year", TARGET]].assign(**preds)
    return table, detail


def importances(df: pd.DataFrame, n_repeats: int = 30) -> pd.DataFrame:
    """Diagnostic du modèle hybride (appris sur 2000–2016, évalué sur 2017–2024).

    - coefficient standardisé de la correction ridge (effet sur l'écart à la tendance) ;
    - importance par permutation : hausse de la MAE de test quand on mélange la variable.
    """
    train, test = temporal_split(df)
    model = TrendPlusRidge().fit(train)
    base = mean_absolute_error(test[TARGET], model.predict(test))
    rng = np.random.default_rng(SEED)
    rows = []
    for feature, coef in zip(FEATURES, model.ridge_[-1].coef_):
        losses = []
        for _ in range(n_repeats):
            shuffled = test.copy()
            shuffled[feature] = rng.permutation(shuffled[feature].to_numpy())
            losses.append(mean_absolute_error(test[TARGET], model.predict(shuffled)) - base)
        rows.append({"variable": FEATURE_LABELS[feature], "coef_correction_standardise": float(coef),
                     "importance_permutation_mae": float(np.mean(losses))})
    return pd.DataFrame(rows).sort_values("importance_permutation_mae", ascending=False).reset_index(drop=True)


def _md(table: pd.DataFrame) -> str:
    head = "| " + " | ".join(table.columns) + " |\n| " + " | ".join("---" for _ in table.columns) + " |\n"
    body = "".join("| " + " | ".join(f"{v:.3f}" if isinstance(v, float) else str(v) for v in row) + " |\n"
                   for row in table.itertuples(index=False))
    return head + body


def run() -> dict:
    import matplotlib
    matplotlib.use("Agg")
    from .plots import plot_holdout, plot_importance, plot_temporal_benin

    df = make_dataset(load_panel())
    REPORTS.mkdir(exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    validation = evaluate_validation(df)
    temporal, temporal_detail = evaluate_temporal(df)
    holdout, holdout_detail = evaluate_country_holdout(df)
    imp = importances(df)
    validation.to_csv(REPORTS / "metrics_validation.csv", index=False, float_format="%.4f")
    temporal.to_csv(REPORTS / "metrics_temporal.csv", index=False, float_format="%.4f")
    holdout.to_csv(REPORTS / "metrics_country_holdout.csv", index=False, float_format="%.4f")
    imp.to_csv(REPORTS / "feature_importance.csv", index=False, float_format="%.4f")
    train, test = temporal_split(df)
    (REPORTS / "metrics.md").write_text(
        "# Résultats de modélisation — cible : espérance de vie à la naissance (années)\n\n"
        f"Variables : {', '.join(FEATURE_LABELS[f] for f in FEATURES)}.\n"
        f"{len(df)} observations pays-année complètes ({df.iso3.nunique()} pays, "
        f"{df.year.min()}–{df.year.max()}).\n\n"
        "## 0. Sélection sur validation (apprentissage 2000–2012, validation 2013–2016)\n\n"
        + _md(validation) + "\n"
        f"## 1. Split temporel : apprentissage {df.year.min()}–{TRAIN_END} ({len(train)} lignes), "
        f"test {TEST_START}–{TEST_END} ({len(test)} lignes)\n\n" + _md(temporal) +
        "\n## 2. Pays jamais vu : leave-one-country-out (16 plis)\n\n" + _md(holdout) +
        "\n## Diagnostic du modèle hybride (appris sur 2000–2016, permutation sur le test 2017–2024)\n\n" + _md(imp) +
        "\nMAE/RMSE en années d'espérance de vie (plus bas = mieux). Corrélation ≠ causalité.\n")
    plot_temporal_benin(temporal_detail, FIGURES_DIR / "06_modele_benin_temporel.png")
    plot_holdout(holdout, temporal, FIGURES_DIR / "07_modele_erreurs.png")
    plot_importance(imp, FIGURES_DIR / "08_importance_variables.png")
    ben = temporal_detail[temporal_detail.iso3 == "BEN"]
    benin = {name: metrics(ben[TARGET], ben[name])["MAE"] for name in temporal.modele}
    pd.Series(benin, name="MAE_benin").to_csv(REPORTS / "metrics_temporal_benin.csv", float_format="%.4f")
    summary = {"benin_temporal_mae": benin, "n_rows": len(df), "n_train": len(train), "n_test": len(test),
               "validation": validation.to_dict("records"), "temporal": temporal.to_dict("records"), "country_holdout": holdout.to_dict("records"),
               "importance": imp.to_dict("records")}
    (REPORTS / "model_results.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(validation.round(3).to_string(index=False))
    print(temporal.round(3).to_string(index=False))
    print(holdout.round(3).to_string(index=False))
    print(imp.round(3).to_string(index=False))
    return summary


if __name__ == "__main__":
    run()
