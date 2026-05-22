from __future__ import annotations

from collections.abc import Sequence

import pandas as pd


NUMERIC_FEATURE_COLUMNS = [
    "amount",
    "tx_count_1h",
    "tx_count_24h",
    "tx_count_7d",
    "amount_sum_1h",
    "amount_sum_24h",
    "amount_sum_7d",
    "amount_mean_1h",
    "amount_mean_24h",
    "amount_mean_7d",
    "wilaya_distance_km",
    "incoming_amount_24h",
    "outgoing_amount_24h",
    "incoming_outgoing_ratio_24h",
]


def _select_existing_columns(
    dataframe: pd.DataFrame,
    columns: Sequence[str],
    *,
    require_all: bool,
) -> list[str]:
    missing_columns = set(columns) - set(dataframe.columns)

    if require_all and missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Colonnes manquantes pour la normalisation: {missing}")

    return [column for column in columns if column in dataframe.columns]


def _numeric_series(dataframe: pd.DataFrame, column: str) -> pd.Series:
    series = pd.to_numeric(dataframe[column], errors="coerce")

    if series.isna().any():
        raise ValueError(f"La colonne {column} contient des valeurs non numeriques")

    return series


def min_max_scale_features(
    dataframe: pd.DataFrame,
    *,
    columns: Sequence[str] | None = None,
    suffix: str = "_scaled",
    require_all: bool = False,
) -> pd.DataFrame:
    """
    Add min-max scaled columns with values between 0 and 1.
    """

    selected_columns = _select_existing_columns(
        dataframe,
        columns or NUMERIC_FEATURE_COLUMNS,
        require_all=require_all,
    )
    scaled = dataframe.copy()

    for column in selected_columns:
        series = _numeric_series(scaled, column)
        minimum = series.min()
        maximum = series.max()
        denominator = maximum - minimum

        if denominator == 0:
            scaled[f"{column}{suffix}"] = 0.0
        else:
            scaled[f"{column}{suffix}"] = (series - minimum) / denominator

    return scaled


def zscore_scale_features(
    dataframe: pd.DataFrame,
    *,
    columns: Sequence[str] | None = None,
    suffix: str = "_zscore",
    require_all: bool = False,
) -> pd.DataFrame:
    """
    Add z-score columns based on each column mean and standard deviation.
    """

    selected_columns = _select_existing_columns(
        dataframe,
        columns or NUMERIC_FEATURE_COLUMNS,
        require_all=require_all,
    )
    scaled = dataframe.copy()

    for column in selected_columns:
        series = _numeric_series(scaled, column)
        mean = series.mean()
        standard_deviation = series.std(ddof=0)

        if standard_deviation == 0:
            scaled[f"{column}{suffix}"] = 0.0
        else:
            scaled[f"{column}{suffix}"] = (series - mean) / standard_deviation

    return scaled


__all__ = [
    "NUMERIC_FEATURE_COLUMNS",
    "min_max_scale_features",
    "zscore_scale_features",
]
