"""Ouvrir DuckDB UI sur la base locale produite par dbt."""

import argparse
import sys
import threading
from pathlib import Path

import duckdb

DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "dbt_ETM" / "dev.duckdb"


def main():
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument("-h", "--help", action="help", help="Afficher cette aide.")
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help="Chemin de la base DuckDB (par défaut : dbt_ETM/dev.duckdb).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Démarrer le serveur sans ouvrir le navigateur.",
    )
    args = parser.parse_args()
    database = args.database.expanduser().resolve()
    if not database.is_file():
        parser.exit(
            1,
            f"Base introuvable : {database}\n"
            "Depuis dbt_ETM, exécutez « uv run dbt deps », puis "
            "« uv run dbt build » après avoir téléchargé les données sources.\n",
        )

    # L'interface a besoin d'un catalogue accessible en écriture pour son état.
    # Seule la base produite par dbt est attachée en lecture seule.
    connection = duckdb.connect(":memory:")
    try:
        # ATTACH n'accepte pas de paramètre lié : échapper le littéral SQL.
        database_literal = str(database).replace("'", "''")
        connection.execute(f"ATTACH '{database_literal}' AS etm (READ_ONLY)")
        connection.execute("INSTALL ui")
        connection.execute("LOAD ui")
        command = "CALL start_ui_server()" if args.no_browser else "CALL start_ui()"
        connection.execute(command)
        print(f"Base attachée en lecture seule : {database}", flush=True)
        print("Interface : http://localhost:4213", flush=True)
        print("Exemple : SELECT * FROM etm.main_raw.raw_cites LIMIT 100;", flush=True)
        print("Gardez ce terminal ouvert. Ctrl+C pour arrêter.", flush=True)
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\nArrêt de DuckDB UI.")
    except duckdb.Error as error:
        print(
            f"Impossible de lancer DuckDB UI : {error}\n"
            "Si la base est verrouillée, fermez les connexions concurrentes "
            "(dbt, notebook ou extension VS Code).\n"
            "Si l'extension ui ne se télécharge pas, vérifiez votre accès "
            "Internet à extensions.duckdb.org.",
            file=sys.stderr,
        )
        return 1
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
