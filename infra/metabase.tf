resource "clevercloud_java_jar" "metabase_app" {
  biggest_flavor = "M"
  dependencies   = ["cellar_2a836064-0dd7-4fc0-88ea-d727596691fc", "postgresql_aa6563d0-2dc6-4e77-a4ef-3fed749bb55b"]
  description    = "Metabase avec connecteur DuckDb"
  environment = {
    JAVA_TOOL_OPTIONS        = "-Xmx768m"
    MB_JETTY_HOST            = "0.0.0.0"
    MB_JETTY_PORT            = "8080"
    MB_DB_TYPE               = "postgres"
    MB_DB_DBNAME             = clevercloud_postgresql.metabase_config_pg.database
    MB_DB_HOST               = clevercloud_postgresql.metabase_config_pg.host
    MB_DB_PASS               = clevercloud_postgresql.metabase_config_pg.password
    MB_DB_PORT               = clevercloud_postgresql.metabase_config_pg.port
    MB_DB_USER               = clevercloud_postgresql.metabase_config_pg.user
    MB_SESSION_SECRET_KEY    = var.mb_session_secret
    MB_ENCRYPTION_SECRET_KEY = var.mb_encryption_secret
  }
  jar_path           = "./metabase.jar"
  java_version       = "25"
  max_instance_count = 1
  min_instance_count = 1
  name               = "metabase-app-test"
  redirect_https     = true
  region             = "par"
  smallest_flavor    = "M"
  sticky_sessions    = false
  vhosts = [
    {
      fqdn       = "app-261ae440-b203-4f58-9831-60ebf31a82dd.cleverapps.io"
      path_begin = "/"
    },
  ]
  hooks {
    pre_build = "metabase/build.sh"
    pre_run   = "metabase/run.sh"
  }
}

resource "clevercloud_postgresql" "metabase_config_pg" {
  backup           = true
  direct_host_only = false
  encryption       = false
  locale           = "en_GB"
  name             = "metabase-config-pg-test"
  plan             = "xxs_sml"
  region           = "par"
  version          = "18"
  lifecycle {
    prevent_destroy = true
  }
}
