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
  type    = string
  default = "e2-standard-2"
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
  type    = bool
  default = true
}

variable "contents_delta_uri" {
  description = "Optional GCS URI for bulk index updates"
  type        = string
  default     = null
}
