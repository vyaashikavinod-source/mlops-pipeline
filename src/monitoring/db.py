from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    request_json: Mapped[str] = mapped_column(Text)
    churn_probability: Mapped[float] = mapped_column(Float)
    churn_label: Mapped[int] = mapped_column(Integer)

    model_uri: Mapped[str] = mapped_column(Text, default="")
    model_version: Mapped[str] = mapped_column(Text, default="")

    has_feedback: Mapped[bool] = mapped_column(Boolean, default=False)
    actual_churn: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class DailyMetric(Base):
    __tablename__ = "daily_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    n_predictions: Mapped[int] = mapped_column(Integer)
    n_feedback: Mapped[int] = mapped_column(Integer)

    roc_auc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pr_auc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    brier: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ece: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    worst_feature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    worst_psi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class SegmentMetric(Base):
    __tablename__ = "segment_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    segment_type: Mapped[str] = mapped_column(Text)  # e.g. "region"
    segment_value: Mapped[str] = mapped_column(Text) # e.g. "NE"
    n: Mapped[int] = mapped_column(Integer)

    roc_auc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pr_auc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    brier: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


def init_db(db_url: str) -> None:
    engine = create_engine(db_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)


def get_engine(db_url: str):
    return create_engine(db_url, pool_pre_ping=True)


def insert_prediction(
    db_url: str,
    request_obj: dict[str, Any],
    proba: float,
    label: int,
    model_uri: str,
    model_version: str,
) -> int:
    engine = get_engine(db_url)
    with Session(engine) as sess:
        row = Prediction(
            request_json=json.dumps(request_obj),
            churn_probability=float(proba),
            churn_label=int(label),
            model_uri=model_uri or "",
            model_version=model_version or "",
        )
        sess.add(row)
        sess.commit()
        sess.refresh(row)
        return int(row.id)


def add_feedback(db_url: str, prediction_id: int, actual_churn: int) -> None:
    engine = get_engine(db_url)
    with Session(engine) as sess:
        row = sess.get(Prediction, prediction_id)
        if row is None:
            raise ValueError(f"prediction_id {prediction_id} not found")
        row.actual_churn = int(actual_churn)
        row.has_feedback = True
        sess.commit()


def insert_daily_metrics(
    db_url: str,
    *,
    n_predictions: int,
    n_feedback: int,
    roc_auc: Optional[float],
    pr_auc: Optional[float],
    brier: Optional[float],
    ece: Optional[float],
    worst_feature: Optional[str],
    worst_psi: Optional[float],
) -> None:
    engine = get_engine(db_url)
    with Session(engine) as sess:
        sess.add(DailyMetric(
            n_predictions=int(n_predictions),
            n_feedback=int(n_feedback),
            roc_auc=roc_auc,
            pr_auc=pr_auc,
            brier=brier,
            ece=ece,
            worst_feature=worst_feature,
            worst_psi=worst_psi,
        ))
        sess.commit()


def insert_segment_metrics(
    db_url: str,
    segment_type: str,
    rows: list[tuple[str, int, Optional[float], Optional[float], Optional[float]]],
) -> None:
    """rows: list of (segment_value, n, roc_auc, pr_auc, brier)"""
    engine = get_engine(db_url)
    with Session(engine) as sess:
        for seg_value, n, roc_auc, pr_auc, brier in rows:
            sess.add(SegmentMetric(
                segment_type=segment_type,
                segment_value=str(seg_value),
                n=int(n),
                roc_auc=roc_auc,
                pr_auc=pr_auc,
                brier=brier,
            ))
        sess.commit()
