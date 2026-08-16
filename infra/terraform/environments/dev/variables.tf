variable "project_id" {
  description = "GCP project ID where the RAG infrastructure will be created"
  type        = string
}

variable "region" {
  description = "Primary region"
  type        = string
  default     = "us-central1"
}
