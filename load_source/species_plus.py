# Télécharge la base Species+ complète et la découpe en un CSV par table
# dans dbt_ETM/input_sources/speciesplus/last_version
#
# Étapes :
#   1. Demander à l'API la liste des téléchargements disponibles.
#   2. Télécharger le premier : un gzip de lignes JSON (une ligne = un taxon).
#   3. Sortir les listes imbriquées de chaque taxon (synonymes, noms communs,
#      listings CITES...) dans des tables séparées, liées par l'id du taxon.
#   4. Remplacer les anciens CSV par les nouveaux.
#
# Tout est fait en mémoire avant l'étape 4 : si le téléchargement échoue,
# le script s'arrête et les anciens CSV restent intacts.
#
# À lancer depuis la racine du dépôt : uv run load_source/speciesplus.py

import io
import os
import json
import gzip
import shutil
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
load_dotenv()  # Charge les variables du fichier .env dans l'environnement

OUTPUT_DIR = Path("dbt_ETM/input_sources/speciesplus/last_version")

# Token de l'API, stocké dans le fichier .env (non commité)
token = os.getenv("SPECIESPLUS_TOKEN")

# --- 1. Liste des téléchargements disponibles ------------------------------
url = "https://api.speciesplus.net/"
endpoint = '/api/v1/downloads'
headers = {
    "X-Authentication-Token": token,
    "Accept": "application/json",
}
params = {
    # "name": "Mammalia",
}
response = requests.get(url + endpoint, headers=headers, params=params, timeout=30)
response.raise_for_status()  # arrête tout si l'appel à l'API a échoué
data = response.json()

# --- 2. Téléchargement du premier fichier de la liste ----------------------
url_download = data[0]['download_url']
response = requests.get(url_download, timeout=60)
response.raise_for_status()  # arrête tout si le téléchargement a échoué

# --- 3. Découpage : une ligne par taxon + des tables filles ----------------
# Les clés dont la valeur est une liste → chacune devient une table
LIST_KEYS = ["synonyms", "accepted_names", "common_names", "cites_listings", "cites_quotas",
             "cites_suspensions", "eu_listings", "eu_decisions", "distributions", "references"]

# Une liste vide par table ; tb_taxon_concepts = table principale (un taxon par ligne)
tables = {"tb_taxon_concepts": []}
for key in LIST_KEYS:
    tables[f"tb_{key}"] = []

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
                # Ajoute l'id du taxon à chaque ligne fille (clé étrangère)
                for row_dict in to_add:
                    row_dict["taxon_concept_id"] = taxon_concept_id
                tables[keys].extend(to_add)
        # Le reste du taxon va dans la table principale
        tables["tb_taxon_concepts"].append(taxon)

# --- 4. Remplacement des anciens CSV par les nouveaux ----------------------
# TO DO : historiser dans dbt_ETM\\input_sources\\speciesplus\\archive
if OUTPUT_DIR.exists():
    shutil.rmtree(OUTPUT_DIR)
OUTPUT_DIR.mkdir(parents=True)

# json_normalize transforme les dictionnaires imbriqués en colonnes : {"a": {"b": 1}} -> a_b
for keys in tables.keys():
    df = pd.json_normalize(tables[keys], sep="_")
    df.to_csv(OUTPUT_DIR / f"{keys}.csv", index=False)
    print(f"📄 {keys}.csv : {len(df)} lignes")
print("✅ Export terminé : ", OUTPUT_DIR)