# Enterprise MLOps: DVC + Prefect + MLflow Registry + AWS ECS (ALB + HTTPS) + Model Monitoring

This repo upgrades the earlier stack to include:

## ✅ Included
- **DVC** pipelines + reproducible artifacts
- **Prefect v3** orchestration (deployments + schedules)
- **MLflow Tracking + Model Registry** (Postgres backend + MinIO artifact store)
- **FastAPI inference** service
- **AWS production deployment** to **ECR + ECS Fargate** behind an **ALB** with **public HTTPS** (ACM + Route53)
- **Real model monitoring**
  - Prediction + input logging to a **monitoring Postgres**
  - Optional ground-truth feedback via `/feedback`
  - Batch jobs to compute **performance metrics** + **data drift**
  - Drift alerts via **Slack webhook** (optional) + JSON reports

---

## Local run (end-to-end)
### 1) Install
```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt -r requirements-dev.txt
```

### 2) Run pipeline (DVC)
```bash
dvc init
dvc repro
```

### 3) Start services (MLflow Registry + Monitoring DB + Observability)
```bash
docker compose up -d
```

Services:
- MLflow UI: http://127.0.0.1:5000
- MinIO console: http://127.0.0.1:9001  (minioadmin / minioadmin)
- Grafana: http://127.0.0.1:3000 (admin/admin)
- Prometheus: http://127.0.0.1:9090

### 4) Register a model to MLflow Registry (alias = champion)
```bash
# Mac/Linux:
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
# PowerShell:
# $env:MLFLOW_TRACKING_URI="http://127.0.0.1:5000"

python scripts/train_register.py --data data/processed --model-name xgb_churn --alias champion
```

### 5) Run API (loads from registry alias; logs predictions to monitoring DB)
```bash
# Mac/Linux:
export MODEL_URI=models:/xgb_churn@champion
export MONITORING_DB_URL=postgresql+psycopg2://monitor:monitor@127.0.0.1:5433/monitoring

# PowerShell:
# $env:MODEL_URI="models:/xgb_churn@champion"
# $env:MONITORING_DB_URL="postgresql+psycopg2://monitor:monitor@127.0.0.1:5433/monitoring"

uvicorn src.api.main:app --reload
```

- API docs: http://127.0.0.1:8000/docs
- Metrics: http://127.0.0.1:8000/metrics

---

## Model monitoring (performance + drift + alerts)


## Email alerts (SMTP)
This project can send drift alerts via **email** using SMTP (e.g., Gmail App Password, Outlook SMTP, SendGrid SMTP relay).

Set these env vars (see `.env.example`):
- `SMTP_HOST` (e.g., `smtp.gmail.com`)
- `SMTP_PORT` (default `587`)
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_STARTTLS` (`true/false`, default `true`)
- `ALERT_EMAIL_FROM` (from address)
- `ALERT_EMAIL_TO` (comma-separated recipients)

Then drift alerts will send email when you run:
```bash
python scripts/drift_alert.py --drift reports/drift_live.json --threshold 0.25 --email
```

### 1) Send predictions (they will be logged)
POST `/predict` returns `prediction_id`.

### 2) Provide ground truth later
POST `/feedback` with:
- `prediction_id`
- `actual_churn` (0/1)

### 3) Compute monitoring reports
```bash
python scripts/compute_performance.py --db "$MONITORING_DB_URL" --out reports/perf.json
python scripts/compute_drift.py --db "$MONITORING_DB_URL" --baseline data/processed/train.parquet --out reports/drift_live.json
python scripts/drift_alert.py --drift reports/drift_live.json --threshold 0.25
```

### 4) Drift alerts to Slack (optional)
Set env:
- `SLACK_WEBHOOK_URL`

---

## AWS production deploy (ALB + HTTPS)
This repo includes a **real ALB + HTTPS** Terraform module in `infra/terraform`.

You need:
- A domain in **Route53** (e.g., `yourdomain.com`)
- An ACM certificate (Terraform creates + validates it via Route53)

### Provision infra
```bash
cd infra/terraform
terraform init
terraform apply
```

Terraform outputs include:
- `alb_dns_name`
- `https_url`
- `ecr_repository_url`
- ECS cluster/service names

### CI/CD deploy (GitHub Actions)
- `.github/workflows/deploy_aws_ecs.yml` builds Docker, pushes to ECR, updates ECS service.
- Follow `docs/aws_deploy.md` to set GitHub secrets.


## Model KPI Dashboard
Grafana auto-provisions a **Model KPI Dashboard** backed by the monitoring Postgres (`daily_metrics`, `segment_metrics`). Open Grafana at http://127.0.0.1:3000.


## Automated retraining triggers
The daily monitoring flow can automatically retrain and promote a new model when:
- drift exceeds threshold (PSI)
- or live ROC-AUC falls below threshold (requires feedback labels)
It registers a new MLflow model version and promotes it to alias `champion` when it beats the current champion.


## GitHub OIDC + Secrets Manager
For AWS deploy, Terraform can create a GitHub OIDC role (no long-lived AWS keys) and inject app config via Secrets Manager into ECS task secrets.
See `docs/github_oidc.md` and `infra/terraform/`.
