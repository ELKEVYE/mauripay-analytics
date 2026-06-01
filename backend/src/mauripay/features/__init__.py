"""
Feature engineering utilities for MauriPay analytics.
"""

from mauripay.features.encoding import (
    CATEGORICAL_COLUMNS,
    CATEGORICAL_VALUES,
    ENCODED_FEATURE_COLUMNS,
    one_hot_encode_categories,
)
from mauripay.features.engineering import (
    TARGET_COLUMN,
    build_features,
    model_feature_columns,
    transactions_to_dataframe,
    transactions_to_polars_dataframe,
)
from mauripay.features.geographic import (
    GEOGRAPHIC_FEATURE_COLUMNS,
    add_geographic_features,
)
from mauripay.features.scaling import (
    NUMERIC_FEATURE_COLUMNS,
    min_max_scale_features,
    zscore_scale_features,
)
from mauripay.features.temporal import (
    TEMPORAL_FEATURE_COLUMNS,
    add_flow_ratio_features,
    add_temporal_features,
)


__all__ = [
    "CATEGORICAL_COLUMNS",
    "CATEGORICAL_VALUES",
    "ENCODED_FEATURE_COLUMNS",
    "GEOGRAPHIC_FEATURE_COLUMNS",
    "NUMERIC_FEATURE_COLUMNS",
    "TARGET_COLUMN",
    "TEMPORAL_FEATURE_COLUMNS",
    "add_geographic_features",
    "add_flow_ratio_features",
    "add_temporal_features",
    "build_features",
    "min_max_scale_features",
    "model_feature_columns",
    "one_hot_encode_categories",
    "transactions_to_dataframe",
    "transactions_to_polars_dataframe",
    "zscore_scale_features",
]
