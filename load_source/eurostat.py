import json
from pathlib import Path
import shutil

import pandas as pd
import requests
from pyjstat import pyjstat

# ---------------------------------------------------------
# PARAMÈTRES
# ---------------------------------------------------------
REPORTER = "FR"                      # France
PRODUCTS = ["01", "0301"]            # Chapitre 01 + position 0301
FLOWS = ["1", "2"]                   # 1 = Import, 2 = Export
FREQ = "A"                           # "A" = annuel, "M" = mensuel
#TIME = "2023"                        # Année (ou "2023-01" si FREQ="M")
TIME = ["2021", "2022", "2023", "2024", "2025"]
INDICATOR = "VALUE_IN_EUROS"         # ou "QUANTITY_IN_KG"

BASE_URL = "https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/data/DS-045409"
OUTPUT_DIR = Path("dbt_ETM/input_sources/eurostat/last_version")


# ---------------------------------------------------------
# RÉCUPÉRATION DES DONNÉES
# ---------------------------------------------------------
def fetch_comext_data(product, flow):
    params = {
        "format": "JSON",
        "lang": "FR",
        "freq": FREQ,
        "reporter": REPORTER,
        "time": TIME,
        "flow": flow,
        "product": product,
        "indicators": INDICATOR,
    }
    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()
    return response.json()


def parse_jsonstat(data, product, flow):
    """Parse une réponse JSON-stat en DataFrame tidy."""
    dataset = pyjstat.Dataset.read(json.dumps(data))
    df = dataset.write("dataframe")
    if not df.empty:
        df["product_query"] = product
        df["flow_query"] = flow
    return df


# ---------------------------------------------------------
# BOUCLE SUR LES CODES PRODUITS ET LES FLUX
# ---------------------------------------------------------
all_data = []

for product in PRODUCTS:
    for flow in FLOWS:
        print(f"Récupération : produit={product}, flow={flow}...")
        try:
            raw = fetch_comext_data(product, flow)
            df = parse_jsonstat(raw, product, flow)
            if not df.empty:
                all_data.append(df)
        except requests.exceptions.HTTPError as e:
            print(f"Erreur pour produit={product}, flow={flow} : {e}")

# ---------------------------------------------------------
# CONSOLIDATION ET EXPORT
# ---------------------------------------------------------
if all_data:
    final_df = pd.concat(all_data, ignore_index=True)

    # Supprime le précédent téléchargement 
    # TO DO : historiser dans dbt_ETM\\input_sources\\eurostat\\archive
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
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
    print("Aucune donnée récupérée.")
