# Données

| Fichier | Contenu |
| --- | --- |
| `raw/wdi_west_africa_long.csv` | observations brutes au format long (`iso3, year, indicator, value`), telles que renvoyées par l'API |
| `raw/metadata.json` | source, licence, date de téléchargement, date de mise à jour WDI de chaque indicateur |
| `processed/panel.csv` | panel pays × année (une colonne par indicateur), construit par `src/data.py` |

- **Source** : Banque mondiale, *World Development Indicators* (WDI), API v2 —
  <https://api.worldbank.org/v2/> · catalogue : <https://datacatalog.worldbank.org/search/dataset/0037712>
- **Équivalent Kaggle** : [World Development Indicators](https://www.kaggle.com/datasets/theworldbank/world-development-indicators)
  (compte officiel *theworldbank*, alimenté par la même API).
- **Licence des données** : [CC BY 4.0](https://datacatalog.worldbank.org/public-licenses), avec les conditions
  complémentaires de la Banque mondiale. Attribution : *The World Bank: World Development Indicators*.
- **Modifications** : sélection de 12 indicateurs, 16 pays + 2 agrégats, années 1990–2024 ;
  passage du format long au format large ; noms de pays traduits en français.

L'instantané (≈ 350 Ko) est versionné pour la reproductibilité. Pour le rafraîchir :

```bash
python -m src.data --refresh
```

Les valeurs WDI sont régulièrement révisées : un nouveau téléchargement peut modifier les chiffres.
