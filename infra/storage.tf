resource "clevercloud_cellar" "storage" {
  name   = "storage-test"
  region = "par"
  lifecycle {
    prevent_destroy = true
  }
}

resource "clevercloud_cellar_bucket" "database_bucket" {
  cellar_id = clevercloud_cellar.storage.id
  id        = "duckdb"
}

resource "clevercloud_cellar_bucket" "extract_bucket" {
  cellar_id = clevercloud_cellar.storage.id
  id        = "extract"
}
