variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "dimensions" {
  description = "Embedding dimensionality (768 for text-embedding-004)"
  type        = number
  default     = 768
}

variable "approximate_neighbors_count" {
  type    = number
  default = 50
}

variable "machine_type" {
  description = "Machine type for dedicated serving resources"
  type        = string
  default     = "e2-standard-2"
}

variable "min_replica_count" {
  type    = number
  default = 1
}

variable "max_replica_count" {
  type    = number
  default = 3
}

variable "public_endpoint_enabled" {
  description = "Expose a public endpoint (still requires IAM). Prefer private for production."
  type        = bool
  default     = true
}

variable "contents_delta_uri" {
  description = "Optional GCS URI for bulk index updates (gs://bucket/path/)"
  type        = string
  default     = null
}
