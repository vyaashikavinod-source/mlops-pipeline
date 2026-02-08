# 10/10 Checklist (what this repo demonstrates)

## Cloud & security
- ECS tasks run in **private subnets** (no public IP) behind ALB
- Egress via **NAT**, inbound only via ALB SG
- Secrets injected via **AWS Secrets Manager** into ECS task secrets
- CI/CD uses **GitHub OIDC** (no long-lived AWS keys)

## ML platform & lifecycle
- MLflow tracking + registry (champion/challenger aliasing)
- DVC reproducible training pipeline
- Orchestration via Prefect (scheduled monitoring + retrain)

## Monitoring (real, model-level)
- Input + prediction logging
- Ground truth feedback endpoint
- KPIs: ROC-AUC, PR-AUC, Brier score, ECE calibration
- Drift: PSI
- Segment/cohort slicing metrics
- Alerts: Slack + Email
- Grafana dashboard (model KPIs) backed by monitoring Postgres
