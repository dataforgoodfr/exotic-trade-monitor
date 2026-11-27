"""
Extraction asynchrone brute des données IUCN Red List (API v4) pour les taxons animaux CITES.

Notes techniques :
- Périmètre : ~6 500 taxons uniques du règne Animalia (dédoublonnés depuis ~29M lignes CITES).
  Extraction brute sans filtre métier pour traitement dans dbt.
- Concurrence & Rate Limits : Parallélisation bornée (MAX_CONCURRENCY = 3) couplée à un
  lissage de débit (MIN_INTERVAL = 0.65s) et une pause globale en cas de HTTP 429.
"""

import asyncio
import json
import os
from pathlib import Path
import shutil
import time

import httpx
import pandas as pd

# ---------------------------------------------------------
# PARAMÈTRES
# ---------------------------------------------------------
API_TOKEN = os.getenv("IUCN_API_TOKEN")
BASE_URL = "https://api.iucnredlist.org/api/v4"

CITES_DIR = Path("dbt_ETM/input_sources/CITES/last_version")
OUTPUT_DIR = Path("dbt_ETM/input_sources/iucn/last_version")
OUTPUT_FILE = OUTPUT_DIR / "iucn_species.csv"

# None par défaut pour la prod (IUCN_MAX_SPECIES=100 pour les tests)
_env_max = os.getenv("IUCN_MAX_SPECIES")
MAX_SPECIES: int | None = int(_env_max) if _env_max else None

MAX_CONCURRENCY = 3     # 3 requêtes simultanées max
MIN_INTERVAL = 0.85     # ~70 req/min max (en-dessous, erreur 429)
BATCH_SIZE = 50         # Taille des lots pour la sauvegarde incrémentale

_rate_lock = asyncio.Lock()
_last_request_ts = 0.0
_cooldown_until = 0.0

# ---------------------------------------------------------
# LECTURE BRUTE DES TAXONS ANIMAUX CITES
# ---------------------------------------------------------
def get_cites_animals(cites_dir: Path) -> pd.DataFrame:
    """Extrait tous les taxons animaux uniques CITES (Class renseignée) sans nettoyage métier."""
    csv_files = list(cites_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"Aucun fichier CSV CITES trouvé dans {cites_dir}")

    chunks = [
        pd.read_csv(f, usecols=["Taxon", "Class"], dtype=str)
        .dropna(subset=["Taxon", "Class"])
        .drop_duplicates(subset=["Taxon"])
        for f in csv_files
    ]
    species_df = (
        pd.concat(chunks, ignore_index=True)
        .drop_duplicates(subset=["Taxon"])
        .reset_index(drop=True)
    )

    parts = species_df["Taxon"].str.split()
    species_df["genus_name"] = parts.str[0]
    species_df["species_name"] = parts.str[1].fillna("")

    return species_df


# ---------------------------------------------------------
# APPELS API IUCN V4 ASYNCHRONES
# ---------------------------------------------------------
async def get_with_retry(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    url: str,
    params: dict | None = None,
) -> dict | None:
    """Exécute un GET asynchrone avec lissage du débit, cooldown 429 et retry réseau/5xx."""
    global _last_request_ts, _cooldown_until
    max_attempts = 4

    for attempt in range(max_attempts):
        async with semaphore:
            async with _rate_lock:
                now = time.perf_counter()
                if _cooldown_until > now:
                    await asyncio.sleep(_cooldown_until - now)

                now = time.perf_counter()
                wait_slot = MIN_INTERVAL - (now - _last_request_ts)
                if wait_slot > 0:
                    await asyncio.sleep(wait_slot)
                _last_request_ts = time.perf_counter()

            try:
                response = await client.get(url, params=params)
            except httpx.RequestError:
                if attempt == max_attempts - 1:
                    raise
                await asyncio.sleep(2**attempt)
                continue

            if response.status_code == 429:
                if attempt == max_attempts - 1:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After")
                wait = int(retry_after) if retry_after and retry_after.isdigit() else 60
                target = time.perf_counter() + wait
                if target > _cooldown_until:
                    _cooldown_until = target
                    print(f"⏳ Rate limit atteint (429), pause partagée de {wait}s...")
                continue

        if response.status_code == 200:
            return response.json()
        if response.status_code == 404:
            return None
        if response.status_code >= 500 and attempt < max_attempts - 1:
            await asyncio.sleep(2**attempt)
            continue
        response.raise_for_status()

    return None


