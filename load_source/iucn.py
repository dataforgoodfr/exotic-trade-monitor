import os
from pathlib import Path
import shutil
import sys
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
OUTPUT_DIR_TEMP = Path("dbt_ETM/input_sources/iucn/temp")

# Étendre cette liste une fois le périmètre validé (ex: "Aves", "Reptilia", "Amphibia")
TARGET_CLASSES = ["Mammalia"]

# Mettre un entier (ex: 10) pour un test rapide, ou None pour tout charger
MAX_SPECIES: int | None = None
REQUEST_DELAY = 1.0


# ---------------------------------------------------------
# LECTURE ET FILTRAGE DES TAXONS CITES
# ---------------------------------------------------------
def get_cites_species(cites_dir: Path, target_classes: list[str]) -> pd.DataFrame:
    """Extrait les espèces uniques vivantes des classes ciblées depuis CITES."""
    csv_files = list(cites_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"Aucun fichier CSV CITES trouvé dans {cites_dir}")

    df = pd.concat(
        [pd.read_csv(f, usecols=["Taxon", "Class", "Term"], low_memory=False) for f in csv_files],
        ignore_index=True,
    )

    # Filtre périmètre V0 : vivant + classes ciblées
    df = df[(df["Term"] == "live") & (df["Class"].isin(target_classes))].copy()
    df = df.dropna(subset=["Taxon"])

    # Exclusion des taxons au niveau genre (spp.) et des hybrides
    mask_excluded = df["Taxon"].str.contains(r"\bspp\.|\bhybrid\b", case=False, regex=True)
    df = df[~mask_excluded]

    # Dédoublonnage sur le nom scientifique exact CITES
    species_df = df[["Taxon", "Class"]].drop_duplicates(subset=["Taxon"]).reset_index(drop=True)

    # Découpage en genus_name et species_name (2 premiers mots)
    parts = species_df["Taxon"].str.strip().str.split()
    species_df = species_df[parts.str.len() >= 2].copy()
    species_df["genus_name"] = parts.str[0]
    species_df["species_name"] = parts.str[1]

    return species_df.reset_index(drop=True)


# ---------------------------------------------------------
# APPELS API IUCN V4
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
    for attempt in range(3):
        response = session.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json()
        if response.status_code == 404:
            return None
        if response.status_code == 429:
            wait = 5 * (attempt + 1)
            print(f"⏳ Rate limit atteint, pause de {wait}s...")
            time.sleep(wait)
            continue
        response.raise_for_status()
    return None


def select_latest_global_assessment(assessments: list[dict]) -> dict | None:
    """Sélectionne la dernière évaluation (priorité au scope Global code='1')."""
    latest = [a for a in assessments if a.get("latest") is True]
    if not latest:
        return None

    for assessment in latest:
        scopes = assessment.get("scopes") or []
        if any(str(s.get("code")) == "1" for s in scopes):
            return assessment

    return latest[0]


def fetch_species_iucn(session: requests.Session, genus: str, species: str) -> dict | None:
    """Récupère sis_id, catégorie de menace et tendance de population pour une espèce."""
    taxon_data = get_with_retry(
        session,
        f"{BASE_URL}/taxa/scientific_name",
        params={"genus_name": genus, "species_name": species},
    )
    if not taxon_data:
        return None

    taxon_info = taxon_data.get("taxon") or {}
    assessments = taxon_data.get("assessments") or []
    latest_assessment = select_latest_global_assessment(assessments)

    if not latest_assessment:
        return None

    assessment_id = latest_assessment.get("assessment_id")
    categorie_uicn = latest_assessment.get("red_list_category_code")
    tendance_uicn = None

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

    return {
        "taxon_sis_id": taxon_info.get("sis_id"),
        "iucn_scientific_name": taxon_info.get("scientific_name"),
        "assessment_id": assessment_id,
        "assessment_year": latest_assessment.get("year_published"),
        "categorie_uicn": categorie_uicn,
        "tendance_uicn": tendance_uicn,
    }


# ---------------------------------------------------------
# VALIDATIONS QUALITÉ (PARE-FEU)
# ---------------------------------------------------------
def validate_dataframe(df: pd.DataFrame, min_rows: int = 1) -> pd.DataFrame:
    """Contrôle la structure et l'intégrité des données avant écriture."""
    if df.empty or len(df) < min_rows:
        raise ValueError(f"Volumétrie insuffisante : {len(df)} lignes (minimum : {min_rows}).")

    required_cols = {"cites_taxon", "taxon_sis_id", "categorie_uicn", "tendance_uicn"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"Colonnes critiques manquantes : {missing_cols}")

    if df["cites_taxon"].isna().any():
        raise ValueError("Valeurs nulles détectées dans 'cites_taxon'.")

    return df.drop_duplicates(subset=["cites_taxon"]).reset_index(drop=True)


def restore_and_exit(message: str) -> None:
    """Restaure la version précédente en cas d'échec."""
    print(message)
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    if OUTPUT_DIR_TEMP.exists():
        shutil.move(OUTPUT_DIR_TEMP, OUTPUT_DIR)
    sys.exit(1)


# ---------------------------------------------------------
# EXÉCUTION PRINCIPALE
# ---------------------------------------------------------
def main() -> None:
    print(f"Lecture des taxons CITES pour les classes : {TARGET_CLASSES}...")
    species_df = get_cites_species(CITES_DIR, TARGET_CLASSES)

    if MAX_SPECIES is not None:
        species_df = species_df.head(MAX_SPECIES)

    total = len(species_df)
    print(f"📋 {total} espèces uniques à interroger sur l'API IUCN.")

    session = create_session()
    results = []
    not_found = 0

    for idx, row in species_df.iterrows():
        cites_taxon = row["Taxon"]
        genus = row["genus_name"]
        species = row["species_name"]

        try:
            iucn_info = fetch_species_iucn(session, genus, species)
            if iucn_info:
                results.append(
                    {
                        "cites_taxon": cites_taxon,
                        "cites_class": row["Class"],
                        **iucn_info,
                    }
                )
            else:
                not_found += 1
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Erreur réseau sur {cites_taxon} : {e}")

        if (idx + 1) % 50 == 0 or (idx + 1) == total:
            print(f"Progression : {idx + 1}/{total} traitées ({len(results)} trouvées, {not_found} absentes)")

        time.sleep(REQUEST_DELAY)

    if not results:
        raise RuntimeError("Échec complet : aucune espèce trouvée sur l'API IUCN.")

    final_df = pd.DataFrame(results)
    final_df = validate_dataframe(final_df, min_rows=1)

    # Sauvegarde sécurisée avec bascule temporaire
    if OUTPUT_DIR_TEMP.exists():
        shutil.rmtree(OUTPUT_DIR_TEMP)
    if OUTPUT_DIR.exists():
        shutil.move(OUTPUT_DIR, OUTPUT_DIR_TEMP)

    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_file = OUTPUT_DIR / "iucn_species.csv"
        final_df.to_csv(output_file, index=False, sep=",", encoding="utf-8-sig")

        if not output_file.exists() or output_file.stat().st_size == 0:
            raise RuntimeError(f"Fichier généré vide ou absent : {output_file}")

        if OUTPUT_DIR_TEMP.exists():
            shutil.rmtree(OUTPUT_DIR_TEMP)

        print(f"✅ Export terminé : {output_file} ({len(final_df)} espèces enrichies, {not_found} non trouvées)")
    except Exception as e:
        restore_and_exit(f"❌ Échec lors de l'écriture : {e}")


if __name__ == "__main__":
    main()