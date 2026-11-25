import os
import json
import requests
import gzip
import pandas as pd
import shutil
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------
# CHARGE L'ENVIRONMENT DE VARIABLE POUR LE TOKEN
# ---------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------
# PARAMÈTRES
# ---------------------------------------------------------
TOKEN = os.getenv("SPECIESPLUS_TOKEN")
LANG = "fr"
BASE_URL = "https://api.speciesplus.net/api/v1/downloads"
OUTPUT_DIR = Path("dbt_ETM/input_sources/speciesplus/last_version")
OUTPUT_DIR_TEMP = Path("dbt_ETM/input_sources/species+/temp")
GZ_FILE_NAME = f"cities_eu_{LANG}.ndjson.gz"
GZ_PATH = OUTPUT_DIR / GZ_FILE_NAME
TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# ---------------------------------------------------------
# RÉCUPÉRATION DES DONNÉES
# ---------------------------------------------------------
response = requests.get(
    BASE_URL,
    headers={"X-Authentication-Token": TOKEN},
    params={"lang": LANG}
)
response.raise_for_status()
data = response.json()

download_url = data[0]["download_url"]
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

with requests.get(download_url, stream=True) as resp:
    resp.raise_for_status()
    with open(GZ_PATH, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1 << 20):
            f.write(chunk)

print(f"Species taxonomy gz file saved at {GZ_PATH}")


# ---------------------------------------------------------
# METTRE LES DONNEES SOUS AU FORMAT CSV
# ---------------------------------------------------------
def build_taxon_row(taxon):
    higher_taxa = taxon.get("higher_taxa") or {}
    common_names = taxon.get("common_names") or []
    cites_listings = taxon.get("cites_listings") or []
    eu_listings = taxon.get("eu_listings") or []

    return {
        "id": taxon.get("id"),
        "full_name": taxon.get("full_name"),
        "author_year": taxon.get("author_year"),
        "rank": taxon.get("rank"),
        "name_status": taxon.get("name_status"),
        "active": taxon.get("active"),
        "updated_at": taxon.get("updated_at"),
        "kingdom": higher_taxa.get("kingdom"),
        "phylum": higher_taxa.get("phylum"),
        "class": higher_taxa.get("class"),
        "order": higher_taxa.get("order"),
        "family": higher_taxa.get("family"),
        "common_names": " | ".join(
            f"{item.get('name')} ({item.get('language')})" for item in common_names
        ),
        "cites_listing": taxon.get("cites_listing"),
        "cites_appendices": " | ".join(
            str(item.get("appendix")) for item in cites_listings if item.get("appendix")
        ),
        "eu_listing": taxon.get("eu_listing"),
        "eu_annexes": " | ".join(
            str(item.get("annex")) for item in eu_listings if item.get("annex")
        ),
    }


rows = []
with gzip.open(GZ_PATH, "rt", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            rows.append(build_taxon_row(json.loads(line)))

taxon_concepts = pd.DataFrame(rows)

# ---------------------------------------------------------
# EXPORTER LA DONNEES
# ---------------------------------------------------------

if OUTPUT_DIR.exists():
    shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

taxon_concepts.to_csv(
    OUTPUT_DIR / f"taxon_concepts_{TIMESTAMP}.csv",
    index=False,
    encoding="utf-8-sig"
)

print(f"✅ Export terminé : {OUTPUT_DIR} ({len(taxon_concepts)} lignes)")
