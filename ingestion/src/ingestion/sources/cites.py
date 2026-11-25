import io
import shutil
import sys
import zipfile
from pathlib import Path

import requests

from ingestion import INPUT_SOURCES_DIR

URL_ARCHIVE = "https://trade.cites.org/fr/cites_trade/download_db"
OUTPUT_DIR = INPUT_SOURCES_DIR / "CITES" / "last_version"
OUTPUT_DIR_TEMP = INPUT_SOURCES_DIR / "CITES" / "temp"


def restore_and_exit(
    message: str, output_dir: Path = OUTPUT_DIR, temp_dir: Path = OUTPUT_DIR_TEMP
) -> None:
    print(message)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    if temp_dir.exists():
        shutil.move(temp_dir, output_dir)
    sys.exit(1)


def run() -> None:
    OUTPUT_DIR.parent.mkdir(parents=True, exist_ok=True)

    # Déplace le fichier temporairement
    # TO DO : historiser dans dbt_ETM/input_sources/CITES/archive
    if OUTPUT_DIR.exists():
        if OUTPUT_DIR_TEMP.exists():
            shutil.rmtree(OUTPUT_DIR_TEMP)
        shutil.move(OUTPUT_DIR, OUTPUT_DIR_TEMP)

    # Téléchargement
    response = requests.get(URL_ARCHIVE)
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
    print("✅ Export terminé : ", OUTPUT_DIR)

    # Compte le nombre de fichiers CSV directement dans OUTPUT_DIR
    nb_csv = len(list(OUTPUT_DIR.glob("*.csv")))
    print(f"📄 Nombre de fichiers CSV dans {OUTPUT_DIR} : {nb_csv}")
    if nb_csv == 0:
        restore_and_exit("❌ Aucun fichier CSV trouvé après extraction")

    # Supprime le téléchargement précédemment mis dans le dossier temporaire
    if OUTPUT_DIR_TEMP.exists():
        shutil.rmtree(OUTPUT_DIR_TEMP)


if __name__ == "__main__":
    run()
