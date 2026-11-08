# DataForGood Saison 15 - Exotic Trade Monitor


## Le dépôt

| Dossier | Rôle |
|---|---|
| `dbt_ETM/` | Les fichiers et configuration dbt |
| `jupyter_notebooks/` | Les analyses de données |
| `load_source/` | Les scripts python pour charger la donnée de puis les différents sites |

## Installation

- [Installation de Python](#installation-de-python)

Ce projet utilise [uv](https://docs.astral.sh/uv/) pour la gestion des dépendances Python. Il est préréquis pour l'installation de ce projet.

Une fois installé, il suffit de lancer la commande suivante pour installer la version de Python adéquate, créer un environnement virtuel et installer les dépendances du projet.

```bash
uv sync
```

A l'usage, si vous utilisez VSCode, l'environnement virtuel sera automatiquement activé lorsque vous ouvrirez le projet. Sinon, il suffit de l'activer manuellement avec la commande suivante :

```bash
source .venv/bin/activate
```

Ou alors, utilisez la commande `uv run ...` (au lieu de `python ...`) pour lancer un script Python. Par exemple:

```bash
uv run pipelines/run.py run download_inputs
```


## Lancer les precommit-hook localement

[Installer les precommit](https://pre-commit.com/)

Assurez-vous que le code satisfait tous les pre-commit avant de créer votre pull request :

```bash
uv run pre-commit run --all-files
```

Ou si vous voulez tester que les fichiers qui ont été modifiés sur votre branche par rapport à main

```bash
uv run pre-commit run --from-ref origin/main --to-ref HEAD
```


## Ingestion des données

Le dossier dbt_ETM\input_sources contient les fichiers de données brutes téléchargées d'internet
On a un dossier par source.

Et dans chaque dossier :
- un dossier last_version avec les données les plus à jours
- et un dossier archive avec les données précédement chargées (à voir combien de version on souhaite conserver)

Pour le moment : pour charger les données en local il faut exécuter les scripts suivant dans votre terminal
```bash
uv run .\load_source\cites.py
uv run .\load_source\eurostat.py
```

## Transformation des données

Il faut toujours être dans le dossier dbt_ETM pour lancer les commandes dbt

Pour executer tous les modèles dbt
```bash
uv run dbt run
```

Pour executer un model dbt précis
```bash
uv run dbt run -s mon_model
```

Pour tester le run et les checks dbt en local
```bash
uv run pre-commit run --hook-stage manual  --all-files
```
**Attention, en pré requis** :
1. Avoir commiter les modifiations (pas forcement push)
2. Etre dans le dossier dbt_ETM 
3. Avoir fait la commande `uv run dbt run` en local

## Analyse de données

Les analyses se font via Jupyter Notebook dans le dossier jupyter_notebooks:

```bash
uv run jupyter notebook
```

