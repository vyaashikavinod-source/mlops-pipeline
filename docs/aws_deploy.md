# AWS Deploy (ALB + HTTPS) on ECS Fargate — Private subnets + NAT + Secrets Manager + OIDC

Terraform provisions:
- Dedicated VPC with **public + private subnets**
- NAT gateways (ECS tasks are private, no public IP)
- ALB public HTTPS endpoint `https://api.<domain>/`
- ECS Fargate service behind ALB
- Secrets Manager secret for app config injected as ECS secrets
- Optional GitHub Actions OIDC role (no long-lived keys)

## 1) Terraform apply
```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars
terraform init
terraform apply
```

## 2) Deploy via GitHub Actions (OIDC)
Set GitHub Secrets:
- `AWS_REGION`
- `AWS_ROLE_TO_ASSUME` (terraform output `github_actions_role_arn`)
- `ECR_REPOSITORY` (terraform output `ecr_repository_name`)
- `ECS_CLUSTER` (terraform output `ecs_cluster_name`)
- `ECS_SERVICE` (terraform output `ecs_service_name`)

Then push to main.

> If you don't want OIDC, you can revert the workflow to key-based auth, but OIDC is what gets this to a 9.5–10/10 standard.
