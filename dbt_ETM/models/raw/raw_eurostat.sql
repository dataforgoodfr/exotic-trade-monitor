-- raw_eurostat

SELECT
--    "Fréquence" AS frequence,
--    "REPORTER" AS reporter,
    "PARTNER" AS partner,
    "PRODUCT" AS product,
    "FLOW" AS flow,
    --    "INDICATORS" AS indicators,
    "TIME_PERIOD" AS time_period,
    "value" AS valeur_en_euros
--    "product_query" AS product_query,
--    "flow_query" AS flow_query
FROM {{ source('src_eurostat', 'eurostat_files') }}
