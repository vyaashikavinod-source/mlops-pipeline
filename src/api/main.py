from __future__ import annotations

import os
from typing import Any, Dict, Optional

import mlflow
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from prometheus_fastapi_instrumentator import Instrumentator

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.monitoring.db import add_feedback, init_db, insert_prediction


def setup_otel(app_name: str = "mlops-api") -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4318/v1/traces")
    resource = Resource.create({"service.name": app_name})
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)


def load_model():
    model_uri = os.getenv("MODEL_URI", "")
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "")
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)
    if model_uri:
        return mlflow.pyfunc.load_model(model_uri), model_uri
    import joblib
    return joblib.load("models/model.joblib"), "local:models/model.joblib"


def resolve_model_version(model_uri: str) -> str:
    # best-effort: if registry URI models:/name@alias, resolve alias -> version
    try:
        if model_uri.startswith("models:/") and "@" in model_uri:
            name_alias = model_uri[len("models:/") :]
            name, alias = name_alias.split("@", 1)
            from mlflow import MlflowClient
            client = MlflowClient()
            m = client.get_registered_model(name)
            v = m.aliases.get(alias)
            return str(v) if v is not None else ""
    except Exception:
        return ""
    return ""


app = FastAPI(title="Enterprise MLOps API", version="2.0.0")

setup_otel("enterprise-mlops-api")
FastAPIInstrumentor.instrument_app(app)
Instrumentator().instrument(app).expose(app)


class PredictRequest(BaseModel):
    tenure_months: float = Field(..., ge=0)
    monthly_charges: float = Field(..., ge=0)
    total_charges: float = Field(..., ge=0)
    tickets_90d: float = Field(..., ge=0)
    contract_type: str
    payment_method: str
    internet_service: str
    region: str


class PredictResponse(BaseModel):
    prediction_id: Optional[int] = None
    churn_probability: float
    churn_label: int
    model_uri: str = ""
    model_version: str = ""


class FeedbackRequest(BaseModel):
    prediction_id: int
    actual_churn: int = Field(..., ge=0, le=1)


@app.on_event("startup")
def on_startup():
    db_url = os.getenv("MONITORING_DB_URL", "")
    if db_url:
        init_db(db_url)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    model, model_uri = load_model()
    model_version = resolve_model_version(model_uri)

    X: list[Dict[str, Any]] = [req.model_dump()]
    try:
        import pandas as pd
        df = pd.DataFrame(X)
        out = model.predict(df)
        proba = float(out[0]) if hasattr(out, "__len__") else float(out)
    except Exception:
        proba = float(model.predict_proba(X)[0, 1])

    label = int(proba >= 0.5)

    pred_id = None
    db_url = os.getenv("MONITORING_DB_URL", "")
    if db_url:
        pred_id = insert_prediction(
            db_url=db_url,
            request_obj=req.model_dump(),
            proba=proba,
            label=label,
            model_uri=model_uri,
            model_version=model_version,
        )

    return PredictResponse(
        prediction_id=pred_id,
        churn_probability=proba,
        churn_label=label,
        model_uri=model_uri,
        model_version=model_version,
    )


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    db_url = os.getenv("MONITORING_DB_URL", "")
    if not db_url:
        raise HTTPException(status_code=400, detail="MONITORING_DB_URL not configured")
    try:
        add_feedback(db_url, req.prediction_id, req.actual_churn)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"status": "ok"}
