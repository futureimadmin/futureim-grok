/**
 * Production environment root module for the RAG system.
 */

terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.30"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 5.30"
    }
  }

  # Configure remote state via:
  #   terraform init -backend-config=backend.hcl
  backend "gcs" {}
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

data "google_project" "current" {
  project_id = var.project_id
}

module "vpc" {
  source = "../../modules/vpc"

  project_id             = var.project_id
  region                 = var.region
  network_name           = "rag-vpc"
  public_ingress_cidr    = "10.10.0.0/24"
  private_ingestion_cidr = "10.10.1.0/24"
  private_serving_cidr   = "10.10.2.0/24"
  private_data_cidr      = "10.10.3.0/24"
}

module "services" {
  source = "../../modules/services"

  project_id      = var.project_id
  region          = var.region
  network_id      = module.vpc.network_id
  redis_memory_gb = 5
  force_destroy   = false
}

module "iam" {
  source = "../../modules/iam"

  project_id     = var.project_id
  project_number = data.google_project.current.number
}

resource "google_vpc_access_connector" "rag_connector" {
  name          = "rag-connector"
  project       = var.project_id
  region        = var.region
  network       = module.vpc.network_name
  ip_cidr_range = "10.8.0.0/28"
  min_instances = 2
  max_instances = 10

  depends_on = [module.vpc]
}

module "eventarc" {
  source = "../../modules/eventarc"

  project_id         = var.project_id
  region             = var.region
  documents_bucket   = module.services.documents_bucket_name
  processed_bucket   = module.services.processed_bucket_name
  ingestion_sa_email = module.iam.ingestion_sa_email
  eventarc_sa_email  = module.iam.eventarc_sa_email
  vpc_connector_id   = google_vpc_access_connector.rag_connector.id
  dlq_topic          = "rag-ingestion-dlq"
  ingestion_image    = "${module.services.artifact_registry_url}/ingestion:latest"

  depends_on = [
    module.services,
    module.iam,
    google_vpc_access_connector.rag_connector,
  ]
}

module "vector_search" {
  source = "../../modules/vector_search"

  project_id                  = var.project_id
  region                      = var.region
  dimensions                  = 768
  approximate_neighbors_count = 50
  machine_type                = "e2-standard-4"
  min_replica_count           = 2
  max_replica_count           = 10
  public_endpoint_enabled     = false
}
