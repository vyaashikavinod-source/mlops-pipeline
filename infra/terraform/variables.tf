variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "enterprise-mlops"
}

variable "ecr_repository" {
  type    = string
  default = "enterprise-mlops-api"
}

variable "ecs_cluster" {
  type    = string
  default = "enterprise-mlops-cluster"
}

variable "ecs_service" {
  type    = string
  default = "enterprise-mlops-service"
}

variable "domain_name" {
  type        = string
  description = "Route53 hosted zone domain, e.g., yourdomain.com"
}

variable "subdomain" {
  type        = string
  default     = "api"
  description = "Subdomain for the API endpoint"
}

variable "container_port" {
  type    = number
  default = 8000
}

# VPC
variable "vpc_cidr" {
  type    = string
  default = "10.50.0.0/16"
}

variable "az_count" {
  type    = number
  default = 2
}

# GitHub OIDC
variable "github_org" {
  type        = string
  description = "GitHub org/user name, e.g., vyaashikavinod-source"
  default     = ""
}

variable "github_repo" {
  type        = string
  description = "GitHub repo name, e.g., media-scout"
  default     = ""
}

variable "github_branch" {
  type    = string
  default = "main"
}

# Secrets Manager (app config JSON)
variable "app_config_json" {
  type        = string
  description = "JSON string stored in Secrets Manager for ECS task secrets (MLFLOW_TRACKING_URI, MONITORING_DB_URL, SMTP creds, etc.)"
  default     = "{}"
}
