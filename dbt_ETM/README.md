# Welcome to Exotic Trade Monitor dbt project!


## La structure du dossier dbt_ETM

- dbt_ETM/input_sources : <br>
Les fichiers brutes importés des différentes sources en local <br>
A terme ces données seront chargées depuis clever cloud en local avec un script (download_inputs.py) - **NE PAS COMMITER**

- dbt_ETM/models : les models SQL de dbt <br>
Les models sont organisés de la manière suivante : <br>
  - raw : dossier pour les données brutes 
  - intermediaire : dossier pour les données données brutes retravaillées, nettoyées, etc 
  - metabse : dossier pour les données qui seront lues pour l'outil de BI pour l'association
  - website : dossier pour les tables consolidées pour le site web à destination du public

On fait un fichier de documentation par model, pour éviter au maximum les conflits git.
Le fichier de documentation/test est un fichier yaml avec le même nom que le model sql.

- dbt_ETM/test :  les test SQL de dbt
- dbt_ETM/models : les fichiers de petites tailles qui ne bougent pas
- dbt_ETM/target : Les models compilés et executés en local - **NE PAS COMMITER**


## Commandes de base

Toujours être dans le dossier dbt_ETM.<br>

Executer/Créer un modèle SQL
```bash
uv run dbt run -s model_name
```

Tester un modèle SQL
```bash
uv run  dbt test -s model_name
```

Executer/Créer et tester un modèle SQL
```bash
uv run  dbt build -s model_name
```


## Excuter plusieurs modeles8 SQL

- Utiliser + :
    - Avant le nom du model (+model_name): va executer tous les modèles nécessaires en amont + ce modèles execute every dependencies
    - Apres le nom du model (model_name+) :  va executer ce modèle et tous les modèles qui le suivent
    - Avant et apres le nom du model  (+model_name+) : va executer les modèles en amont, ce modèle et tous les modèles qui le suivent e
- Utiliser tag : Pour executer les modèles DBT qui ont été étiquettés 

Fait la liste des modèles DBT qui serait executés par la commande `dbt run` avec les mêmes options
```bash
uv run  dbt list -tag:raw
```

## Documentation et tests

Comment ? : Ecrire un fichier model_name.yml pour chque model_name.sql<br>

Voici un exemple de fichier de documentation et de test.<br>
Vous pouvez aussi regarder les fichiers déjà écrits dans le dépots


```bash
version: 2

models:
  - name: my_first_dbt_model
    description: "A starter dbt model"
    columns:
      - name: id
        description: "The primary key for this table"
        data_tests:
          - unique
          - not_null
```

### Resources:
- Learn more about dbt [in the docs](https://docs.getdbt.com/docs/introduction)
- Check out [Discourse](https://discourse.getdbt.com/) for commonly asked questions and answers
- Join the [chat](https://community.getdbt.com/) on Slack for live discussions and support
- Find [dbt events](https://events.getdbt.com) near you
- Check out [the blog](https://blog.getdbt.com/) for the latest news on dbt's development and best practices
