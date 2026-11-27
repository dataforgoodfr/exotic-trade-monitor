DUCKDB_CLI_VERSION ?= 1.5.6

.PHONY: duckdb-ui
duckdb-ui:
	@test -f dbt_ETM/dev.duckdb || { echo 'Base introuvable. Après avoir téléchargé les données sources, lancez « uv run dbt build » depuis dbt_ETM.' >&2; exit 1; }
	uvx --from "duckdb-cli==$(DUCKDB_CLI_VERSION)" duckdb -bail \
		-cmd "ATTACH 'dbt_ETM/dev.duckdb' AS etm (READ_ONLY)" -ui
