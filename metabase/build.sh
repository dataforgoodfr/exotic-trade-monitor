#!/bin/sh

. ./metabase/versions.env
curl -fsSL -o metabase.jar https://downloads.metabase.com/v${METABASE}/metabase.jar && mkdir -p plugins && curl -fsSL -o plugins/duckdb.metabase-driver.jar https://github.com/motherduckdb/metabase_duckdb_driver/releases/download/${DUCKDB_DRIVER}/duckdb.metabase-driver.jar
