/**
 * Development environment root module for the RAG system.
 *
 * Deploys:
 *  - Custom VPC with four subnets (public-ingress, private-ingestion,
 *    private-serving, private-data) that enforce the architectural
 *    boundaries described in the RAG Architecture document.
 *  - Required APIs, GCS buckets, Memorystore Redis, Pub/Sub, Artifact Registry
 *  - Least-privilege service accounts for each plane
 *  - Eventarc trigger (GCS object finalized → Cloud Run ingestion)
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

  # Uncomment and configure for remote state in production
  # backend "gcs" {
  #   bucket = "your-tf-state-bucket"
  #   prefix = "rag/dev"
  # }
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

# -----------------------------------------------------------------------------
# VPC – clear network boundaries
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# Shared services (GCS, Redis, Pub/Sub, Artifact Registry, private services)
# -----------------------------------------------------------------------------

module "services" {
  source = "../../modules/services"

  project_id      = var.project_id
  region          = var.region
  network_id      = module.vpc.network_id
  redis_memory_gb = 1
  force_destroy   = true # safe for dev
}

# -----------------------------------------------------------------------------
# IAM – plane-specific service accounts
# -----------------------------------------------------------------------------

module "iam" {
  source = "../../modules/iam"

  project_id     = var.project_id
  project_number = data.google_project.current.number
}

# -----------------------------------------------------------------------------
# Serverless VPC Access connector so Cloud Run can reach private Redis / data plane
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# Eventarc → Cloud Run ingestion pipeline
# -----------------------------------------------------------------------------

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
  # After first image build, set:
  # ingestion_image = "${module.services.artifact_registry_url}/ingestion:latest"
  ingestion_image    = "us-docker.pkg.dev/cloudrun/container/hello"

  depends_on = [
    module.services,
    module.iam,
    google_vpc_access_connector.rag_connector,
  ]
}
