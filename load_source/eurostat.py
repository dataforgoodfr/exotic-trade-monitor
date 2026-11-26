import json
from pathlib import Path
import shutil
import pandas as pd
import requests
from pyjstat import pyjstat
from datetime import datetime

# N dernières années + année en cours
def compute_years(nb_years):
    current = datetime.now().year
    return [str(y) for y in range(current - nb_years + 1, current + 1)]

# ---------------------------------------------------------
# PARAMÈTRES
# ---------------------------------------------------------
REPORTER = "FR"                      # France
PRODUCTS = ["01", "0301"]            # Chapitre 01 + position 0301
FLOWS = ["1", "2"]                   # 1 = Import, 2 = Export
FREQ = "A"                        # "A" = annuel, "M" = mensuel
#dernieres 5 annees
TIME = compute_years(5)
INDICATOR = "VALUE_IN_EUROS"         # ou "QUANTITY_IN_KG"

BASE_URL = "https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/data/DS-045409"
OUTPUT_DIR = Path("dbt_ETM/input_sources/eurostat/last_version")
ARCHIVE_DIR = Path("dbt_ETM/input_sources/eurostat/archive")


# ---------------------------------------------------------
# RÉCUPÉRATION DES DONNÉES
# ---------------------------------------------------------

def fetch_comext_data(product, flow, years, reporter, freq, indicator):
    params = {
        "format": "JSON",
        "lang": "FR",
        "freq": freq,
        "reporter": reporter,
        "time": years,
        "flow": flow,
        "product": product,
        "indicators": indicator,
    }
    response = requests.get(BASE_URL, params=params, timeout=60)
    response.raise_for_status()
    return response.json()


def parse_jsonstat(data, product, flow):
    """Parse une réponse JSON-stat en DataFrame tidy."""
    dataset = pyjstat.Dataset.read(json.dumps(data))
    df = dataset.write("dataframe")
    if not df.empty:
        df["product_query"] = product
        df["flow_query"] = flow
        # ajouter la date de derniere MAJ retournée par l'api
        df["api_updated"] = data.get("updated")
    return df


# ---------------------------------------------------------
# BOUCLE SUR LES CODES PRODUITS ET LES FLUX
# ---------------------------------------------------------
all_data = []
failures = []
# Utilisé pour ajouter la date d'extraction dans le jeu de données
extracted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

for product in PRODUCTS:
    for flow in FLOWS:
        print(f"Récupération : produit={product}, flow={flow}...")
        try:
            raw = fetch_comext_data(product, flow, TIME, REPORTER, FREQ, INDICATOR)
            df = parse_jsonstat(raw, product, flow)
            if not df.empty:
                all_data.append(df)
        except requests.exceptions.HTTPError as e:
            print(f"Erreur pour produit={product}, flow={flow} : {e}")
            failures.append((product, flow))

# ---------------------------------------------------------
# CONSOLIDATION ET EXPORT
# ---------------------------------------------------------

# Ne pas enregistrer CSV si erreur dans la réponse API 
if all_data and not failures:
    final_df = pd.concat(all_data, ignore_index=True)
    # Ajouter une colonne avec la date d'extraction dans le jeu de données (heure locale pas de l'API)
    final_df["extracted_at"] = extracted_at
    
    # Historise dans dbt_ETM\\input_sources\\eurostat\\archive
    if OUTPUT_DIR.exists():
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.move(str(OUTPUT_DIR), str(ARCHIVE_DIR / f"archive_{stamp}"))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / "commerce_france_NC01_0301.csv"

    final_df.to_csv(
        output_file,
        index=False,
        sep=",",
        encoding="utf-8-sig"   # utf-8-sig évite les soucis d'accents dans Excel/SQL
    )
    print("✅ Export terminé : commerce_france_NC01_0301.csv")
else:
    print(f"Export annulé. Échecs : {failures}" if failures else "Aucune donnée récupérée.")