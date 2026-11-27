# Télécharge la base Species+ complète et la découpe en un CSV par table
# dans dbt_ETM/input_sources/speciesplus/last_version
#
# Étapes :
#   1. Demander à l'API la liste des téléchargements disponibles.
#   2. Télécharger le premier : un gzip de lignes JSON (une ligne = un taxon).
#   3. Sortir les listes imbriquées de chaque taxon (synonymes, noms communs,
#      listings CITES...) dans des tables séparées, liées par l'id du taxon.
#   4. Remplacer les anciens CSV par les nouveaux, avec des colonnes fixes (COLUMNS).
#
# Tout est fait en mémoire avant l'étape 4 : si le téléchargement échoue,
# le script s'arrête et les anciens CSV restent intacts.
#
# Les quotas et suspensions CITES sont vides dans le téléchargement : non chargés.
#
# À lancer depuis la racine du dépôt : uv run load_source/species_plus.py

import io
import os
import json
import gzip
import shutil
import logging
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# PARAMÈTRES
# ---------------------------------------------------------
OUTPUT_DIR = Path("dbt_ETM/input_sources/speciesplus/last_version")
API_URL = "https://api.speciesplus.net/api/v1/downloads/latest"

# Une table par nom ci-dessous (préfixe "tb_").
# Les clés du taxon dont la valeur est une liste, puis les deux tables
# remplies depuis les distributions (références et tags de chaque distribution).
LIST_KEYS = ["synonyms", "accepted_names", "common_names", "cites_listings",
             "eu_listings", "eu_decisions", "distributions", "references",
             "distribution_references", "distribution_tags"]

# Colonnes attendues pour chaque table (toujours les mêmes, dans le même ordre)
# Toutes les tables filles commencent par taxon_concept_id (clé vers tb_taxon_concepts)
COLUMNS = {
    "tb_taxon_concepts": ['id', 'full_name', 'author_year', 'rank', 'name_status', 'updated_at', 'active',
                          'cites_listing', 'eu_listing', 'higher_taxa_kingdom', 'higher_taxa_phylum',
                          'higher_taxa_class', 'higher_taxa_order', 'higher_taxa_family'],
    "tb_accepted_names": ['taxon_concept_id', 'id', 'full_name', 'author_year', 'rank'],
    "tb_synonyms": ['taxon_concept_id', 'id', 'full_name', 'author_year', 'rank'],
    "tb_common_names": ['taxon_concept_id', 'name', 'language'],
    "tb_cites_listings": ['taxon_concept_id', 'id', 'is_current', 'appendix', 'change_type', 'effective_at',
                          'annotation', 'party_iso_code2', 'party_name', 'party_type',
                          'hash_annotation_symbol', 'hash_annotation_note'],
    "tb_eu_listings": ['taxon_concept_id', 'id', 'is_current', 'annex', 'change_type', 'effective_at',
                       'annotation', 'hash_annotation_symbol', 'hash_annotation_note',
                       'party_iso_code2', 'party_name', 'party_type'],
    "tb_eu_decisions": ['taxon_concept_id', 'id', 'notes', 'start_date', 'is_current',
                        'eu_decision_type_name', 'eu_decision_type_description', 'eu_decision_type_type',
                        'geo_entity_iso_code2', 'geo_entity_name', 'geo_entity_type',
                        'start_event_name', 'start_event_date', 'start_event_url',
                        'source_code', 'source_name', 'term_code', 'term_name'],
    "tb_distributions": ['taxon_concept_id', 'id', 'iso_code2', 'name', 'type'],
    "tb_distribution_references": ['taxon_concept_id', 'distribution_id', 'reference'],
    "tb_distribution_tags": ['taxon_concept_id', 'distribution_id', 'tag'],
    "tb_references": ['taxon_concept_id', 'id', 'citation', 'is_standard'],
}


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()  # Charge les variables du fichier .env dans l'environnement

    # Token de l'API, stocké dans le fichier .env (non commité)
    headers = {
        "X-Authentication-Token": os.getenv("SPECIESPLUS_TOKEN"),
        "Accept": "application/json",
    }
    params = {
        "lang": "fr"
    }

    # --- 1. Appel de l'API pour obtenir l'url de téléchargement la plus récente ----------------
    response = requests.get(API_URL, headers=headers, params=params, timeout=30)
    response.raise_for_status()  # arrête tout si l'appel à l'API a échoué
    url_download = response.url
    logger.info("Appel de l'API Species+ : téléchargement du fichier %s", url_download)
    
    # --- 2. Découpage : une ligne par taxon + des tables filles --------------
    # Une liste vide par table ; tb_taxon_concepts = table principale (un taxon par ligne)
    tables = {"tb_taxon_concepts": []}
    for key in LIST_KEYS:
        tables[f"tb_{key}"] = []

    logger.info("Découpage des taxons en tables...")
    # Lecture du gzip en mémoire, ligne par ligne (un objet JSON par ligne = un taxon)
    with gzip.open(io.BytesIO(response.content), "rt", encoding="utf-8") as f:
        for line in f:
            taxon = json.loads(line)
            taxon_concept_id = taxon.get('id')
            for keys in tables.keys():
                name = keys.removeprefix("tb_")
                # Retire la liste du taxon (pour qu'elle ne reste pas dans la table principale)
                to_add = taxon.pop(name, None)
                if to_add:
                    for row_dict in to_add:
                        # Ajoute l'id du taxon à chaque ligne fille (clé étrangère)
                        row_dict["taxon_concept_id"] = taxon_concept_id
                        # Les références et tags d'une distribution vont dans leurs propres tables
                        if keys == "tb_distributions":
                            for reference in row_dict.pop("references", []):
                                tables["tb_distribution_references"].append({
                                    "taxon_concept_id": taxon_concept_id,
                                    "distribution_id": row_dict["id"],
                                    "reference": reference,
                                })
                            for tag in row_dict.pop("tags", []):
                                tables["tb_distribution_tags"].append({
                                    "taxon_concept_id": taxon_concept_id,
                                    "distribution_id": row_dict["id"],
                                    "tag": tag,
                                })
                    tables[keys].extend(to_add)
            # Le reste du taxon va dans la table principale
            tables["tb_taxon_concepts"].append(taxon)

    # --- 3. Remplacement des anciens CSV par les nouveaux --------------------
    # TO DO : historiser dans dbt_ETM\\input_sources\\speciesplus\\archive
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    for keys in tables.keys():
        # json_normalize transforme les dictionnaires imbriqués en colonnes : {"a": {"b": 1}} -> a_b
        df = pd.json_normalize(tables[keys], sep="_")
        df = df.reindex(columns=COLUMNS[keys])  # colonnes fixes ; colonne absente → vide
        df.to_csv(OUTPUT_DIR / f"{keys}.csv", index=False)
        logger.info("%s.csv : %s lignes", keys, len(df))
    logger.info("Export terminé : %s", OUTPUT_DIR)


# Lance le chargement uniquement si le fichier est exécuté directement
# (pas lors d'un import, sinon l'API serait appelée)
if __name__ == "__main__":
    main()
