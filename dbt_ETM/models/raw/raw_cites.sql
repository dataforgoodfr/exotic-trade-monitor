-- raw_cites

SELECT
    "Id" AS id,
    "Year" AS "year", -- to rename to not use key_word ?
    "Appendix" AS appendix,
    "Taxon" AS taxon,
    "Class" AS "class", -- to rename to not use key_word ?
    "Order" AS "order", -- to rename to not use key_word ?
    "Family" AS "family",-- to rename to not use key_word ?
    "Genus" AS genus,
    "Term" AS term,
    "Quantity" AS quantity,
    "Unit" AS unit,
    "Importer" AS importer,
    "Exporter" AS exporter,
    "Origin" AS origin,
    "Purpose" AS purpose,
    "Source" AS "source", -- to rename to not use key_word ?
    "Reporter.type" AS reporter_type,
    "Import.permit.RandomID" AS import_permit_random_id,
    "Export.permit.RandomID" AS export_permit_random_id,
    "Origin.permit.RandomID" AS origin_permit_random_id,
    "Ifs.permit.RandomID" AS ifs_permit_random_id
FROM {{ source('src_cites', 'trade_files') }}
WHERE
    purpose = 'T'
    AND appendix != 'N'
