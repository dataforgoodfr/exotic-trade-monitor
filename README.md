# DataForGood Saison 15 - Exotic Trade Monitor

## Le dépôt

| Dossier | Rôle |
| --- | --- |
| `dbt_ETM/` | Les fichiers et configuration dbt |
| `notebooks/` | Les analyses de données |
| `ingestion/` | Package Python pour charger les données depuis les différentes sources |

## Installation

<<<<<<< HEAD
- [Installation de Python](#installation)
=======
Ce projet utilise [uv](https://docs.astral.sh/uv/) pour la gestion des dépendances Python (organisé en `uv` workspace avec des `dependency-groups`). Il est préréquis pour l'installation de ce projet.
>>>>>>> f522698 (refactor(#40): refactor python codebase into package and add makefile)

Une fois installé, il suffit de lancer la commande suivante pour installer la version de Python adéquate, créer un environnement virtuel et installer l'ensemble des dépendances du projet :

```bash
uv sync
# ou via Makefile :
make install
```

Il est également possible d'installer uniquement certains sous-ensembles de dépendances :

```bash
# Uniquement le package d'ingestion (ou `make install-ingestion`)
uv sync --package ingestion --no-default-groups

# Uniquement dbt (sans les notebooks)
uv sync --only-group dbt

# Uniquement les notebooks
uv sync --only-group notebooks
```

A l'usage, si vous utilisez VSCode, l'environnement virtuel sera automatiquement activé lorsque vous ouvrirez le projet. Sinon, il suffit de l'activer manuellement avec la commande suivante :

```bash
source .venv/bin/activate
```

<<<<<<< HEAD
Ou alors, utilisez la commande `uv run ...` (au lieu de `python ...`) pour lancer un script Python. Par exemple :
=======
Ou alors, utilisez la commande `uv run ...` (au lieu de `python ...`) pour lancer un script ou une commande Python. Par exemple:
>>>>>>> f522698 (refactor(#40): refactor python codebase into package and add makefile)

```bash
uv run ingest
# ou via Makefile :
make ingest
```

<<<<<<< HEAD
=======
## Commandes courantes (Makefile)

Un `Makefile` à la racine regroupe des raccourcis pour les tâches courantes (`make install`, `make ingest`, `make dbt-run`, `make dbt-build`, `make lint`, etc.). Lancez `make` ou `make help` pour afficher la liste complète des cibles disponibles.

>>>>>>> f522698 (refactor(#40): refactor python codebase into package and add makefile)
## Lancer les precommit-hook localement

[Installer les precommit](https://pre-commit.com/)

Assurez-vous que le code satisfait tous les pre-commit avant de créer votre pull request :

```bash
uv run pre-commit run --all-files
# ou via Makefile :
make lint
```

Ou si vous voulez tester que les fichiers qui ont été modifiés sur votre branche par rapport à main

```bash
uv run pre-commit run --from-ref origin/main --to-ref HEAD
```

## Ingestion des données

Le dossier dbt_ETM/input_sources contient les fichiers de données brutes téléchargées d'internet
On a un dossier par source.

Et dans chaque dossier :

- un dossier last_version avec les données les plus à jours
- et un dossier archive avec les données précédement chargées (à voir combien de version on souhaite conserver)

<<<<<<< HEAD
Pour le moment : pour charger les données en local il faut exécuter les scripts suivant dans votre terminal
=======
Pour charger toutes les sources de données en local, exécutez la commande suivante dans votre terminal :
>>>>>>> f522698 (refactor(#40): refactor python codebase into package and add makefile)

```bash
uv run ingest
# ou via Makefile :
make ingest
```

Vous pouvez aussi ne charger qu'une ou plusieurs sources spécifiques :

```bash
uv run ingest cites
uv run ingest eurostat
# ou via Makefile :
make ingest SOURCES=cites
```

### Ajouter une nouvelle source

Pour ajouter une nouvelle source de données (aucune modification des workflows GitHub Actions n'est nécessaire) :

1. **Créer le module** `ingestion/src/ingestion/sources/<ma_source>.py` avec une fonction `run() -> None` qui écrit les fichiers téléchargés dans `INPUT_SOURCES_DIR / "<ma_source>" / "last_version"` (importé depuis `ingestion`) :

   ```python
   from ingestion import INPUT_SOURCES_DIR

   OUTPUT_DIR = INPUT_SOURCES_DIR / "<ma_source>" / "last_version"


   def run() -> None:
       OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
       # Téléchargement et export des données dans OUTPUT_DIR
   ```

2. **Enregistrer la source** dans `ingestion/src/ingestion/sources/__init__.py` en l'ajoutant au dictionnaire `SOURCES` :

   ```python
   from ingestion.sources import cites, eurostat, <ma_source>

   SOURCES: dict[str, Callable[[], None]] = {
       "cites": cites.run,
       "eurostat": eurostat.run,
       "<ma_source>": <ma_source>.run,
   }
   ```

   Elle sera automatiquement prise en compte par `uv run ingest`, `make ingest` et le pipeline CI.

3. **Ajouter d'éventuelles dépendances Python** au package `ingestion` (`ingestion/pyproject.toml`) :

   ```bash
   uv add --package ingestion <paquet>
   ```

4. **Tester localement** :

   ```bash
   uv run ingest <ma_source>
   # ou :
   make ingest SOURCES=<ma_source>
   ```

## Transformation des données

Il faut toujours être dans le dossier `dbt_ETM` pour lancer les commandes `dbt` directement (ou utiliser `make dbt-*` depuis la racine).

Pour executer tous les modèles dbt:

```bash
uv run dbt run
# ou depuis la racine via Makefile :
make dbt-run
```

Pour executer un model dbt précis:

```bash
uv run dbt run -s mon_model
```

**Pour tester le run et les checks dbt de CI en local avant de pusher:**

```bash
uv run pre-commit run --hook-stage manual  --all-files
# ou via Makefile :
make dbt-check
```

**Attention, en pré requis** :

1. Avoir commité les modifiations sur git (pas forcement push)
2. Etre dans le dossier dbt_ETM
3. Avoir fait la commande `uv run dbt build` en local (ou `make dbt-build`)
4. Avoir fait la commande `uv run dbt docs generate` en local (ou `make dbt-docs`)

## Analyse de données

Les analyses se font via Jupyter Notebook dans le dossier notebooks :

```bash
uv run jupyter notebook
# ou via Makefile :
make jupyter
```

**Attention, en pré requis pour lire les données dans la base de données** :

1. Avoir téléchargé en local les fichiers à ingérer (cf partie "Ingestion des données")
2. Avoir fait la commande `uv run dbt run` en local dans le dossier dbt_ETM (ou `make dbt-run`)

Ou avec les notebooks marino

voir documentation :

- <https://duckdb.org/docs/2.0/guides/python/marimo>
- <https://docs.marimo.io/>

Pour le tutorial marino:

```bash
uv run marimo tutorial intro
```

Pour créer un nouveau notebook

```bash
uv run marimo edit
# ou via Makefile :
make marimo
```

Pour éditer un notebook

```bash
uv run marimo edit exemple_duckdb.py
```
