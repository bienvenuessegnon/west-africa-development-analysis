"""Pays, indicateurs et chemins du projet."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
FIGURES_DIR = ROOT / "reports" / "figures"
RAW_FILE = RAW_DIR / "wdi_west_africa_long.csv"
META_FILE = RAW_DIR / "metadata.json"
PANEL_FILE = PROCESSED_DIR / "panel.csv"

START_YEAR, END_YEAR = 1990, 2024

# Afrique de l'Ouest (sous-région des Nations unies, 16 pays) : code ISO3 -> nom français
COUNTRIES = {
    "BEN": "Bénin", "BFA": "Burkina Faso", "CPV": "Cabo Verde",
    "CIV": "Côte d'Ivoire", "GMB": "Gambie", "GHA": "Ghana", "GIN": "Guinée",
    "GNB": "Guinée-Bissau", "LBR": "Libéria", "MLI": "Mali", "MRT": "Mauritanie",
    "NER": "Niger", "NGA": "Nigeria", "SEN": "Sénégal", "SLE": "Sierra Leone",
    "TGO": "Togo",
}
# Agrégats de comparaison (non utilisés pour la modélisation)
AGGREGATES = {"SSF": "Afrique subsaharienne", "WLD": "Monde"}
# Pays mis en avant : le Bénin et ses voisins directs + grandes économies de la zone
FOCUS = ["BEN", "TGO", "NGA", "NER", "BFA", "GHA", "CIV", "SEN"]

# code WDI -> (nom de colonne, libellé français)
INDICATORS = {
    "SP.DYN.LE00.IN": ("life_expectancy", "Espérance de vie à la naissance (années)"),
    "NY.GDP.PCAP.KD": ("gdp_pc", "PIB par habitant (USD constants 2015)"),
    "NY.GDP.MKTP.KD.ZG": ("gdp_growth", "Croissance du PIB (% annuel)"),
    "SP.POP.TOTL": ("population", "Population totale"),
    "SP.URB.TOTL.IN.ZS": ("urban_pct", "Population urbaine (% du total)"),
    "SP.DYN.TFRT.IN": ("fertility", "Fécondité (naissances par femme)"),
    "SH.DYN.MORT": ("under5_mortality", "Mortalité des moins de 5 ans (pour 1 000)"),
    "EG.ELC.ACCS.ZS": ("electricity", "Accès à l'électricité (% de la population)"),
    "IT.NET.USER.ZS": ("internet", "Utilisateurs d'Internet (% de la population)"),
    "IT.CEL.SETS.P2": ("mobile", "Abonnements mobiles (pour 100 habitants)"),
    "SH.H2O.BASW.ZS": ("water", "Accès à l'eau potable de base (% de la population)"),
    "SE.PRM.CMPT.ZS": ("primary_completion", "Achèvement du primaire (% du groupe d'âge)"),
}
COLUMNS = {code: col for code, (col, _) in INDICATORS.items()}
LABELS = {col: label for col, label in INDICATORS.values()}
