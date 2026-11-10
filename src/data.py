"""Téléchargement (API Banque mondiale) et préparation du panel pays × année.

Usage : python -m src.data            # utilise l'instantané déjà présent
        python -m src.data --refresh  # retélécharge depuis l'API
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

import pandas as pd
import requests

from .config import (AGGREGATES, COLUMNS, COUNTRIES, END_YEAR, INDICATORS,
                     META_FILE, PANEL_FILE, RAW_DIR, RAW_FILE, START_YEAR)

API = "https://api.worldbank.org/v2/country/{countries}/indicator/{indicator}"


def fetch_indicator(code: str, countries: list[str], session=None, retries: int = 4) -> tuple[list[dict], str]:
    """Toutes les observations d'un indicateur (format long) + date de mise à jour."""
    session = session or requests.Session()
    url = API.format(countries=";".join(countries), indicator=code)
    params = {"format": "json", "date": f"{START_YEAR}:{END_YEAR}", "per_page": 20000}
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, params=params, timeout=120)
            response.raise_for_status()
            payload = response.json()
            break
        except (requests.RequestException, ValueError) as error:
            if attempt == retries:
                raise RuntimeError(f"Échec du téléchargement de {code} après {retries} essais") from error
            wait = 5 * attempt
            print(f"  {code} : essai {attempt} échoué ({type(error).__name__}), nouvel essai dans {wait} s")
            time.sleep(wait)
    if len(payload) < 2 or payload[1] is None:
        raise RuntimeError(f"Réponse vide pour {code} : {payload[:1]}")
    header, rows = payload
    records = [
        {"iso3": r["countryiso3code"], "year": int(r["date"]), "indicator": code, "value": r["value"]}
        for r in rows if r["value"] is not None
    ]
    return records, header.get("lastupdated", "")


def download() -> pd.DataFrame:
    """Télécharge les indicateurs et écrit data/raw/ (format long + métadonnées)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    codes = list(COUNTRIES) + list(AGGREGATES)
    records, updated = [], {}
    with requests.Session() as session:
        for code in INDICATORS:
            rows, last = fetch_indicator(code, codes, session)
            records += rows
            updated[code] = last
            print(f"{code:<20} {len(rows):>5} observations")
    raw = pd.DataFrame(records).sort_values(["iso3", "indicator", "year"])
    raw.to_csv(RAW_FILE, index=False)
    META_FILE.write_text(json.dumps({
        "source": "World Bank, World Development Indicators (API v2)",
        "api": "https://api.worldbank.org/v2/",
        "license": "CC BY 4.0 — https://datacatalog.worldbank.org/public-licenses",
        "downloaded_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "wdi_last_updated": updated,
        "years": [START_YEAR, END_YEAR],
        "countries": COUNTRIES, "aggregates": AGGREGATES,
    }, indent=2, ensure_ascii=False))
    return raw


def build_panel(raw: pd.DataFrame) -> pd.DataFrame:
    """Format long -> panel large (une ligne par pays et par année)."""
    expected = {"iso3", "year", "indicator", "value"}
    if missing := expected - set(raw.columns):
        raise ValueError(f"colonnes manquantes : {missing}")
    if raw.duplicated(["iso3", "year", "indicator"]).any():
        raise ValueError("doublons pays/année/indicateur")
    panel = (raw.pivot(index=["iso3", "year"], columns="indicator", values="value")
                .rename(columns=COLUMNS).reset_index())
    for col in COLUMNS.values():
        if col not in panel:
            panel[col] = float("nan")
    names = {**COUNTRIES, **AGGREGATES}
    panel.insert(1, "country", panel["iso3"].map(names))
    panel.insert(2, "is_aggregate", ~panel["iso3"].isin(COUNTRIES))
    panel.columns.name = None
    return panel[["iso3", "country", "is_aggregate", "year", *COLUMNS.values()]] \
        .sort_values(["iso3", "year"]).reset_index(drop=True)


def load_panel(countries_only: bool = False) -> pd.DataFrame:
    """Charge le panel préparé (le reconstruit depuis data/raw si besoin)."""
    if not PANEL_FILE.exists():
        prepare()
    panel = pd.read_csv(PANEL_FILE)
    return panel[~panel["is_aggregate"]].reset_index(drop=True) if countries_only else panel


def prepare(refresh: bool = False) -> pd.DataFrame:
    raw = download() if refresh or not RAW_FILE.exists() else pd.read_csv(RAW_FILE)
    panel = build_panel(raw)
    PANEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(PANEL_FILE, index=False)
    print(f"Panel : {len(panel)} lignes ({panel.iso3.nunique()} entités, "
          f"{panel.year.min()}–{panel.year.max()}) -> {PANEL_FILE}")
    return panel


def main() -> None:
    parser = argparse.ArgumentParser(description="Données WDI Afrique de l'Ouest")
    parser.add_argument("--refresh", action="store_true", help="retélécharger depuis l'API Banque mondiale")
    prepare(parser.parse_args().refresh)


if __name__ == "__main__":
    main()
