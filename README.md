# Template DataForGood

This file will become your README and also the index of your
documentation.

# Contributing


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
uv run pipelines/run.py run build_database
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

## Utiliser Tox pour tester votre code

    tox -vv

## Ingestion des données

Le dossier dbt_ETM\models\source contient les fichiers de données brutes téléchargées d'internet
On a un dossier par source.

Et dans chaque dossier :
- un dossier last_version avec les données les plus à jours
- et un dossier archive avec les données précédement chargées (à voir combien de version on souhaite conserver)

## Transformation des données

Il faut aller dans le dossier dbt_ETM pour utiliser les commandes dbt et tester que le code tourne sans erreur

Pour executer tous les modèles
```bash
uv run dbt run
```
Pour executer un model précis
```bash
uv run dbt run -s mon_model
```

Pour tester le run et les checks dbt en local
```bash
uv run pre-commit run --hook-stage manual  --all-files
```
**Attention** : il faut avoir commiter les modifiations (pas forcement push)

**Remarque** : pre-commit refait un run et crée un dev.duckdb. C'est cette db locale qui est testée avec la commande précédente.
Pas celui généré "manuellement" par un uv run dbt (qui lui est dans dbt_ETM\dev.duckdb)

## Analyse de données

Les analyses se font via Jupyter Notebook dans le dossier jupyter_notebooks:

```bash
uv run jupyter notebook
```

