import requests
import zipfile
import io
import shutil
from pathlib import Path

url_archive = "https://trade.cites.org/fr/cites_trade/download_db"
OUTPUT_DIR = Path("dbt_ETM\\input_sources\\CITES\\last_version")

# Supprime le précédent téléchargement 
# TO DO : historiser dans dbt_ETM\\input_sources\\CITES\\archive
if OUTPUT_DIR.exists():
    shutil.rmtree(OUTPUT_DIR)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Téléchargement et extraction
response = requests.get(url_archive)
with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
    zip_ref.extractall(OUTPUT_DIR)
