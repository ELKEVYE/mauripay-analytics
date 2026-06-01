from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd


WINDOWS: Mapping[str, str] = {
    "1h": "1h",
    "24h": "24h",
    "7d": "7D",
}

TEMPORAL_FEATURE_COLUMNS = [
    "tx_count_5min",
    "tx_count_10min",
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
    "sender_unique_receivers_1h",
    "sender_unique_receivers_24h",
    "same_sender_receiver_count_1h",
    "similar_amount_count_1h",
    "same_receiver_amount_count_24h",
    "amount_vs_sender_avg_7d",
    "amount_vs_sender_past_avg_7d",
    "amount_zscore_sender_7d",
    "sender_past_tx_count_7d",
    "tx_gap_seconds",
    "amount_log",
    "fees_to_amount_ratio",
    "is_failed",
    "is_night",
    "receiver_tx_count_1h",
    "receiver_unique_senders_1h",
    "receiver_amount_sum_1h",
    "receiver_tx_count_24h",
    "receiver_unique_senders_24h",
    "receiver_amount_sum_24h",
    "operator_failure_rate_1h",
    "sender_wilaya_change_count_24h",
    "hour",
    "day_of_week",
    "is_weekend",
    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos",
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


def _add_sender_window_features(
    features: pd.DataFrame,
    *,
    sender_col: str,
    receiver_col: str,
    timestamp_col: str,
    amount_col: str,
) -> None:
    features["sender_unique_receivers_1h"] = 0
    features["same_sender_receiver_count_1h"] = 0
    features["similar_amount_count_1h"] = 0

    if receiver_col not in features.columns:
        return

    for _, group in features.groupby(sender_col, sort=False):
        timestamps = group[timestamp_col].tolist()
        receivers = group[receiver_col].tolist()
        amounts = group[amount_col].tolist()
        indexes = group.index.tolist()
        start_index = 0

        for end_index, timestamp in enumerate(timestamps):
            window_start = timestamp - pd.Timedelta(hours=1)
            while timestamps[start_index] < window_start:
                start_index += 1

            window_receivers = receivers[start_index : end_index + 1]
            window_amounts = amounts[start_index : end_index + 1]
            receiver = receivers[end_index]
            amount = amounts[end_index]
            lower = amount * 0.95
            upper = amount * 1.05

            features.loc[indexes[end_index], "sender_unique_receivers_1h"] = len(
                set(window_receivers)
            )
            features.loc[indexes[end_index], "same_sender_receiver_count_1h"] = (
                window_receivers.count(receiver)
            )
            features.loc[indexes[end_index], "similar_amount_count_1h"] = sum(
                lower <= window_amount <= upper
                for window_amount in window_amounts
            )


def _add_receiver_window_features(
    features: pd.DataFrame,
    *,
    sender_col: str,
    receiver_col: str,
    timestamp_col: str,
    amount_col: str,
) -> None:
    features["receiver_tx_count_1h"] = 0
    features["receiver_unique_senders_1h"] = 0
    features["receiver_amount_sum_1h"] = 0.0
    features["receiver_tx_count_24h"] = 0
    features["receiver_unique_senders_24h"] = 0
    features["receiver_amount_sum_24h"] = 0.0

    if receiver_col not in features.columns:
        return

    receiver_sorted = features.sort_values([receiver_col, timestamp_col, "_original_order"])
    for _, group in receiver_sorted.groupby(receiver_col, sort=False):
        timestamps = group[timestamp_col].tolist()
        senders = group[sender_col].tolist()
        amounts = group[amount_col].tolist()
        indexes = group.index.tolist()
        start_index = 0

        start_1h = 0
        start_24h = 0
        for end_index, timestamp in enumerate(timestamps):
            window_start_1h = timestamp - pd.Timedelta(hours=1)
            while timestamps[start_1h] < window_start_1h:
                start_1h += 1

            window_start_24h = timestamp - pd.Timedelta(hours=24)
            while timestamps[start_24h] < window_start_24h:
                start_24h += 1

            window_senders_1h = senders[start_1h : end_index + 1]
            window_amounts_1h = amounts[start_1h : end_index + 1]
            window_senders_24h = senders[start_24h : end_index + 1]
            window_amounts_24h = amounts[start_24h : end_index + 1]

            features.loc[indexes[end_index], "receiver_tx_count_1h"] = len(window_senders_1h)
            features.loc[indexes[end_index], "receiver_unique_senders_1h"] = len(
                set(window_senders_1h)
            )
            features.loc[indexes[end_index], "receiver_amount_sum_1h"] = sum(window_amounts_1h)
            features.loc[indexes[end_index], "receiver_tx_count_24h"] = len(window_senders_24h)
            features.loc[indexes[end_index], "receiver_unique_senders_24h"] = len(
                set(window_senders_24h)
            )
            features.loc[indexes[end_index], "receiver_amount_sum_24h"] = sum(window_amounts_24h)


def _add_operator_failure_features(
    features: pd.DataFrame,
    *,
    operator_col: str,
    status_col: str,
    timestamp_col: str,
) -> None:
    features["operator_failure_rate_1h"] = 0.0

    if operator_col not in features.columns or status_col not in features.columns:
        return

    operator_sorted = features.sort_values([operator_col, timestamp_col, "_original_order"])
    for _, group in operator_sorted.groupby(operator_col, sort=False):
        timestamps = group[timestamp_col].tolist()
        failures = (group[status_col].astype(str) != "SUCCESS").astype(int).tolist()
        indexes = group.index.tolist()
        start_index = 0

        for end_index, timestamp in enumerate(timestamps):
            window_start = timestamp - pd.Timedelta(hours=1)
            while timestamps[start_index] < window_start:
                start_index += 1

            window_failures = failures[start_index : end_index + 1]
            features.loc[indexes[end_index], "operator_failure_rate_1h"] = (
                sum(window_failures) / len(window_failures)
            )


def _add_location_change_features(
    features: pd.DataFrame,
    *,
    sender_col: str,
    sender_wilaya_col: str,
    timestamp_col: str,
) -> None:
    features["sender_wilaya_change_count_24h"] = 0

    if sender_wilaya_col not in features.columns:
        return

    for _, group in features.groupby(sender_col, sort=False):
        timestamps = group[timestamp_col].tolist()
        wilayas = group[sender_wilaya_col].tolist()
        indexes = group.index.tolist()
        start_index = 0

        for end_index, timestamp in enumerate(timestamps):
            window_start = timestamp - pd.Timedelta(hours=24)
            while timestamps[start_index] < window_start:
                start_index += 1

            window_wilayas = wilayas[start_index : end_index + 1]
            changes = sum(
                current != previous
                for previous, current in zip(window_wilayas, window_wilayas[1:])
            )
            features.loc[indexes[end_index], "sender_wilaya_change_count_24h"] = changes


def _add_sender_24h_window_features(
    features: pd.DataFrame,
    *,
    sender_col: str,
    receiver_col: str,
    timestamp_col: str,
    amount_col: str,
) -> None:
    """24h window: unique receivers and same-receiver similar-amount count.

    The 1h window in _add_sender_window_features misses STRUCTURING sequences
    that span up to 105 minutes (2-15 min spacing × 7 steps). The 24h window
    reliably captures all transactions in a structuring burst.
    """
    features["sender_unique_receivers_24h"] = 0
    features["same_receiver_amount_count_24h"] = 0

    if receiver_col not in features.columns:
        return

    for _, group in features.groupby(sender_col, sort=False):
        timestamps = group[timestamp_col].tolist()
        receivers = group[receiver_col].tolist()
        amounts = group[amount_col].tolist()
        indexes = group.index.tolist()
        start_index = 0

        for end_index, timestamp in enumerate(timestamps):
            window_start = timestamp - pd.Timedelta(hours=24)
            while timestamps[start_index] < window_start:
                start_index += 1

            window_receivers = receivers[start_index : end_index + 1]
            window_amounts = amounts[start_index : end_index + 1]
            receiver = receivers[end_index]
            amount = amounts[end_index]
            lower = amount * 0.95
            upper = amount * 1.05

            features.loc[indexes[end_index], "sender_unique_receivers_24h"] = len(
                set(window_receivers)
            )
            features.loc[indexes[end_index], "same_receiver_amount_count_24h"] = sum(
                r == receiver and lower <= a <= upper
                for r, a in zip(window_receivers, window_amounts)
            )


def add_temporal_features(
    dataframe: pd.DataFrame,
    *,
    sender_col: str = "sender_id",
    receiver_col: str = "receiver_id",
    timestamp_col: str = "timestamp",
    amount_col: str = "amount",
    ramadan_col: str = "is_ramadan",
    operator_col: str = "operator",
    status_col: str = "status",
    sender_wilaya_col: str = "sender_wilaya",
) -> pd.DataFrame:
    """Add rolling temporal and behavior features without using labels."""

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

    # Seconds since the sender's previous transaction. Within each sender group the
    # DataFrame is already in chronological order, so groupby.diff() is correct.
    # HIGH_FREQUENCY sequences have gaps of 20-120 s — this is the strongest single
    # feature for that anomaly type. First transaction per sender gets 86400 (24h).
    tx_gap = (
        features.groupby(sender_col, sort=False)[timestamp_col]
        .diff()
        .dt.total_seconds()
    )
    features["tx_gap_seconds"] = tx_gap.fillna(86400.0).clip(lower=0.0)

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

    for suffix, window in {"5min": "5min", "10min": "10min"}.items():
        features[f"tx_count_{suffix}"] = (
            features.set_index(timestamp_col)
            .groupby(sender_col)[amount_col]
            .rolling(window, closed="both")
            .count()
            .to_numpy()
        )

    _add_sender_window_features(
        features,
        sender_col=sender_col,
        receiver_col=receiver_col,
        timestamp_col=timestamp_col,
        amount_col=amount_col,
    )
    _add_sender_24h_window_features(
        features,
        sender_col=sender_col,
        receiver_col=receiver_col,
        timestamp_col=timestamp_col,
        amount_col=amount_col,
    )
    _add_receiver_window_features(
        features,
        sender_col=sender_col,
        receiver_col=receiver_col,
        timestamp_col=timestamp_col,
        amount_col=amount_col,
    )
    _add_operator_failure_features(
        features,
        operator_col=operator_col,
        status_col=status_col,
        timestamp_col=timestamp_col,
    )
    _add_location_change_features(
        features,
        sender_col=sender_col,
        sender_wilaya_col=sender_wilaya_col,
        timestamp_col=timestamp_col,
    )

    sender_avg_7d = features["amount_mean_7d"].replace(0, pd.NA)
    features["amount_vs_sender_avg_7d"] = (
        features[amount_col] / sender_avg_7d
    ).fillna(0.0)

    features["sender_past_tx_count_7d"] = (features["tx_count_7d"] - 1).clip(lower=0)
    sender_past_amount_sum_7d = (features["amount_sum_7d"] - features[amount_col]).clip(lower=0)
    sender_past_avg_7d = (
        sender_past_amount_sum_7d / features["sender_past_tx_count_7d"].replace(0, pd.NA)
    )
    features["amount_vs_sender_past_avg_7d"] = (
        features[amount_col] / sender_past_avg_7d.replace(0, pd.NA)
    ).fillna(1.0)

    # Z-score of current amount vs sender 7d stats. Catches HIGH_AMOUNT even when
    # the sender has a history (ratio alone can be misleading with small history).
    amount_std_safe = features["amount_std_7d"].replace(0, pd.NA)
    features["amount_zscore_sender_7d"] = (
        (features[amount_col] - features["amount_mean_7d"]) / amount_std_safe
    ).fillna(0.0).clip(-10.0, 10.0)

    features["amount_log"] = np.log1p(features[amount_col])

    if "fees" in features.columns:
        fees = pd.to_numeric(features["fees"], errors="coerce").fillna(0.0)
        amount_denominator = features[amount_col].replace(0, pd.NA)
        features["fees_to_amount_ratio"] = (fees / amount_denominator).fillna(0.0)
    else:
        features["fees_to_amount_ratio"] = 0.0

    if status_col in features.columns:
        features["is_failed"] = (features[status_col].astype(str) != "SUCCESS").astype(int)
    else:
        features["is_failed"] = 0

    features["hour"] = features[timestamp_col].dt.hour
    features["day_of_week"] = features[timestamp_col].dt.dayofweek
    features["is_weekend"] = features["day_of_week"].isin([5, 6]).astype(int)
    features["hour_sin"] = np.sin(2 * np.pi * features["hour"] / 24)
    features["hour_cos"] = np.cos(2 * np.pi * features["hour"] / 24)
    features["day_of_week_sin"] = np.sin(2 * np.pi * features["day_of_week"] / 7)
    features["day_of_week_cos"] = np.cos(2 * np.pi * features["day_of_week"] / 7)

    if ramadan_col in features.columns:
        features["is_ramadan"] = _boolean_series_to_int(features[ramadan_col])
    else:
        features["is_ramadan"] = 0

    # Night transactions (00:00–04:59) are contextually unusual.
    features["is_night"] = features["hour"].isin([0, 1, 2, 3, 4]).astype(int)

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
    """Add incoming/outgoing amount ratio features for the sender account."""

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


