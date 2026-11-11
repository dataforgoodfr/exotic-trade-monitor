import requests
import zipfile
import io
import shutil
import sys
from pathlib import Path

url_archive = "https://trade.cites.org/fr/cites_trade/download_db"
OUTPUT_DIR = Path("dbt_ETM/input_sources/CITES/last_version")
OUTPUT_DIR_TEMP = Path("dbt_ETM/input_sources/CITES/temp")

def restore_and_exit(message):
    print(message)
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    if OUTPUT_DIR_TEMP.exists():
        shutil.move(OUTPUT_DIR_TEMP, OUTPUT_DIR)
    sys.exit(1)

# Déplace le fichier temporairement
# TO DO : historiser dans dbt_ETM\\input_sources\\CITES\\archive
if OUTPUT_DIR.exists():
    shutil.move(OUTPUT_DIR, OUTPUT_DIR_TEMP)

# Téléchargement
response = requests.get(url_archive)
if response.status_code != 200:
    restore_and_exit(f"❌ Erreur lors du téléchargement (code {response.status_code})")

# Vérifie que le contenu téléchargé est bien un zip valide
zip_bytes = io.BytesIO(response.content)
if not zipfile.is_zipfile(zip_bytes):
    restore_and_exit("❌ Le fichier téléchargé n'est pas un zip valide")

# Extraction
with zipfile.ZipFile(zip_bytes) as zip_ref:
    zip_ref.extractall(OUTPUT_DIR)
print("✅ Export terminé : ", OUTPUT_DIR)

# Compte le nombre de fichiers CSV directement dans OUTPUT_DIR 
nb_csv = len(list(OUTPUT_DIR.glob("*.csv")))
print(f"📄 Nombre de fichiers CSV dans {OUTPUT_DIR} : {nb_csv}")
if nb_csv == 0:
    restore_and_exit("❌ Aucun fichier CSV trouvé après extraction")

# Supprime le téléchargement précédemet mis dans le dossier temporaire
if OUTPUT_DIR_TEMP.exists():
    shutil.rmtree(OUTPUT_DIR_TEMP)
