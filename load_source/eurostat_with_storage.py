"""
Publie les données Eurostat sur le storage Cellar (Clever Cloud).

Même logique que load_source/cites_with_storage.py :
    1. récupération des fichiers dans dbt_ETM/input_sources/eurostat/last_version
    2. vérification (au moins un CSV non vide)
    3. upload vers s3://extract/eurostat/last_version + eurostat/metadata.json

La récupération "réelle" (API / chargement en masse Comext) est en cours
de développement en parallèle. En attendant, la fonction `fetch_files`
copie un fichier ou dossier LOCAL. Quand le vrai téléchargement sera prêt,
il suffira de remplacer le contenu de `fetch_files` : le reste ne bouge pas.

Usage :
    uv run load_source/eurostat_with_storage.py
    uv run load_source/eurostat_with_storage.py --source chemin/vers/fichier_ou_dossier
    uv run load_source/eurostat_with_storage.py --dry-run   # sans upload
"""
import argparse
import datetime
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.storage import upload_folder, upload_json  # noqa: E402

OUTPUT_DIR = Path("dbt_ETM/input_sources/eurostat/last_version")
OUTPUT_DIR_TEMP = Path("dbt_ETM/input_sources/eurostat/temp")
REMOTE_FOLDER = "eurostat/last_version"
REMOTE_METADATA = "eurostat/metadata.json"

# Source locale par défaut, utilisée tant que le vrai téléchargement n'existe pas
DEFAULT_LOCAL_SOURCE = Path("dbt_ETM/input_sources/eurostat/local_source")

LOAD_DATE = datetime.date.today().isoformat()
# TO DO  MAX_ARCHIVE_VERSIONS = 5  # nombre de versions conservées sur Cellar


def restore_and_exit(message):
    """Remet la version précédente en place et arrête le script en erreur."""
    print(message)
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    if OUTPUT_DIR_TEMP.exists():
        shutil.move(OUTPUT_DIR_TEMP, OUTPUT_DIR)
    sys.exit(1)


def fetch_files(output_dir: Path, source: Path) -> None:
    """
    Dépose les fichiers bruts Eurostat dans output_dir.

    TO DO : remplacer par le vrai téléchargement (API ou bulk Comext).
    Pour l'instant : copie d'un fichier ou d'un dossier local.
    """
    if not source.exists():
        restore_and_exit(f"Source locale introuvable : {source}")

    output_dir.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, output_dir, dirs_exist_ok=True)
    else:
        shutil.copy2(source, output_dir / source.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, default=DEFAULT_LOCAL_SOURCE,
                        help=f"fichier ou dossier local à publier (défaut : {DEFAULT_LOCAL_SOURCE})")
    parser.add_argument("--dry-run", action="store_true",
                        help="prépare et vérifie les fichiers sans les envoyer sur Cellar")
    args = parser.parse_args()

    print("Loading Eurostat files...")

    # Met de côté la version précédente pour pouvoir la restaurer en cas d'erreur
    if OUTPUT_DIR_TEMP.exists():
        shutil.rmtree(OUTPUT_DIR_TEMP)
    if OUTPUT_DIR.exists():
        shutil.move(OUTPUT_DIR, OUTPUT_DIR_TEMP)

    # Récupération
    fetch_files(OUTPUT_DIR, args.source)
    print("Fichiers récupérés : ", OUTPUT_DIR)

    # Vérifie qu'on a au moins un CSV non vide
    csv_files = list(OUTPUT_DIR.glob("*.csv"))
    print(f"Nombre de fichiers CSV dans {OUTPUT_DIR} : {len(csv_files)}")
    if not csv_files:
        restore_and_exit("Aucun fichier CSV trouvé")
    empty = [f.name for f in csv_files if f.stat().st_size == 0]
    if empty:
        restore_and_exit(f"Fichier(s) CSV vide(s) : {', '.join(empty)}")

    # TO DO
    # Archive l'ANCIENNE version (celle actuellement sur Cellar) dans eurostat/archive/{previous_load_date}

    if args.dry_run:
        print(f"Dry run : upload ignoré (aurait publié vers {REMOTE_FOLDER})")
    else:
        # Publie la nouvelle version sur Cellar et met à jour la date dans metadata.json
        try:
            upload_folder(OUTPUT_DIR, REMOTE_FOLDER)
            upload_json({"load_date": LOAD_DATE}, REMOTE_METADATA)
        except Exception as e:  # noqa: BLE001 - on veut restaurer quelle que soit l'erreur
            restore_and_exit(f"Erreur lors de l'upload sur Cellar : {e}")

    # Supprime la version précédente mise de côté
    if OUTPUT_DIR_TEMP.exists():
        shutil.rmtree(OUTPUT_DIR_TEMP)

    if not args.dry_run:
        print("Données Eurostat publiées sur Cellar")


if __name__ == "__main__":
    main()
