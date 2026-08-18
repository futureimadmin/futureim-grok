/**
 * Vertex AI Vector Search (Matching Engine) for the RAG system.
 * Index (STREAM_UPDATE) + Endpoint + Deployed Index.
 * Dimensions must match embedding model (text-embedding-004 → 768).
 */

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.30"
    }
  }
}

resource "google_vertex_ai_index" "rag" {
  project      = var.project_id
  region       = var.region
  display_name = "rag-index"
  description  = "Production RAG vector index – stream updates from ingestion plane"

  metadata {
    contents_delta_uri = var.contents_delta_uri
    config {
      dimensions                  = var.dimensions
      approximate_neighbors_count = var.approximate_neighbors_count
      distance_measure_type       = "DOT_PRODUCT_DISTANCE"
      algorithm_config {
        tree_ah_config {
          leaf_node_embedding_count    = 1000
          leaf_nodes_to_search_percent = 10
        }
      }
    }
  }

  index_update_method = "STREAM_UPDATE"

  labels = {
    component = "rag-vector-store"
    plane     = "data"
  }
}

resource "google_vertex_ai_index_endpoint" "rag" {
  project                 = var.project_id
  region                  = var.region
  display_name            = "rag-index-endpoint"
  description             = "Serving endpoint for RAG ANN queries"
  public_endpoint_enabled = var.public_endpoint_enabled

  labels = {
    component = "rag-vector-store"
    plane     = "data"
  }
}

resource "google_vertex_ai_index_endpoint_deployed_index" "rag" {
  index_endpoint    = google_vertex_ai_index_endpoint.rag.id
  index             = google_vertex_ai_index.rag.id
  deployed_index_id = "rag_deployed"
  display_name      = "rag-deployed-index"

  dedicated_resources {
    machine_spec {
      machine_type = var.machine_type
    }
    min_replica_count = var.min_replica_count
    max_replica_count = var.max_replica_count
  }

  enable_access_logging = true
}
