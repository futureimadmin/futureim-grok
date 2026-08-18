/**
 * RAG System VPC — four subnets matching architectural planes:
 *  public-ingress, private-ingestion, private-serving, private-data
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
  description             = "VPC for production RAG system – plane isolation"
}

resource "google_compute_subnetwork" "public_ingress" {
  name                     = "${var.network_name}-public-ingress"
  project                  = var.project_id
  region                   = var.region
  network                  = google_compute_network.rag_vpc.id
  ip_cidr_range            = var.public_ingress_cidr
  private_ip_google_access = true
  description              = "Edge tier – Cloud Run ingress, LB, API Gateway"

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
  description              = "Offline ingestion plane – chunkers, embedders"

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
  description              = "Online query plane – orchestrator, retrieval, LLM"

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
  description              = "Data plane – Redis, private service endpoints"

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

resource "google_compute_router" "rag_router" {
  name    = "${var.network_name}-router"
  project = var.project_id
  region  = var.region
  network = google_compute_network.rag_vpc.id
}

resource "google_compute_router_nat" "rag_nat" {
  name                               = "${var.network_name}-nat"
  project                            = var.project_id
  region                             = var.region
  router                             = google_compute_router.rag_router.name
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

resource "google_compute_firewall" "deny_all_ingress" {
  name      = "${var.network_name}-deny-all-ingress"
  project   = var.project_id
  network   = google_compute_network.rag_vpc.name
  direction = "INGRESS"
  priority  = 65534

  deny {
    protocol = "all"
  }

  source_ranges = ["0.0.0.0/0"]
  description   = "Default deny; allow rules must be explicit"
}

resource "google_compute_firewall" "allow_internal" {
  name    = "${var.network_name}-allow-internal"
  project = var.project_id
  network = google_compute_network.rag_vpc.name

  allow {
    protocol = "tcp"
  }
  allow {
    protocol = "udp"
  }
  allow {
    protocol = "icmp"
  }

  source_ranges = [
    var.public_ingress_cidr,
    var.private_ingestion_cidr,
    var.private_serving_cidr,
    var.private_data_cidr,
  ]
  description = "East-west traffic within RAG VPC"
}

resource "google_compute_firewall" "allow_iap_ssh" {
  name    = "${var.network_name}-allow-iap-ssh"
  project = var.project_id
  network = google_compute_network.rag_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["rag-ops"]
  description   = "IAP SSH for operational break-glass access only"
}
