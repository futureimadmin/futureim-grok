variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "documents_bucket" {
  description = "Name of the GCS documents landing bucket"
  type        = string
}

variable "processed_bucket" {
  description = "Name of the processed / archive bucket"
  type        = string
}

variable "ingestion_sa_email" {
  description = "Service account used by the Cloud Run ingestion service"
  type        = string
}

variable "eventarc_sa_email" {
  description = "Service account used by Eventarc to invoke Cloud Run"
  type        = string
}

variable "vpc_connector_id" {
  description = "Serverless VPC Access connector ID/self-link"
  type        = string
}

variable "ingestion_image" {
  description = "Container image for the ingestion worker"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello" # replace after first build
}

variable "dlq_topic" {
  description = "Pub/Sub topic name for dead-letter"
  type        = string
  default     = "rag-ingestion-dlq"
}

variable "max_instances" {
  type    = number
  default = 20
}

variable "embedding_model" {
  type    = string
  default = "text-embedding-004"
}

variable "vector_index_id" {
  type    = string
  default = ""
}

variable "vector_endpoint_id" {
  type    = string
  default = ""
}

variable "apis_dependency" {
  description = "Optional dependency on API enablement"
  type        = any
  default     = null
}
