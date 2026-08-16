variable "project_id" {
  description = "GCP project ID for production"
  type        = string
}

variable "region" {
  description = "Primary region"
  type        = string
  default     = "us-central1"
}
