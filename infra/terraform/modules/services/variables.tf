variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "network_id" {
  description = "Self-link or ID of the VPC that Redis and private services will attach to"
  type        = string
}

variable "redis_memory_gb" {
  type    = number
  default = 1
}

variable "force_destroy" {
  description = "Allow destruction of buckets with objects (dev only)"
  type        = bool
  default     = false
}
