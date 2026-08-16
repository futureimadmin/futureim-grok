/**
 * Development environment root module for the RAG system.
 *
 * Deploys:
 *  - Custom VPC with four subnets (public-ingress, private-ingestion,
 *    private-serving, private-data) that enforce the architectural
 *    boundaries described in the RAG Architecture document.
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
# Optional: Serverless VPC Access connector so Cloud Run can reach private Redis
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
