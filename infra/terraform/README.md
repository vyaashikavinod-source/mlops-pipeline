# Terraform (9.5–10/10 production pattern)

This provisions:
- Dedicated **VPC** with **public + private subnets** across multiple AZs
- **NAT gateways** (private subnets can reach internet without public IPs)
- **ALB** in public subnets, **ECS Fargate tasks** in private subnets
- **HTTPS endpoint** via **ACM** + **Route53** validation + record
- **Secrets Manager** for app configuration injected into ECS as **secrets**
- Optional: **GitHub Actions OIDC role** (no long-lived AWS keys)

## Quick start
1) Create a `terraform.tfvars` like:
```hcl
domain_name = "yourdomain.com"
subdomain   = "api"

# optional OIDC:
github_org  = "YOUR_GH_ORG"
github_repo = "YOUR_REPO"

# app config (JSON) -> Secrets Manager
app_config_json = jsonencode({
  MLFLOW_TRACKING_URI = "http://YOUR_MLFLOW:5000"
  MONITORING_DB_URL   = "postgresql+psycopg2://user:pass@host:5432/db"
  SLACK_WEBHOOK_URL   = ""
  SMTP_HOST           = "smtp.gmail.com"
  SMTP_PORT           = "587"
  SMTP_USERNAME       = "..."
  SMTP_PASSWORD       = "..."
  SMTP_STARTTLS       = "true"
  ALERT_EMAIL_FROM    = "alerts@yourdomain.com"
  ALERT_EMAIL_TO      = "you@domain.com"
})
```

2) Apply:
```bash
terraform init
terraform apply
```

Outputs:
- `https_url` -> your public HTTPS endpoint.
