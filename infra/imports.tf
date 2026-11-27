# metabase_app
import {
  to = clevercloud_java_jar.metabase_app
  id = "app_261ae440-b203-4f58-9831-60ebf31a82dd"
}

# metabase_config_pg
import {
  to = clevercloud_postgresql.metabase_config_pg
  id = "postgresql_aa6563d0-2dc6-4e77-a4ef-3fed749bb55b"
}

# storage-test
import {
  to = clevercloud_cellar.storage
  id = "cellar_2a836064-0dd7-4fc0-88ea-d727596691fc"
}

# database_bucket
import {
  to = clevercloud_cellar_bucket.database_bucket
  id = "cellar_2a836064-0dd7-4fc0-88ea-d727596691fc/duckdb"
}

# extract_bucket
import {
  to = clevercloud_cellar_bucket.extract_bucket
  id = "cellar_2a836064-0dd7-4fc0-88ea-d727596691fc/extract"
}
