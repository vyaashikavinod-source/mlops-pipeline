# GitHub Actions OIDC (no long-lived AWS keys)

This repo supports deploying to AWS using **GitHub OIDC**.

## What you get
- No `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` in GitHub Secrets.
- GitHub Actions assumes an AWS role at runtime via OIDC.

## Setup steps
1. In `infra/terraform`, set:
   - `github_org`
   - `github_repo`
   - `github_branch` (default `main`)

2. Apply Terraform:
```bash
cd infra/terraform
terraform init
terraform apply
```

3. In GitHub Secrets set:
- `AWS_REGION`
- `AWS_ROLE_TO_ASSUME` = Terraform output `github_actions_role_arn`
- `ECR_REPOSITORY` = Terraform output `ecr_repository_name`
- `ECS_CLUSTER` = Terraform output `ecs_cluster_name`
- `ECS_SERVICE` = Terraform output `ecs_service_name`

Then push to `main` → deploy workflow uses OIDC.
