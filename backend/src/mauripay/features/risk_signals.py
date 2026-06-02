from __future__ import annotations

import numpy as np
import pandas as pd


RISK_SIGNAL_FEATURE_COLUMNS = [
    "amount_to_sender_mean_24h",
    "amount_to_sender_mean_7d",
    "amount_zscore_sender_7d",
    "amount_to_flow_24h",
    "fee_rate",
    "is_zero_fee",
    "is_failed_status",
    "failed_zero_fee_signal",
    "is_far_wilaya",
    "remote_receiver_signal",
    "high_distance_amount_signal",
    "sender_receiver_wilaya_tx_count_prior",
    "sender_total_tx_count_prior",
    "sender_receiver_wilaya_share_prior",
    "sender_receiver_is_new_wilaya",
    "sender_receiver_is_rare_wilaya",
    "sender_receiver_id_tx_count_prior",
    "sender_receiver_id_share_prior",
    "sender_receiver_is_new_receiver",
    "sender_receiver_is_rare_receiver",
    "sender_usual_distance_km_prior",
    "sender_distance_gap_km",
    "sender_distance_ratio_prior",
    "sender_receiver_is_new_remote_wilaya",
    "sender_receiver_is_rare_remote_wilaya",
    "sender_receiver_remote_history_gap",
    "new_remote_amount_signal",
    "rare_remote_amount_signal",
    "new_wilaya_distance_signal",
    "new_wilaya_distance_amount_signal",
    "tx_count_1h_to_24h_ratio",
    "tx_count_1h_to_7d_ratio",
    "tx_count_5min_to_1h_ratio",
    "amount_std_to_mean_1h",
    "amount_std_to_mean_5min",
    "sender_receiver_tx_count_5min",
    "sender_receiver_amount_std_to_mean_5min",
    "same_receiver_similar_amount_5min",
    "structuring_signal",
    "high_frequency_signal",
]


REMOTE_WILAYAS = {
    "Dakhlet Nouadhibou",
    "Guidimakha",
    "Inchiri",
    "Tiris Zemmour",
}


def _numeric(series: pd.Series, default: float = 0.0) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(default)


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    clean_denominator = denominator.replace(0, np.nan)
    return (numerator / clean_denominator).replace([np.inf, -np.inf], np.nan).fillna(0.0)


def _has_columns(dataframe: pd.DataFrame, columns: set[str]) -> bool:
    return columns <= set(dataframe.columns)


def _add_sender_location_history_features(features: pd.DataFrame) -> pd.DataFrame:
    required = {"sender_id", "receiver_wilaya", "timestamp"}
    if not _has_columns(features, required):
        features["sender_receiver_wilaya_tx_count_prior"] = 0.0
        features["sender_total_tx_count_prior"] = 0.0
        features["sender_receiver_wilaya_share_prior"] = 0.0
        features["sender_receiver_is_new_wilaya"] = 0
        features["sender_receiver_is_rare_wilaya"] = 0
        return features

    ordered = features.copy()
    ordered["_original_order"] = range(len(ordered))
    ordered["_timestamp_for_location"] = pd.to_datetime(
        ordered["timestamp"],
        utc=True,
        errors="coerce",
        format="mixed",
    )
    ordered = ordered.sort_values(
        ["sender_id", "_timestamp_for_location", "_original_order"],
        na_position="last",
    )

    sender_wilaya_counts = (
        ordered.groupby(["sender_id", "receiver_wilaya"]).cumcount().astype(float)
    )
    sender_total_counts = ordered.groupby("sender_id").cumcount().astype(float)
    share = _safe_ratio(sender_wilaya_counts, sender_total_counts)

    ordered["sender_receiver_wilaya_tx_count_prior"] = sender_wilaya_counts
    ordered["sender_total_tx_count_prior"] = sender_total_counts
    ordered["sender_receiver_wilaya_share_prior"] = share
    ordered["sender_receiver_is_new_wilaya"] = sender_wilaya_counts.eq(0).astype(int)
    ordered["sender_receiver_is_rare_wilaya"] = (
        sender_total_counts.ge(3) & share.lt(0.05)
    ).astype(int)

    history_columns = [
        "_original_order",
        "sender_receiver_wilaya_tx_count_prior",
        "sender_total_tx_count_prior",
        "sender_receiver_wilaya_share_prior",
        "sender_receiver_is_new_wilaya",
        "sender_receiver_is_rare_wilaya",
    ]
    return (
        ordered[history_columns]
        .sort_values("_original_order")
        .drop(columns=["_original_order"])
        .reset_index(drop=True)
        .join(features.reset_index(drop=True).drop(columns=history_columns[1:], errors="ignore"))
    )


