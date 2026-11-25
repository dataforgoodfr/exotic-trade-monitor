.DEFAULT_GOAL := help
.PHONY: help install install-ingestion ingest dbt-deps dbt-run dbt-test dbt-build dbt-docs dbt-check lint jupyter marimo

SOURCES ?=

help: ## Show available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies locally
	uv sync

install-ingestion: ## Install only ingestion package dependencies
	uv sync --package ingestion --no-default-groups

ingest: ## Run data ingestion (all sources, or e.g. make ingest SOURCES=cites)
	uv run ingest $(SOURCES)

dbt-deps: ## Install dbt packages
	cd dbt_ETM && uv run dbt deps

dbt-run: ## Run dbt models
	cd dbt_ETM && uv run dbt run

dbt-test: ## Run dbt tests
	cd dbt_ETM && uv run dbt test

dbt-build: ## Build and test all dbt models
	cd dbt_ETM && uv run dbt build

dbt-docs: ## Generate dbt documentation
	cd dbt_ETM && uv run dbt docs generate

dbt-check: ## Run manual dbt-checkpoint pre-commit hooks
	uv run pre-commit run --hook-stage manual --all-files

lint: ## Run pre-commit linters on all files
	uv run pre-commit run --all-files

jupyter: ## Launch Jupyter Notebook
	uv run jupyter notebook

marimo: ## Launch Marimo notebook editor
	uv run marimo edit
