from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class FeatureSpec:
    numeric: Sequence[str]
    categorical: Sequence[str]
    target: str


CHURN_SPEC = FeatureSpec(
    numeric=["tenure_months", "monthly_charges", "total_charges", "tickets_90d"],
    categorical=["contract_type", "payment_method", "internet_service", "region"],
    target="churn",
)