def _add_sender_receiver_history_features(features: pd.DataFrame) -> pd.DataFrame:
    required = {"sender_id", "receiver_id", "timestamp"}
    if not _has_columns(features, required):
        features["sender_receiver_id_tx_count_prior"] = 0.0
        features["sender_receiver_id_share_prior"] = 0.0
        features["sender_receiver_is_new_receiver"] = 0
        features["sender_receiver_is_rare_receiver"] = 0
        return features

    ordered = features.copy()
    ordered["_original_order"] = range(len(ordered))
    ordered["_timestamp_for_receiver"] = pd.to_datetime(
        ordered["timestamp"],
        utc=True,
        errors="coerce",
        format="mixed",
    )
    ordered = ordered.sort_values(
        ["sender_id", "_timestamp_for_receiver", "_original_order"],
        na_position="last",
    )

    receiver_counts = ordered.groupby(["sender_id", "receiver_id"]).cumcount().astype(float)
    sender_counts = ordered.groupby("sender_id").cumcount().astype(float)
    share = _safe_ratio(receiver_counts, sender_counts)

    ordered["sender_receiver_id_tx_count_prior"] = receiver_counts
    ordered["sender_receiver_id_share_prior"] = share
    ordered["sender_receiver_is_new_receiver"] = receiver_counts.eq(0).astype(int)
    ordered["sender_receiver_is_rare_receiver"] = (
        sender_counts.ge(3) & share.lt(0.05)
    ).astype(int)

    history_columns = [
        "_original_order",
        "sender_receiver_id_tx_count_prior",
        "sender_receiver_id_share_prior",
        "sender_receiver_is_new_receiver",
        "sender_receiver_is_rare_receiver",
    ]
    return (
        ordered[history_columns]
        .sort_values("_original_order")
        .drop(columns=["_original_order"])
        .reset_index(drop=True)
        .join(features.reset_index(drop=True).drop(columns=history_columns[1:], errors="ignore"))
    )


def _add_sender_distance_history_features(features: pd.DataFrame) -> pd.DataFrame:
    required = {"sender_id", "timestamp", "wilaya_distance_km"}
    if not _has_columns(features, required):
        features["sender_usual_distance_km_prior"] = 0.0
        features["sender_distance_gap_km"] = 0.0
        features["sender_distance_ratio_prior"] = 0.0
        return features

    ordered = features.copy()
    ordered["_original_order"] = range(len(ordered))
    ordered["_timestamp_for_distance"] = pd.to_datetime(
        ordered["timestamp"],
        utc=True,
        errors="coerce",
        format="mixed",
    )
    ordered["_distance"] = _numeric(ordered["wilaya_distance_km"])
    ordered = ordered.sort_values(
        ["sender_id", "_timestamp_for_distance", "_original_order"],
        na_position="last",
    )

    prior_distance_mean = (
        ordered.groupby("sender_id")["_distance"]
        .expanding()
        .mean()
        .groupby(level=0)
        .shift(1)
        .reset_index(level=0, drop=True)
    ).fillna(0.0)

    ordered["sender_usual_distance_km_prior"] = prior_distance_mean
    ordered["sender_distance_gap_km"] = (ordered["_distance"] - prior_distance_mean).clip(
        lower=0.0
    )
    ordered["sender_distance_ratio_prior"] = _safe_ratio(
        ordered["_distance"],
        prior_distance_mean,
    )

    history_columns = [
        "_original_order",
        "sender_usual_distance_km_prior",
        "sender_distance_gap_km",
        "sender_distance_ratio_prior",
    ]
    return (
        ordered[history_columns]
        .sort_values("_original_order")
        .drop(columns=["_original_order"])
        .reset_index(drop=True)
        .join(features.reset_index(drop=True).drop(columns=history_columns[1:], errors="ignore"))
    )