async def fetch_taxon_raw_iucn(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    row: dict,
) -> list[dict]:
    """Récupère les données brutes IUCN d'un taxon (tous scopes 'latest')."""
    cites_taxon = row["Taxon"]
    base_info = {
        "cites_taxon": cites_taxon,
        "cites_class": row["Class"],
    }
    not_found_row = [
        {
            **base_info,
            "iucn_found": False,
            "taxon_sis_id": None,
            "iucn_scientific_name": None,
            "assessment_id": None,
            "assessment_year": None,
            "assessment_latest": None,
            "assessment_scopes": None,
            "categorie_uicn": None,
            "tendance_uicn": None,
        }
    ]

    genus, species = row["genus_name"], row["species_name"]
    if not genus or not species:
        return not_found_row

    try:
        taxon_data = await get_with_retry(
            client,
            semaphore,
            f"{BASE_URL}/taxa/scientific_name",
            params={"genus_name": genus, "species_name": species},
        )
        if not taxon_data:
            return not_found_row

        taxon_info = taxon_data.get("taxon") or {}
        assessments = taxon_data.get("assessments") or []
        latest_assessments = [a for a in assessments if a.get("latest") is True] or assessments[:1]

        rows = []
        for assessment in latest_assessments:
            assessment_id = assessment.get("assessment_id")
            categorie_uicn = assessment.get("red_list_category_code")
            tendance_uicn = None
            scopes = [s.get("code") for s in (assessment.get("scopes") or [])]

            if assessment_id:
                detail = await get_with_retry(
                    client, semaphore, f"{BASE_URL}/assessment/{assessment_id}"
                )
                if detail:
                    cat_obj = detail.get("red_list_category")
                    if isinstance(cat_obj, dict):
                        categorie_uicn = cat_obj.get("code") or categorie_uicn
                    trend_obj = detail.get("population_trend")
                    if isinstance(trend_obj, dict):
                        tendance_uicn = (trend_obj.get("description") or {}).get("en")

            rows.append(
                {
                    **base_info,
                    "iucn_found": True,
                    "taxon_sis_id": taxon_info.get("sis_id"),
                    "iucn_scientific_name": taxon_info.get("scientific_name"),
                    "assessment_id": assessment_id,
                    "assessment_year": assessment.get("year_published"),
                    "assessment_latest": assessment.get("latest"),
                    "assessment_scopes": json.dumps(scopes),
                    "categorie_uicn": categorie_uicn,
                    "tendance_uicn": tendance_uicn,
                }
            )
        return rows or not_found_row

    except httpx.HTTPError as e:
        print(f"⚠️ Erreur réseau sur {cites_taxon} (sera retenté au prochain lancement) : {e}")
        return []


# ---------------------------------------------------------
# SAUVEGARDE ET ORCHESTRATION
# ---------------------------------------------------------
def save_dataframe(df: pd.DataFrame, target_file: Path) -> None:
    """Écrit le CSV de manière atomique via un fichier temporaire."""
    target_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file = target_file.with_suffix(".tmp.csv")
    df.to_csv(temp_file, index=False, sep=",", encoding="utf-8-sig")
    shutil.move(temp_file, target_file)


async def run_extraction() -> None:
    if not API_TOKEN:
        raise ValueError("Variable IUCN_API_TOKEN manquante. Utilise --env-file .env")

    print("Lecture des taxons animaux CITES...")
    species_df = get_cites_animals(CITES_DIR)

    existing_results = []
    already_processed = set()
    if OUTPUT_FILE.exists() and OUTPUT_FILE.stat().st_size > 0:
        existing_df = pd.read_csv(OUTPUT_FILE)
        existing_results = existing_df.to_dict(orient="records")
        already_processed = set(existing_df["cites_taxon"].dropna().unique())
        print(f"♻️ Reprise détectée : {len(already_processed)} taxons déjà traités ignorés.")

    pending_df = species_df[~species_df["Taxon"].isin(already_processed)].reset_index(drop=True)
    if MAX_SPECIES is not None:
        pending_df = pending_df.head(MAX_SPECIES)

    total = len(pending_df)
    print(f"📋 {total} nouveaux taxons à interroger (concurrence max : {MAX_CONCURRENCY}).")
    if total == 0:
        print("✅ Rien à mettre à jour.")
        return

    results = list(existing_results)
    pending_records = pending_df.to_dict(orient="records")
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    headers = {"Authorization": f"Bearer {API_TOKEN}", "Accept": "application/json"}

    start_time = time.perf_counter()
    processed_count = 0

    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        for i in range(0, total, BATCH_SIZE):
            batch = pending_records[i : i + BATCH_SIZE]
            batch_outputs = await asyncio.gather(
                *(fetch_taxon_raw_iucn(client, semaphore, row) for row in batch)
            )
            for rows in batch_outputs:
                results.extend(rows)

            processed_count += len(batch)
            elapsed = time.perf_counter() - start_time
            rate = processed_count / elapsed if elapsed > 0 else 0

            save_dataframe(pd.DataFrame(results), OUTPUT_FILE)
            print(
                f"💾 {processed_count}/{total} traités "
                f"({elapsed:.1f}s écoulées, {rate:.2f} taxons/s)."
            )

    total_time = time.perf_counter() - start_time
    file_size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(
        f"✅ Extraction terminée en {total_time:.1f}s : {OUTPUT_FILE} "
        f"({len(results)} lignes, {file_size_kb:.1f} Ko)."
    )


if __name__ == "__main__":
    asyncio.run(run_extraction())