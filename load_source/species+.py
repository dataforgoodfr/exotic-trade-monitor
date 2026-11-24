import os
import shutil
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://api.speciesplus.net/api/v1/taxon_concepts"
OUTPUT_DIR = Path("dbt_ETM/input_sources/speciesplus/last_version")
OUTPUT_FILE = OUTPUT_DIR / "speciesplus_taxon_concepts.csv"

load_dotenv()

TOKEN = os.getenv("SPECIESPLUS_TOKEN")
TAXON_NAME = os.getenv("SPECIESPLUS_TAXON_NAME", "").strip()
PER_PAGE = int(os.getenv("SPECIESPLUS_PER_PAGE", "500"))


def fetch_all_taxons():
    if not TOKEN:
        raise RuntimeError(
            "Token Species+ manquant. Définissez SPECIESPLUS_TOKEN dans votre .env ou dans les variables d'environnement."
        )

    all_records = []
    page = 1

    retries = Retry(
        total=8,
        backoff_factor=2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retries))

    while True:
        params = {"page": page, "per_page": PER_PAGE}
        if TAXON_NAME:
            params["name"] = TAXON_NAME

        response = session.get(
            BASE_URL,
            headers={"X-Authentication-Token": TOKEN},
            params=params,
            timeout=60,
        )
        response.raise_for_status()

        payload = response.json()
        records = payload.get("taxon_concepts", [])
        all_records.extend(records)

        pagination = payload.get("pagination") or {}
        total_entries = pagination.get("total_entries")
        if total_entries is not None:
            print(
                f"Species+ : page {page}, {len(all_records)}/{total_entries} taxons récupérés"
            )
            if len(all_records) >= int(total_entries):
                break
        elif not records:
            break

        if not records:
            break

        page += 1
        time.sleep(0.25)

    if not all_records:
        filter_description = f" pour {TAXON_NAME!r}" if TAXON_NAME else ""
        raise RuntimeError(f"Aucun taxon récupéré{filter_description}.")

    return all_records


def flatten_taxon(taxon):
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


try:
    taxons = fetch_all_taxons()
    df = pd.DataFrame([flatten_taxon(taxon) for taxon in taxons])

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"✅ Export terminé : {OUTPUT_FILE} ({len(df)} lignes)")
except (requests.RequestException, RuntimeError) as exc:
    raise SystemExit(f"Erreur Species+ : {exc}") from exc