def _sender_receiver_rolling_stats(
    features: pd.DataFrame,
    window: str = "5min",
) -> pd.DataFrame:
    required = {"sender_id", "receiver_id", "timestamp", "amount"}
    columns = [
        "sender_receiver_tx_count_5min",
        "sender_receiver_amount_mean_5min",
        "sender_receiver_amount_std_5min",
    ]
    if not _has_columns(features, required):
        return pd.DataFrame({column: [0.0] * len(features) for column in columns})

    ordered = features.copy()
    ordered["_original_order"] = range(len(ordered))
    ordered["_timestamp_for_pair"] = pd.to_datetime(
        ordered["timestamp"],
        utc=True,
        errors="coerce",
        format="mixed",
    )
    ordered["_amount"] = _numeric(ordered["amount"])
    ordered = ordered.sort_values(
        ["sender_id", "receiver_id", "_timestamp_for_pair", "_original_order"],
        na_position="last",
    )
    valid = ordered.dropna(subset=["_timestamp_for_pair"])
    result = pd.DataFrame({column: [0.0] * len(features) for column in columns})
    if valid.empty:
        return result

    rolled = (
        valid.set_index("_timestamp_for_pair")
        .groupby(["sender_id", "receiver_id"])["_amount"]
        .rolling(window, closed="both")
    )
    stats = valid[["_original_order"]].copy()
    stats["sender_receiver_tx_count_5min"] = rolled.count().to_numpy()
    stats["sender_receiver_amount_mean_5min"] = rolled.mean().to_numpy()
    stats["sender_receiver_amount_std_5min"] = rolled.std().fillna(0).to_numpy()
    result.loc[stats["_original_order"].to_numpy(), columns] = stats[columns].to_numpy()
    return result


