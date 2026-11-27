terraform {
  required_providers {
    clevercloud = {
      source  = "CleverCloud/clevercloud"
      version = "~> 3.0"
    }
  }
  backend "s3" {
    bucket = "exotic-trade-monitor-tf-state"
    key    = "prod.tfstate"
    region = "par"

    endpoints = { s3 = "https://cellar-c2.services.clever-cloud.com" }

    use_path_style              = true
    skip_region_validation      = true
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_requesting_account_id  = true
  }
}

provider "clevercloud" {}
