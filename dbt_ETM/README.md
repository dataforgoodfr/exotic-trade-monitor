# Welcome to Exotic Trade Monitor dbt project!

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
