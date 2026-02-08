output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}
output "ecr_repository_name" {
  value = aws_ecr_repository.app.name
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "ecs_service_name" {
  value = aws_ecs_service.app.name
}

output "alb_dns_name" {
  value = aws_lb.alb.dns_name
}

output "https_url" {
  value = "https://${var.subdomain}.${var.domain_name}"
}

output "secrets_manager_app_config_arn" {
  value = aws_secretsmanager_secret.app_config.arn
}

output "github_actions_role_arn" {
  value = length(aws_iam_role.github_actions) > 0 ? aws_iam_role.github_actions[0].arn : null
}
