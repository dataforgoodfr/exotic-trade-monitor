import os
from pathlib import Path
import shutil

import pandas as pd
import requests

# ---------------------------------------------------------
# PARAMÈTRES
# ---------------------------------------------------------
API_TOKEN = os.getenv("IUCN_API_TOKEN")
BASE_URL = "https://api.iucnredlist.org/api/v4"
OUTPUT_DIR = Path("dbt_ETM/input_sources/iucn/last_version")

TEST_SPECIES = [
    {"genus_name": "Panthera", "species_name": "leo"},
    {"genus_name": "Testudo", "species_name": "hermanni"},
]


# ---------------------------------------------------------
# RÉCUPÉRATION DES DONNÉES
# ---------------------------------------------------------
def get_headers() -> dict:
    if not API_TOKEN:
        raise ValueError("Variable IUCN_API_TOKEN manquante. Utilise --env-file .env")
    return {
        "Authorization": f"Bearer {API_TOKEN}",
        "Accept": "application/json",
    }


def fetch_taxon(genus: str, species: str) -> dict:
    url = f"{BASE_URL}/taxa/scientific_name"
    params = {"genus_name": genus, "species_name": species}
    response = requests.get(url, headers=get_headers(), params=params, timeout=30)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------
# VALIDATIONS QUALITÉ (PARE-FEU AVANT UPLOAD)
# ---------------------------------------------------------
def validate_dataframe(df: pd.DataFrame, min_rows: int = 1) -> pd.DataFrame:
    """Contrôle la structure et l'intégrité des données en mémoire."""
    # 1. Volumétrie
    if df.empty or len(df) < min_rows:
        raise ValueError(f"Volumétrie insuffisante : {len(df)} lignes (minimum : {min_rows}).")

    # 2. Présence des colonnes critiques
    required_cols = {"taxon.sis_id", "taxon.scientific_name", "assessments"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"Colonnes critiques manquantes : {missing_cols}")

    # 3. Intégrité de la clé primaire (pas de valeurs nulles + suppression des doublons)
    if df["taxon.sis_id"].isna().any():
        raise ValueError("Valeurs nulles détectées dans 'taxon.sis_id'.")

    df_clean = df.drop_duplicates(subset=["taxon.sis_id"]).reset_index(drop=True)
    return df_clean


def validate_output_file(file_path: Path) -> None:
    """Contrôle l'intégrité physique du fichier écrit sur le disque."""
    # 4. Existence et taille > 0 octet
    if not file_path.exists() or file_path.stat().st_size == 0:
        raise RuntimeError(f"Le fichier généré est absent ou vide : {file_path}")


# ---------------------------------------------------------
# EXÉCUTION ET EXPORT CSV
# ---------------------------------------------------------
def main():
    records = []

    for item in TEST_SPECIES:
        genus = item["genus_name"]
        species = item["species_name"]
        print(f"Récupération : {genus} {species}...")
        try:
            data = fetch_taxon(genus, species)
            df_item = pd.json_normalize(data)
            records.append(df_item)
        except requests.exceptions.HTTPError as e:
            print(f"Erreur HTTP pour {genus} {species} : {e}")

    if not records:
        raise RuntimeError("Échec complet de l'extraction : aucune donnée récupérée.")

    final_df = pd.concat(records, ignore_index=True)

    # Validations 1, 2 et 3 avant écriture
    final_df = validate_dataframe(final_df, min_rows=1)

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / "iucn_test_species.csv"
    final_df.to_csv(
        output_file,
        index=False,
        sep=",",
        encoding="utf-8-sig",
    )

    # Validation 4 avant le futur envoi vers Clever Cloud
    validate_output_file(output_file)
    print(f"✅ Validations réussies et export terminé : {output_file} ({len(final_df)} lignes)")

    # TO DO : Appeler ici la fonction d'upload vers le bucket Clever Cloud


if __name__ == "__main__":
    main()