variable "project_id" {
  description = "GCP project ID where the RAG infrastructure will be created"
  type        = string
}

variable "region" {
  description = "Primary region (Vertex AI, Cloud Run, GCS, Memorystore, Eventarc)"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "Primary availability zone for zonal resources (e.g. us-central1-a)"
  type        = string
  default     = ""
}

variable "force_destroy" {
  description = "Allow destroy of non-empty buckets (dev only)"
  type        = bool
  default     = true
}
