#!/bin/sh

mkdir -p data && curl -fsSL --aws-sigv4 'aws:amz:par:s3' --user "$CELLAR_ADDON_KEY_ID:$CELLAR_ADDON_KEY_SECRET" -o data/dev.duckdb "https://$CELLAR_ADDON_HOST/duckdb/dev.duckdb"
