import datetime
import io
import logging
import shutil
import sys
import zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.storage import upload_folder, upload_json

url_archive = "https://trade.cites.org/fr/cites_trade/download_db"
OUTPUT_DIR = Path("dbt_ETM/input_sources/CITES/last_version")
OUTPUT_DIR_TEMP = Path("dbt_ETM/input_sources/CITES/temp")

LOAD_DATE = datetime.date.today().isoformat()
# TO DO  MAX_ARCHIVE_VERSIONS = 5  # nombre de versions conservées sur Cellar

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def restore_and_exit(message):
    logger.error(message)
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    if OUTPUT_DIR_TEMP.exists():
        shutil.move(OUTPUT_DIR_TEMP, OUTPUT_DIR)
    sys.exit(1)


def run() -> None:
    logger.info("Loading CITES trades files...")

    # Déplace le fichier temporairement
    if OUTPUT_DIR.exists():
        shutil.move(OUTPUT_DIR, OUTPUT_DIR_TEMP)

    # Téléchargement
    response = requests.get(url_archive, timeout=120)
    response.raise_for_status()
    if response.status_code != 200:
        restore_and_exit(
            f"❌ Erreur lors du téléchargement (code {response.status_code})"
        )

    # Vérifie que le contenu téléchargé est bien un zip valide
    zip_bytes = io.BytesIO(response.content)
    if not zipfile.is_zipfile(zip_bytes):
        restore_and_exit("❌ Le fichier téléchargé n'est pas un zip valide")

    # Extraction
    with zipfile.ZipFile(zip_bytes) as zip_ref:
        zip_ref.extractall(OUTPUT_DIR)
    logger.info("✅ Export terminé : %s", OUTPUT_DIR)

    # Compte le nombre de fichiers CSV directement dans OUTPUT_DIR
    nb_csv = len(list(OUTPUT_DIR.glob("*.csv")))
    logger.info("Nombre de fichiers CSV dans %s : %d", OUTPUT_DIR, nb_csv)
    if nb_csv == 0:
        restore_and_exit("❌ Aucun fichier CSV trouvé après extraction")

    # TO DO
    # Archive l'ANCIENNE version (celle actuellement sur Cellar) dans CITES/archive/{previous_load_date}
    # {previous_load_date} : date de son téléchargement ou à la date actuelle si l'ancienne date a été perdue/corrompue

    # Publie la nouvelle version sur Cellar et met à jour la data dans metadata.json
    upload_folder(OUTPUT_DIR, "CITES/last_version")
    upload_json({"load_date": LOAD_DATE}, "CITES/metadata.json")

    # Supprime le téléchargement précédemet mis dans le dossier temporaire
    if OUTPUT_DIR_TEMP.exists():
        shutil.rmtree(OUTPUT_DIR_TEMP)

    logger.info("✅ Données CITES publiées sur Cellar")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    run()
