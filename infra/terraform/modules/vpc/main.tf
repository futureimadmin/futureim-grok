/**
 * RAG System VPC Module
 * Creates a custom VPC with clear network boundaries matching the
 * three architectural layers described in the RAG Architecture guide:
 *
 *  - public-ingress   : API Gateway / Cloud Run frontend (user-facing)
 *  - private-ingestion: Offline write pipeline (Chunker → Embedder)
 *  - private-serving  : Online query path (Orchestrator → Retrieval → LLM)
 *  - private-data     : Shared state (Memorystore Redis, private endpoints)
 *
 * All subnets have Private Google Access enabled so that Cloud Run,
 * Vertex AI, GCS, etc. can be reached without public IPs on the workloads.
 */

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.30"
    }
  }
}

resource "google_compute_network" "rag_vpc" {
  name                    = var.network_name
  project                 = var.project_id
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
  description             = "VPC for production RAG system – clear boundaries between ingestion, serving and data planes"
}

# -----------------------------------------------------------------------------
# Subnets – one per architectural boundary
# -----------------------------------------------------------------------------

resource "google_compute_subnetwork" "public_ingress" {
  name                     = "${var.network_name}-public-ingress"
  project                  = var.project_id
  region                   = var.region
  network                  = google_compute_network.rag_vpc.id
  ip_cidr_range            = var.public_ingress_cidr
  private_ip_google_access = true
  description              = "Public / edge tier – Cloud Run ingress, Load Balancer, API Gateway"

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

resource "google_compute_subnetwork" "private_ingestion" {
  name                     = "${var.network_name}-private-ingestion"
  project                  = var.project_id
  region                   = var.region
  network                  = google_compute_network.rag_vpc.id
  ip_cidr_range            = var.private_ingestion_cidr
  private_ip_google_access = true
  description              = "Offline ingestion plane – document processors, chunkers, embedders (never serves user traffic)"

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

resource "google_compute_subnetwork" "private_serving" {
  name                     = "${var.network_name}-private-serving"
  project                  = var.project_id
  region                   = var.region
  network                  = google_compute_network.rag_vpc.id
  ip_cidr_range            = var.private_serving_cidr
  private_ip_google_access = true
  description              = "Online query path – orchestrator, retriever, reranker, prompt builder, LLM clients"

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

resource "google_compute_subnetwork" "private_data" {
  name                     = "${var.network_name}-private-data"
  project                  = var.project_id
  region                   = var.region
  network                  = google_compute_network.rag_vpc.id
  ip_cidr_range            = var.private_data_cidr
  private_ip_google_access = true
  description              = "Data plane – Memorystore Redis (semantic cache), private service connect endpoints, any self-managed stores"

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# -----------------------------------------------------------------------------
# Cloud Router + Cloud NAT (for private subnets that need controlled egress)
# -----------------------------------------------------------------------------

resource "google_compute_router" "rag_router" {
  name    = "${var.network_name}-router"
  project = var.project_id
  region  = var.region
  network = google_compute_network.rag_vpc.id
}

resource "google_compute_router_nat" "rag_nat" {
  name                               = "${var.network_name}-nat"
  project                            = var.project_id
  router                             = google_compute_router.rag_router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"

  subnetwork {
    name                    = google_compute_subnetwork.private_ingestion.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }
  subnetwork {
    name                    = google_compute_subnetwork.private_serving.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }
  subnetwork {
    name                    = google_compute_subnetwork.private_data.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# -----------------------------------------------------------------------------
# Firewall – default deny + explicit allows that enforce architectural boundaries
# -----------------------------------------------------------------------------

# Allow internal health checks / Google LB probes
resource "google_compute_firewall" "allow_health_checks" {
  name    = "${var.network_name}-allow-health-checks"
  project = var.project_id
  network = google_compute_network.rag_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["80", "443", "8080", "8000"]
  }

  source_ranges = [
    "35.191.0.0/16", # Google health check ranges
    "130.211.0.0/22",
  ]
  target_tags = ["rag-serving", "rag-ingress"]
  description = "Allow Google health-check probes to serving and ingress tiers"
}

# Ingestion plane can talk to data plane (Redis, private endpoints) and to Google APIs
resource "google_compute_firewall" "ingestion_to_data" {
  name    = "${var.network_name}-ingestion-to-data"
  project = var.project_id
  network = google_compute_network.rag_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["6379", "5432", "443"] # Redis, Postgres-style, HTTPS
  }

  source_tags = ["rag-ingestion"]
  target_tags = ["rag-data"]
  description = "Ingestion workers may reach semantic cache / doc store only"
}

# Serving plane can talk to data plane
resource "google_compute_firewall" "serving_to_data" {
  name    = "${var.network_name}-serving-to-data"
  project = var.project_id
  network = google_compute_network.rag_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["6379", "5432", "443"]
  }

  source_tags = ["rag-serving"]
  target_tags = ["rag-data"]
  description = "Query path may reach semantic cache / doc store"
}

# Deny direct communication between ingestion and serving (they only share the vector store)
resource "google_compute_firewall" "deny_ingestion_serving" {
  name     = "${var.network_name}-deny-ingestion-serving"
  project  = var.project_id
  network  = google_compute_network.rag_vpc.name
  priority = 1000

  deny {
    protocol = "all"
  }

  source_tags = ["rag-ingestion"]
  target_tags = ["rag-serving"]
  description = "Architectural boundary: ingestion and query path never communicate directly"
}

resource "google_compute_firewall" "deny_serving_ingestion" {
  name     = "${var.network_name}-deny-serving-ingestion"
  project  = var.project_id
  network  = google_compute_network.rag_vpc.name
  priority = 1000

  deny {
    protocol = "all"
  }

  source_tags = ["rag-serving"]
  target_tags = ["rag-ingestion"]
  description = "Architectural boundary: query path cannot reach ingestion workers"
}

# Allow IAP / SSH for operational access (optional, restricted)
resource "google_compute_firewall" "allow_iap_ssh" {
  name    = "${var.network_name}-allow-iap-ssh"
  project = var.project_id
  network = google_compute_network.rag_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["35.235.240.0/20"] # IAP
  target_tags   = ["rag-ops"]
  description   = "IAP SSH for operational break-glass access only"
}

# Egress is controlled via Cloud NAT; no broad egress firewall needed when using private Google access.
