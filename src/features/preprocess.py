from __future__ import annotations

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.modeling.schema import FeatureSpec


def build_preprocessor(spec: FeatureSpec) -> ColumnTransformer:
    numeric_pipe = Pipeline([("scaler", StandardScaler())])
    cat_pipe = Pipeline([("onehot", OneHotEncoder(handle_unknown="ignore"))])

    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipe, list(spec.numeric)),
            ("cat", cat_pipe, list(spec.categorical)),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def split_xy(df: pd.DataFrame, spec: FeatureSpec) -> tuple[pd.DataFrame, pd.Series]:
    X = df[list(spec.numeric) + list(spec.categorical)].copy()
    y = df[spec.target].astype(int).copy()
    return X, y