def add_risk_signal_features(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Add business risk signals without using target labels.

    These features make known MauriPay anomaly patterns easier to reconstruct:
    unusually high amounts, outage-like failures, remote locations, structuring,
    and high-frequency bursts.
    """

    features = dataframe.copy()
    features = _add_sender_location_history_features(features)
    features = _add_sender_receiver_history_features(features)
    features = _add_sender_distance_history_features(features)

    if "amount" in features.columns:
        amount = _numeric(features["amount"])
    else:
        amount = pd.Series(0.0, index=features.index)

    if _has_columns(features, {"amount", "amount_mean_24h"}):
        features["amount_to_sender_mean_24h"] = _safe_ratio(
            amount,
            _numeric(features["amount_mean_24h"]),
        )
    else:
        features["amount_to_sender_mean_24h"] = 0.0

    if _has_columns(features, {"amount", "amount_mean_7d"}):
        features["amount_to_sender_mean_7d"] = _safe_ratio(
            amount,
            _numeric(features["amount_mean_7d"]),
        )
    else:
        features["amount_to_sender_mean_7d"] = 0.0

    if _has_columns(features, {"amount", "amount_mean_7d", "amount_std_7d"}):
        features["amount_zscore_sender_7d"] = _safe_ratio(
            amount - _numeric(features["amount_mean_7d"]),
            _numeric(features["amount_std_7d"]),
        )
    else:
        features["amount_zscore_sender_7d"] = 0.0

    if _has_columns(features, {"amount", "amount_sum_24h"}):
        features["amount_to_flow_24h"] = _safe_ratio(
            amount,
            _numeric(features["amount_sum_24h"]),
        )
    else:
        features["amount_to_flow_24h"] = 0.0

    if _has_columns(features, {"fees", "amount"}):
        features["fee_rate"] = _safe_ratio(_numeric(features["fees"]), amount)
        features["is_zero_fee"] = (_numeric(features["fees"]) == 0).astype(int)
    else:
        features["fee_rate"] = 0.0
        features["is_zero_fee"] = 0

    if "status" in features.columns:
        status = features["status"].fillna("").astype(str).str.upper()
        features["is_failed_status"] = status.eq("FAILED").astype(int)
    else:
        features["is_failed_status"] = 0
    features["failed_zero_fee_signal"] = (
        features["is_failed_status"].astype(int) * features["is_zero_fee"].astype(int)
    )

    if "wilaya_distance_km" in features.columns:
        distance = _numeric(features["wilaya_distance_km"])
        features["is_far_wilaya"] = (distance >= 300).astype(int)
        features["high_distance_amount_signal"] = (
            features["is_far_wilaya"].astype(int) * np.log1p(amount)
        )
    else:
        features["is_far_wilaya"] = 0
        features["high_distance_amount_signal"] = 0.0

    if "receiver_wilaya" in features.columns:
        features["remote_receiver_signal"] = (
            features["receiver_wilaya"].fillna("").astype(str).isin(REMOTE_WILAYAS).astype(int)
        )
    else:
        features["remote_receiver_signal"] = 0

    new_wilaya = _numeric(features["sender_receiver_is_new_wilaya"]).astype(int)
    rare_wilaya = _numeric(features["sender_receiver_is_rare_wilaya"]).astype(int)
    remote_receiver = _numeric(features["remote_receiver_signal"]).astype(int)
    wilaya_share = _numeric(features["sender_receiver_wilaya_share_prior"])
    distance = (
        _numeric(features["wilaya_distance_km"])
        if "wilaya_distance_km" in features
        else pd.Series(0.0, index=features.index)
    )

    features["sender_receiver_is_new_remote_wilaya"] = new_wilaya * remote_receiver
    features["sender_receiver_is_rare_remote_wilaya"] = rare_wilaya * remote_receiver
    features["sender_receiver_remote_history_gap"] = (
        remote_receiver * (1.0 - wilaya_share.clip(lower=0.0, upper=1.0))
    )
    features["new_remote_amount_signal"] = (
        features["sender_receiver_is_new_remote_wilaya"] * np.log1p(amount)
    )
    features["rare_remote_amount_signal"] = (
        features["sender_receiver_is_rare_remote_wilaya"] * np.log1p(amount)
    )
    features["new_wilaya_distance_signal"] = new_wilaya * distance
    features["new_wilaya_distance_amount_signal"] = (
        new_wilaya * distance * np.log1p(amount)
    )

    if _has_columns(features, {"tx_count_1h", "tx_count_24h"}):
        features["tx_count_1h_to_24h_ratio"] = _safe_ratio(
            _numeric(features["tx_count_1h"]),
            _numeric(features["tx_count_24h"]),
        )
    else:
        features["tx_count_1h_to_24h_ratio"] = 0.0

    if _has_columns(features, {"tx_count_1h", "tx_count_7d"}):
        features["tx_count_1h_to_7d_ratio"] = _safe_ratio(
            _numeric(features["tx_count_1h"]),
            _numeric(features["tx_count_7d"]),
        )
    else:
        features["tx_count_1h_to_7d_ratio"] = 0.0

    if _has_columns(features, {"tx_count_5min", "tx_count_1h"}):
        features["tx_count_5min_to_1h_ratio"] = _safe_ratio(
            _numeric(features["tx_count_5min"]),
            _numeric(features["tx_count_1h"]),
        )
    else:
        features["tx_count_5min_to_1h_ratio"] = 0.0

    if _has_columns(features, {"amount_std_1h", "amount_mean_1h"}):
        features["amount_std_to_mean_1h"] = _safe_ratio(
            _numeric(features["amount_std_1h"]),
            _numeric(features["amount_mean_1h"]),
        )
    else:
        features["amount_std_to_mean_1h"] = 0.0

    if _has_columns(features, {"amount_std_5min", "amount_mean_5min"}):
        features["amount_std_to_mean_5min"] = _safe_ratio(
            _numeric(features["amount_std_5min"]),
            _numeric(features["amount_mean_5min"]),
        )
    else:
        features["amount_std_to_mean_5min"] = 0.0

    pair_stats = _sender_receiver_rolling_stats(features)
    for column in pair_stats.columns:
        features[column] = pair_stats[column]
    features["sender_receiver_amount_std_to_mean_5min"] = _safe_ratio(
        _numeric(features["sender_receiver_amount_std_5min"]),
        _numeric(features["sender_receiver_amount_mean_5min"]),
    )
    features["same_receiver_similar_amount_5min"] = (
        (_numeric(features["sender_receiver_tx_count_5min"]) >= 3)
        & (_numeric(features["sender_receiver_amount_std_to_mean_5min"]) <= 0.15)
    ).astype(int)

    tx_count_1h = (
        _numeric(features["tx_count_1h"])
        if "tx_count_1h" in features
        else pd.Series(0.0, index=features.index)
    )
    amount_similarity = (
        _numeric(features["amount_std_to_mean_1h"])
        if "amount_std_to_mean_1h" in features
        else pd.Series(0.0, index=features.index)
    )
    transaction_type = (
        features["transaction_type"].fillna("").astype(str).str.upper()
        if "transaction_type" in features
        else pd.Series("", index=features.index)
    )
    features["structuring_signal"] = (
        transaction_type.eq("TRANSFER")
        & (
            ((tx_count_1h >= 4) & (amount_similarity <= 0.15))
            | features["same_receiver_similar_amount_5min"].astype(bool)
        )
    ).astype(int)
    tx_count_5min = (
        _numeric(features["tx_count_5min"])
        if "tx_count_5min" in features
        else pd.Series(0.0, index=features.index)
    )
    features["high_frequency_signal"] = ((tx_count_1h >= 10) | (tx_count_5min >= 4)).astype(int)

    return features


__all__ = [
    "REMOTE_WILAYAS",
    "RISK_SIGNAL_FEATURE_COLUMNS",
    "add_risk_signal_features",
]
