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

On fait un fichier de documentation par model, pour éviter au maxiumum les conflits git.
Le fichier de documentation/test est un fichier yaml avec le nême nom que le model sql.

- dbt_ETM/test :  les test SQL de dbt
- dbt_ETM/models : les fichiers de petites tailles qui ne bougent pas
- dbt_ETM/target : Les models compilés et executés en local - **NE PAS COMMITER**


## Basic commands

Create a model
```bash
uv run dbt run -s model_name
```

Execute test for a model
```bash
uv run  dbt test -s model_name --project-dir dbt_ETM 
```

Create a model and execute test for a model
```bash
uv run  dbt build-s model_name  --project-dir dbt_ETM 
```

Create a model with full refresh of data
```bash
uv run  dbt run -f -s model_name --project-dir dbt_ETM 
```



## Run several models

- using + :
    - in front of the model : will execute every dependencies
    - After the model : will execute every followers
    - In front and after the model : execute every dependencies and followers
- using file : To execute DBT models with similar names, you can use a wildcard with the -s "file:expression" argument.
- using tag : To execute DBT models flag with a tag

Lists models what will be executed  if use dbt run
```bash
uv run  dbt list -tag:website --project-dir dbt_ETM 
```

## Documentation and tests

How ? : Writting model_name.yml file information for each model

Here a template for schema.yml file with some tests

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
