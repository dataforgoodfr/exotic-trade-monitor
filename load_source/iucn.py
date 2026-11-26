import json
import os
from pathlib import Path
import shutil
import time

import pandas as pd
import requests

# ---------------------------------------------------------
# PARAMÈTRES
# ---------------------------------------------------------
API_TOKEN = os.getenv("IUCN_API_TOKEN")
BASE_URL = "https://api.iucnredlist.org/api/v4"

CITES_DIR = Path("dbt_ETM/input_sources/CITES/last_version")
OUTPUT_DIR = Path("dbt_ETM/input_sources/iucn/last_version")
OUTPUT_FILE = OUTPUT_DIR / "iucn_species.csv"

MAX_SPECIES: int | None = 100  # Passer à None une fois le test validé
REQUEST_DELAY = 1.0
SAVE_EVERY = 50


# ---------------------------------------------------------
# LECTURE BRUTE DES TAXONS ANIMAUX CITES
# ---------------------------------------------------------
def get_cites_animals(cites_dir: Path) -> pd.DataFrame:
    """Extrait tous les taxons animaux uniques CITES (Class renseignée) sans nettoyage métier."""
    csv_files = list(cites_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"Aucun fichier CSV CITES trouvé dans {cites_dir}")

    df = pd.concat(
        [pd.read_csv(f, usecols=["Taxon", "Class"], low_memory=False) for f in csv_files],
        ignore_index=True,
    )

    # Dans CITES, les animaux ont une Class renseignée (les plantes ont Class vide/NaN)
    df = df.dropna(subset=["Taxon", "Class"]).copy()

    # Dédoublonnage technique sur le nom exact CITES
    species_df = df[["Taxon", "Class"]].drop_duplicates(subset=["Taxon"]).reset_index(drop=True)

    # Découpage en genus / species (2 premiers mots si disponibles)
    parts = species_df["Taxon"].str.strip().str.split()
    species_df["genus_name"] = parts.str[0]
    species_df["species_name"] = parts.str[1].fillna("")

    return species_df


# ---------------------------------------------------------
# APPELS API IUCN V4 (EXTRACTION BRUTE)
# ---------------------------------------------------------
def create_session() -> requests.Session:
    if not API_TOKEN:
        raise ValueError("Variable IUCN_API_TOKEN manquante. Utilise --env-file .env")
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {API_TOKEN}",
            "Accept": "application/json",
        }
    )
    return session


def get_with_retry(session: requests.Session, url: str, params: dict | None = None) -> dict | None:
    """Exécute un GET avec gestion des 404 et pause en cas de rate limit (429)."""
    for attempt in range(4):
        response = session.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json()
        if response.status_code == 404:
            return None
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            wait = int(retry_after) if retry_after and retry_after.isdigit() else 10 * (attempt + 1)
            print(f"⏳ Rate limit atteint (429), pause de {wait}s...")
            time.sleep(wait)
            continue
        response.raise_for_status()
    return None


def fetch_taxon_raw_iucn(session: requests.Session, genus: str, species: str) -> list[dict]:
    """Récupère les données brutes IUCN pour toutes les dernières évaluations (tous scopes)."""
    if not genus or not species:
        return []

    taxon_data = get_with_retry(
        session,
        f"{BASE_URL}/taxa/scientific_name",
        params={"genus_name": genus, "species_name": species},
    )
    if not taxon_data:
        return []

    taxon_info = taxon_data.get("taxon") or {}
    assessments = taxon_data.get("assessments") or []

    # Conserve toutes les évaluations marquées 'latest' (Global, Europe, etc.) pour filtrage dans dbt
    latest_assessments = [a for a in assessments if a.get("latest") is True] or assessments[:1]

    rows = []
    for assessment in latest_assessments:
        assessment_id = assessment.get("assessment_id")
        categorie_uicn = assessment.get("red_list_category_code")
        tendance_uicn = None
        scopes = [s.get("code") for s in (assessment.get("scopes") or [])]

        if assessment_id:
            time.sleep(REQUEST_DELAY)
            detail = get_with_retry(session, f"{BASE_URL}/assessment/{assessment_id}")
            if detail:
                cat_obj = detail.get("red_list_category")
                if isinstance(cat_obj, dict):
                    categorie_uicn = cat_obj.get("code") or categorie_uicn
                trend_obj = detail.get("population_trend")
                if isinstance(trend_obj, dict):
                    tendance_uicn = (trend_obj.get("description") or {}).get("en")

        rows.append(
            {
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

    return rows


# ---------------------------------------------------------
# SAUVEGARDE ET EXÉCUTION
# ---------------------------------------------------------
def save_dataframe(df: pd.DataFrame, target_file: Path) -> None:
    """Écrit le CSV de manière atomique via un fichier temporaire."""
    target_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file = target_file.with_suffix(".tmp.csv")
    df.to_csv(temp_file, index=False, sep=",", encoding="utf-8-sig")
    shutil.move(temp_file, target_file)


def main() -> None:
    print("Lecture des taxons animaux CITES...")
    species_df = get_cites_animals(CITES_DIR)
    print(f"Classes détectées : {sorted(species_df['Class'].unique().tolist())}")

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
    print(f"📋 {total} nouveaux taxons à interroger sur l'API IUCN.")
    if total == 0:
        print("✅ Rien à mettre à jour.")
        return

    session = create_session()
    results = list(existing_results)

    for idx, row in pending_df.iterrows():
        cites_taxon = row["Taxon"]
        base_info = {
            "cites_taxon": cites_taxon,
            "cites_class": row["Class"],
        }

        try:
            iucn_rows = fetch_taxon_raw_iucn(session, row["genus_name"], row["species_name"])
            if iucn_rows:
                for item in iucn_rows:
                    results.append({**base_info, **item})
            else:
                results.append(
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
                )
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Erreur réseau sur {cites_taxon} (sera retenté au prochain lancement) : {e}")
            continue

        if (idx + 1) % SAVE_EVERY == 0 or (idx + 1) == total:
            save_dataframe(pd.DataFrame(results), OUTPUT_FILE)
            print(f"💾 Progression sauvegardée : {idx + 1}/{total} nouveaux taxons traités.")

        time.sleep(REQUEST_DELAY)

    print(f"✅ Extraction brute terminée : {OUTPUT_FILE} ({len(results)} lignes au total).")


if __name__ == "__main__":
    main()