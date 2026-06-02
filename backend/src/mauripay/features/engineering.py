from __future__ import annotations

from collections.abc import Sequence
from typing import Literal
from typing import Any

import pandas as pd

from mauripay.features.encoding import one_hot_encode_categories
from mauripay.features.geographic import add_geographic_features
from mauripay.features.risk_signals import add_risk_signal_features
from mauripay.features.scaling import (
    NUMERIC_FEATURE_COLUMNS,
    min_max_scale_features,
    zscore_scale_features,
)
from mauripay.features.temporal import add_flow_ratio_features, add_temporal_features
from mauripay.ingestion.common import IngestionResult
from mauripay.ingestion.schema import Transaction


TARGET_COLUMN = "is_anomaly"
DataFrameEngine = Literal["pandas", "polars"]


def transactions_to_dataframe(
    transactions: Sequence[Transaction] | IngestionResult | pd.DataFrame | tuple[Any, ...],
) -> pd.DataFrame:
    """
    Convert validated transactions or ingestion results into a DataFrame.
    """

    if isinstance(transactions, pd.DataFrame):
        return transactions.copy()

    if isinstance(transactions, IngestionResult):
        transactions = transactions.transactions

    if isinstance(transactions, tuple):
        transactions = transactions[0]

    rows = [
        transaction.model_dump(mode="json")
        if isinstance(transaction, Transaction)
        else dict(transaction)
        for transaction in transactions
    ]

    return pd.DataFrame(rows)


def transactions_to_polars_dataframe(
    transactions: Sequence[Transaction] | IngestionResult | pd.DataFrame | tuple[Any, ...],
):
    """
    Convert validated transactions or ingestion results into a Polars DataFrame.
    """

    try:
        import polars as pl
    except ImportError as exc:
        raise ImportError("Pour utiliser Polars, installe le package polars") from exc

    if isinstance(transactions, pd.DataFrame):
        return pl.from_pandas(transactions)

    if isinstance(transactions, IngestionResult):
        transactions = transactions.transactions

    if isinstance(transactions, tuple):
        transactions = transactions[0]

    rows = [
        transaction.model_dump(mode="json")
        if isinstance(transaction, Transaction)
        else dict(transaction)
        for transaction in transactions
    ]

    return pl.DataFrame(rows)


def _numeric_ml_frame(dataframe: pd.DataFrame) -> pd.DataFrame:
    ml_frame = dataframe.copy()

    if TARGET_COLUMN in ml_frame.columns:
        ml_frame[TARGET_COLUMN] = ml_frame[TARGET_COLUMN].astype(bool).astype(int)

    for column in ml_frame.columns:
        if ml_frame[column].dtype == bool:
            ml_frame[column] = ml_frame[column].astype(int)

    numeric_columns = ml_frame.select_dtypes(include=["number"]).columns.tolist()

    return ml_frame[numeric_columns].copy()


def build_features(
    transactions: Sequence[Transaction] | IngestionResult | pd.DataFrame | tuple[Any, ...],
    *,
    include_target: bool = True,
    dataframe_engine: DataFrameEngine = "pandas",
) -> pd.DataFrame:
    """
    Build the complete ML feature table from validated transactions.
    """

    if dataframe_engine == "pandas":
        dataframe = transactions_to_dataframe(transactions)
    elif dataframe_engine == "polars":
        dataframe = transactions_to_polars_dataframe(transactions).to_pandas()
    else:
        raise ValueError("dataframe_engine doit etre 'pandas' ou 'polars'")

    if dataframe.empty:
        return pd.DataFrame()

    features = add_temporal_features(dataframe)
    features = add_flow_ratio_features(features)
    features = add_geographic_features(features)
    features = add_risk_signal_features(features)
    features = one_hot_encode_categories(features)
    features = min_max_scale_features(features, columns=NUMERIC_FEATURE_COLUMNS)
    features = zscore_scale_features(features, columns=NUMERIC_FEATURE_COLUMNS)
    features = _numeric_ml_frame(features)

    if not include_target and TARGET_COLUMN in features.columns:
        features = features.drop(columns=[TARGET_COLUMN])

    return features


def model_feature_columns(dataframe: pd.DataFrame) -> list[str]:
    """
    Return feature columns excluding the evaluation target.
    """

    return [
        column
        for column in dataframe.columns
        if column != TARGET_COLUMN
    ]


__all__ = [
    "TARGET_COLUMN",
    "build_features",
    "model_feature_columns",
    "transactions_to_dataframe",
    "transactions_to_polars_dataframe",
]
