variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Primary region for regional resources"
  type        = string
  default     = "us-central1"
}

variable "network_name" {
  description = "Name of the VPC network"
  type        = string
  default     = "rag-vpc"
}

variable "public_ingress_cidr" {
  description = "CIDR for the public / edge subnet"
  type        = string
  default     = "10.10.0.0/24"
}

variable "private_ingestion_cidr" {
  description = "CIDR for the offline ingestion plane subnet"
  type        = string
  default     = "10.10.1.0/24"
}

variable "private_serving_cidr" {
  description = "CIDR for the online query / serving plane subnet"
  type        = string
  default     = "10.10.2.0/24"
}

variable "private_data_cidr" {
  description = "CIDR for the data plane subnet (Redis, private endpoints)"
  type        = string
  default     = "10.10.3.0/24"
}
