/**
 * Development environment root module for the RAG system.
 *
 * Deploys:
 *  - Custom VPC with four subnets (public-ingress, private-ingestion,
 *    private-serving, private-data)
 *  - Required APIs, GCS buckets, Memorystore Redis, Pub/Sub, Artifact Registry
 *  - Least-privilege service accounts for each plane
 *
 * Usage:
 *   export TF_VAR_project_id=your-gcp-project
 *   terraform init
 *   terraform plan
 *   terraform apply
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
  redis_memory_gb = 1
  force_destroy   = true
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
  max_instances = 3

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
  ingestion_image    = "us-docker.pkg.dev/cloudrun/container/hello"

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
  machine_type                = "e2-standard-2"
  min_replica_count           = 1
  max_replica_count           = 3
  public_endpoint_enabled     = true
}
