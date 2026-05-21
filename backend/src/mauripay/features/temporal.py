from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


WINDOWS: Mapping[str, str] = {
    "1h": "1h",
    "24h": "24h",
    "7d": "7D",
}

TEMPORAL_FEATURE_COLUMNS = [
    "tx_count_1h",
    "tx_count_24h",
    "tx_count_7d",
    "amount_sum_1h",
    "amount_sum_24h",
    "amount_sum_7d",
    "amount_mean_1h",
    "amount_mean_24h",
    "amount_mean_7d",
    "amount_std_1h",
    "amount_std_24h",
    "amount_std_7d",
    "hour",
    "day_of_week",
    "is_weekend",
    "is_ramadan",
    "incoming_amount_24h",
    "outgoing_amount_24h",
    "incoming_outgoing_ratio_24h",
]


def _boolean_series_to_int(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.astype(int)

    if pd.api.types.is_numeric_dtype(series):
        return series.fillna(0).astype(int)

    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin({"1", "true", "yes", "y"})
        .astype(int)
    )


def add_temporal_features(
    dataframe: pd.DataFrame,
    *,
    sender_col: str = "sender_id",
    timestamp_col: str = "timestamp",
    amount_col: str = "amount",
    ramadan_col: str = "is_ramadan",
) -> pd.DataFrame:
    """
    Add rolling temporal features per sender account.

    Rolling windows include the current transaction and all previous
    transactions from the same sender inside the requested time window.
    """

    required_columns = {sender_col, timestamp_col, amount_col}
    missing_columns = required_columns - set(dataframe.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Colonnes manquantes pour les features temporelles: {missing}")

    features = dataframe.copy()
    features["_original_order"] = range(len(features))
    features[timestamp_col] = pd.to_datetime(
        features[timestamp_col],
        utc=True,
        format="mixed",
    )
    features[amount_col] = pd.to_numeric(features[amount_col], errors="coerce")

    if features[amount_col].isna().any():
        raise ValueError(f"La colonne {amount_col} contient des montants invalides")

    features = features.sort_values([sender_col, timestamp_col, "_original_order"])

    for suffix, window in WINDOWS.items():
        rolled = (
            features.set_index(timestamp_col)
            .groupby(sender_col)[amount_col]
            .rolling(window, closed="both")
        )

        features[f"tx_count_{suffix}"] = rolled.count().to_numpy()
        features[f"amount_sum_{suffix}"] = rolled.sum().to_numpy()
        features[f"amount_mean_{suffix}"] = rolled.mean().to_numpy()
        features[f"amount_std_{suffix}"] = rolled.std().fillna(0).to_numpy()

    features["hour"] = features[timestamp_col].dt.hour
    features["day_of_week"] = features[timestamp_col].dt.dayofweek
    features["is_weekend"] = features["day_of_week"].isin([5, 6]).astype(int)

    if ramadan_col in features.columns:
        features["is_ramadan"] = _boolean_series_to_int(features[ramadan_col])
    else:
        features["is_ramadan"] = 0

    return (
        features.sort_values("_original_order")
        .drop(columns=["_original_order"])
        .reset_index(drop=True)
    )


def add_flow_ratio_features(
    dataframe: pd.DataFrame,
    *,
    sender_col: str = "sender_id",
    receiver_col: str = "receiver_id",
    timestamp_col: str = "timestamp",
    amount_col: str = "amount",
    window: str = "24h",
) -> pd.DataFrame:
    """
    Add incoming/outgoing amount ratio features for the sender account.

    For each transaction, the features describe the sender account activity
    inside the rolling window ending at the transaction timestamp.
    """

    required_columns = {sender_col, receiver_col, timestamp_col, amount_col}
    missing_columns = required_columns - set(dataframe.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Colonnes manquantes pour le ratio entrant/sortant: {missing}")

    features = dataframe.copy()
    features["_original_order"] = range(len(features))
    features[timestamp_col] = pd.to_datetime(
        features[timestamp_col],
        utc=True,
        format="mixed",
    )
    features[amount_col] = pd.to_numeric(features[amount_col], errors="coerce")

    if features[amount_col].isna().any():
        raise ValueError(f"La colonne {amount_col} contient des montants invalides")

    outgoing_events = pd.DataFrame(
        {
            "account_id": features[sender_col],
            timestamp_col: features[timestamp_col],
            "_original_order": features["_original_order"],
            "_event_order": 0,
            "incoming_amount": 0.0,
            "outgoing_amount": features[amount_col],
            "_is_sender_event": True,
        }
    )
    incoming_events = pd.DataFrame(
        {
            "account_id": features[receiver_col],
            timestamp_col: features[timestamp_col],
            "_original_order": features["_original_order"],
            "_event_order": 1,
            "incoming_amount": features[amount_col],
            "outgoing_amount": 0.0,
            "_is_sender_event": False,
        }
    )
    events = pd.concat([outgoing_events, incoming_events], ignore_index=True)
    events = events.sort_values(["account_id", timestamp_col, "_event_order", "_original_order"])

    rolled = (
        events.set_index(timestamp_col)
        .groupby("account_id")[["incoming_amount", "outgoing_amount"]]
        .rolling(window, closed="both")
        .sum()
        .reset_index()
    )
    events["incoming_amount_24h"] = rolled["incoming_amount"].to_numpy()
    events["outgoing_amount_24h"] = rolled["outgoing_amount"].to_numpy()

    sender_events = events[events["_is_sender_event"]].copy()
    denominator = sender_events["outgoing_amount_24h"].replace(0, pd.NA)
    sender_events["incoming_outgoing_ratio_24h"] = (
        sender_events["incoming_amount_24h"] / denominator
    ).fillna(0.0)

    ratio_columns = [
        "_original_order",
        "incoming_amount_24h",
        "outgoing_amount_24h",
        "incoming_outgoing_ratio_24h",
    ]
    features = features.merge(
        sender_events[ratio_columns],
        on="_original_order",
        how="left",
    )

    return (
        features.sort_values("_original_order")
        .drop(columns=["_original_order"])
        .reset_index(drop=True)
    )


__all__ = [
    "TEMPORAL_FEATURE_COLUMNS",
    "WINDOWS",
    "add_flow_ratio_features",
    "add_temporal_features",
]
