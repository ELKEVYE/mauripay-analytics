from __future__ import annotations

import pandas as pd

REMOTE_WILAYAS = {
    "Dakhlet Nouadhibou",
    "Guidimakha",
    "Inchiri",
    "Tiris Zemmour",
}

HIGH_AMOUNT_LIMITS_BY_TYPE = {
    "AIRTIME": 5_000.0,
    "BILL_PAY": 10_000.0,
    "MERCHANT": 50_000.0,
    "TRANSFER": 100_000.0,
    "CASH_OUT": 100_000.0,
    "CASH_IN": 100_000.0,
}


def _numeric(series: pd.Series, default: float = 0.0) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(default)


def _empty_reasons(index: pd.Index) -> pd.Series:
    return pd.Series([""] * len(index), index=index, dtype=object)


def _append_reason(reasons: pd.Series, mask: pd.Series, reason: str) -> pd.Series:
    updated = reasons.copy()
    clean_mask = mask.fillna(False).astype(bool)
    for idx in updated.index[clean_mask]:
        updated.at[idx] = (
            reason if not updated.at[idx] else f"{updated.at[idx]};{reason}"
        )
    return updated


def _failed_zero_fee_mask(dataframe: pd.DataFrame) -> pd.Series:
    if not {"status", "fees"} <= set(dataframe.columns):
        return pd.Series(False, index=dataframe.index)

    status = dataframe["status"].fillna("").astype(str).str.upper()
    fees = _numeric(dataframe["fees"])
    return status.eq("FAILED") & fees.eq(0)


def _high_amount_sender_profile_mask(dataframe: pd.DataFrame) -> pd.Series:
    required = {"sender_id", "timestamp", "amount"}
    if not required <= set(dataframe.columns):
        return pd.Series(False, index=dataframe.index)

    ordered = dataframe.copy()
    ordered["_original_order"] = range(len(ordered))
    ordered["_timestamp"] = pd.to_datetime(
        ordered["timestamp"],
        utc=True,
        errors="coerce",
        format="mixed",
    )
    ordered["_amount"] = _numeric(ordered["amount"])
    ordered = ordered.sort_values(
        ["sender_id", "_timestamp", "_original_order"],
        na_position="last",
    )

    prior_mean = (
        ordered.groupby("sender_id")["_amount"]
        .expanding()
        .mean()
        .groupby(level=0)
        .shift(1)
        .reset_index(level=0, drop=True)
    )
    prior_count = ordered.groupby("sender_id").cumcount()

    mask = prior_count.ge(3) & ordered["_amount"].gt(prior_mean.fillna(0) * 4)
    mask &= ordered["_amount"].gt(100_000)

    return (
        pd.DataFrame(
            {
                "_original_order": ordered["_original_order"],
                "mask": mask.astype(bool),
            }
        )
        .sort_values("_original_order")
        ["mask"]
        .reset_index(drop=True)
    )


def _sender_rolling_stats(dataframe: pd.DataFrame, window: str = "1h") -> pd.DataFrame:
    required = {"sender_id", "timestamp", "amount"}
    if not required <= set(dataframe.columns):
        return pd.DataFrame(index=dataframe.index)

    ordered = dataframe.copy()
    ordered["_original_order"] = range(len(ordered))
    ordered["_timestamp"] = pd.to_datetime(
        ordered["timestamp"],
        utc=True,
        errors="coerce",
        format="mixed",
    )
    ordered["_amount"] = _numeric(ordered["amount"])
    ordered = ordered.sort_values(
        ["sender_id", "_timestamp", "_original_order"],
        na_position="last",
    )
    valid = ordered.dropna(subset=["_timestamp"])
    if valid.empty:
        return pd.DataFrame(
            {
                "tx_count_1h": [0.0] * len(dataframe),
                "amount_mean_1h": [0.0] * len(dataframe),
                "amount_std_1h": [0.0] * len(dataframe),
                "amount_sum_1h": [0.0] * len(dataframe),
            },
            index=dataframe.index,
        )

    rolled = (
        valid.set_index("_timestamp")
        .groupby("sender_id")["_amount"]
        .rolling(window, closed="both")
    )
    stats = valid[["_original_order"]].copy()
    stats["tx_count_1h"] = rolled.count().to_numpy()
    stats["amount_mean_1h"] = rolled.mean().to_numpy()
    stats["amount_std_1h"] = rolled.std().fillna(0).to_numpy()
    stats["amount_sum_1h"] = rolled.sum().to_numpy()

    result = (
        stats.sort_values("_original_order")
        .drop(columns=["_original_order"])
        .reset_index(drop=True)
    )
    full = pd.DataFrame(
        {
            "tx_count_1h": [0.0] * len(dataframe),
            "amount_mean_1h": [0.0] * len(dataframe),
            "amount_std_1h": [0.0] * len(dataframe),
            "amount_sum_1h": [0.0] * len(dataframe),
        }
    )
    original_order = stats.sort_values("_original_order")["_original_order"].to_numpy()
    full.loc[original_order, result.columns] = result.to_numpy()
    return full


def _high_frequency_mask(dataframe: pd.DataFrame) -> pd.Series:
    hourly_stats = _sender_rolling_stats(dataframe)
    ten_minute_stats = _sender_rolling_stats(dataframe, window="10min")
    if hourly_stats.empty or ten_minute_stats.empty:
        return pd.Series(False, index=dataframe.index)
    return hourly_stats["tx_count_1h"].ge(10) | ten_minute_stats["tx_count_1h"].ge(4)


def _structuring_mask(dataframe: pd.DataFrame) -> pd.Series:
    one_hour = _sender_rolling_stats(dataframe)
    two_hours = _sender_rolling_stats(dataframe, window="2h")
    six_hours = _sender_rolling_stats(dataframe, window="6h")
    day = _sender_rolling_stats(dataframe, window="24h")
    if (
        one_hour.empty
        or two_hours.empty
        or six_hours.empty
        or day.empty
        or "transaction_type" not in dataframe.columns
    ):
        return pd.Series(False, index=dataframe.index)

    transaction_type = dataframe["transaction_type"].fillna("").astype(str).str.upper()
    one_hour_similarity = (
        one_hour["amount_std_1h"] / one_hour["amount_mean_1h"].replace(0, pd.NA)
    ).fillna(0.0)
    two_hour_similarity = (
        two_hours["amount_std_1h"] / two_hours["amount_mean_1h"].replace(0, pd.NA)
    ).fillna(0.0)
    six_hour_similarity = (
        six_hours["amount_std_1h"] / six_hours["amount_mean_1h"].replace(0, pd.NA)
    ).fillna(0.0)
    day_similarity = (
        day["amount_std_1h"] / day["amount_mean_1h"].replace(0, pd.NA)
    ).fillna(0.0)

    one_hour_pattern = (
        one_hour["tx_count_1h"].ge(3)
        & one_hour["amount_sum_1h"].ge(100_000)
        & one_hour_similarity.le(0.15)
    )
    two_hour_pattern = (
        two_hours["tx_count_1h"].ge(4)
        & two_hours["amount_sum_1h"].ge(100_000)
        & two_hour_similarity.le(0.15)
    )
    six_hour_pattern = (
        six_hours["tx_count_1h"].ge(6)
        & six_hours["amount_sum_1h"].ge(150_000)
        & six_hour_similarity.le(0.25)
    )
    day_pattern = (
        day["tx_count_1h"].ge(6)
        & day["amount_sum_1h"].ge(150_000)
        & day_similarity.le(0.25)
    )
    return transaction_type.eq("TRANSFER") & (
        one_hour_pattern | two_hour_pattern | six_hour_pattern | day_pattern
    )


def _operator_outage_mask(dataframe: pd.DataFrame) -> pd.Series:
    operator_column = None
    for candidate in ("operator", "operator_id"):
        if candidate in dataframe.columns:
            operator_column = candidate
            break

    if operator_column is None or "timestamp" not in dataframe.columns:
        return pd.Series(False, index=dataframe.index)

    failed_zero_fee = _failed_zero_fee_mask(dataframe)
    ordered = dataframe.copy()
    ordered["_original_order"] = range(len(ordered))
    ordered["_timestamp"] = pd.to_datetime(
        ordered["timestamp"],
        utc=True,
        errors="coerce",
        format="mixed",
    )
    ordered["_failed_zero_fee"] = failed_zero_fee.astype(int)
    ordered = ordered.sort_values(
        [operator_column, "_timestamp", "_original_order"],
        na_position="last",
    )
    valid = ordered.dropna(subset=["_timestamp"])
    if valid.empty:
        return pd.Series(False, index=dataframe.index)

    cluster_count_30min = (
        valid.set_index("_timestamp")
        .groupby(operator_column)["_failed_zero_fee"]
        .rolling("30min", closed="both")
        .sum()
        .to_numpy()
    )
    cluster_count_60min = (
        valid.set_index("_timestamp")
        .groupby(operator_column)["_failed_zero_fee"]
        .rolling("60min", closed="both")
        .sum()
        .to_numpy()
    )
    clustered = pd.Series(False, index=dataframe.index)
    clustered.loc[valid["_original_order"].to_numpy()] = (
        (cluster_count_30min >= 3) | (cluster_count_60min >= 2)
    )
    return failed_zero_fee & clustered


def _unusual_location_mask(dataframe: pd.DataFrame) -> pd.Series:
    required = {"sender_id", "timestamp", "receiver_wilaya", "amount"}
    if not required <= set(dataframe.columns):
        return pd.Series(False, index=dataframe.index)

    ordered = dataframe.copy()
    ordered["_original_order"] = range(len(ordered))
    ordered["_timestamp"] = pd.to_datetime(
        ordered["timestamp"],
        utc=True,
        errors="coerce",
        format="mixed",
    )
    ordered["_amount"] = _numeric(ordered["amount"])
    if "wilaya_distance_km" in ordered.columns:
        ordered["_distance"] = _numeric(ordered["wilaya_distance_km"])
    else:
        ordered["_distance"] = 0.0
    ordered = ordered.sort_values(
        ["sender_id", "_timestamp", "_original_order"],
        na_position="last",
    )

    prior_sender_count = ordered.groupby("sender_id").cumcount()
    prior_wilaya_count = ordered.groupby(["sender_id", "receiver_wilaya"]).cumcount()
    prior_distance_mean = (
        ordered.groupby("sender_id")["_distance"]
        .expanding()
        .mean()
        .groupby(level=0)
        .shift(1)
        .reset_index(level=0, drop=True)
    ).fillna(0.0)
    receiver_wilaya = ordered["receiver_wilaya"].fillna("").astype(str)
    is_remote = receiver_wilaya.isin(REMOTE_WILAYAS)
    is_far = ordered["_distance"].ge(300)
    distance_jump = ordered["_distance"].ge(prior_distance_mean + 250)
    if "transaction_type" in ordered.columns:
        transaction_type = ordered["transaction_type"].fillna("").astype(str).str.upper()
    else:
        transaction_type = pd.Series("", index=ordered.index)

    mask = (
        prior_sender_count.ge(3)
        & prior_wilaya_count.eq(0)
        & (is_remote | is_far | distance_jump)
        & ordered["_amount"].ge(50_000)
        & transaction_type.isin({"TRANSFER", "CASH_OUT"})
    )

    return (
        pd.DataFrame(
            {
                "_original_order": ordered["_original_order"],
                "mask": mask.astype(bool),
            }
        )
        .sort_values("_original_order")
        ["mask"]
        .reset_index(drop=True)
    )


def _high_amount_type_limit_mask(dataframe: pd.DataFrame) -> pd.Series:
    required = {"transaction_type", "amount"}
    if not required <= set(dataframe.columns):
        return pd.Series(False, index=dataframe.index)

    transaction_type = dataframe["transaction_type"].fillna("").astype(str).str.upper()
    amount = _numeric(dataframe["amount"])
    limits = transaction_type.map(HIGH_AMOUNT_LIMITS_BY_TYPE).fillna(float("inf"))
    return amount.ge(limits).astype(bool)


def _receiver_profile_location_mismatch_mask(dataframe: pd.DataFrame) -> pd.Series:
    required = {"receiver_id", "receiver_wilaya", "sender_id", "sender_wilaya"}
    if not required <= set(dataframe.columns):
        return pd.Series(False, index=dataframe.index)

    source = dataframe.reset_index(drop=True).copy()
    sender_profile = (
        source.groupby("sender_id")["sender_wilaya"]
        .agg(lambda values: values.mode().iloc[0] if not values.mode().empty else None)
        .rename("receiver_profile_wilaya")
    )
    sender_profile_support = (
        source.groupby("sender_id").size().rename("receiver_profile_support")
    )
    receiver_profile = pd.concat([sender_profile, sender_profile_support], axis=1)
    profiled = source.join(receiver_profile, on="receiver_id")

    receiver_wilaya = profiled["receiver_wilaya"].fillna("").astype(str)
    profile_wilaya = profiled["receiver_profile_wilaya"].fillna("").astype(str)
    profile_support = _numeric(profiled["receiver_profile_support"])

    remote_receiver = receiver_wilaya.isin(REMOTE_WILAYAS)
    profile_available = profile_support.ge(1) & profile_wilaya.ne("")
    profile_mismatch = receiver_wilaya.ne(profile_wilaya)

    return (profile_available & remote_receiver & profile_mismatch).astype(bool)


def apply_business_rules(
    dataframe: pd.DataFrame,
    detector_result: pd.DataFrame,
) -> pd.DataFrame:
    """Add conservative business-rule flags to detector predictions.

    The original detector label is preserved. Business rules can only add an
    anomaly flag, not remove one.
    """

    result = detector_result.reset_index(drop=True).copy()
    source = dataframe.reset_index(drop=True).copy()

    if "anomaly_label" not in result.columns:
        raise ValueError("detector_result must contain anomaly_label")

    algorithm = (
        str(result["algorithm"].dropna().iloc[0])
        if "algorithm" in result.columns and not result["algorithm"].dropna().empty
        else "detector"
    )
    model_label_column = (
        "autoencoder_label"
        if algorithm == "autoencoder"
        else f"{algorithm}_model_label"
    )
    result[model_label_column] = result["anomaly_label"].astype(int)
    reasons = _empty_reasons(result.index)

    failed_zero_fee = _failed_zero_fee_mask(source)
    reasons = _append_reason(reasons, failed_zero_fee, "failed_zero_fee")

    high_amount_sender_profile = _high_amount_sender_profile_mask(source)
    reasons = _append_reason(
        reasons,
        high_amount_sender_profile,
        "high_amount_sender_profile",
    )

    high_amount_type_limit = _high_amount_type_limit_mask(source)
    reasons = _append_reason(
        reasons,
        high_amount_type_limit,
        "high_amount_type_limit",
    )

    high_frequency = _high_frequency_mask(source)
    reasons = _append_reason(reasons, high_frequency, "high_frequency_burst")

    structuring = _structuring_mask(source)
    reasons = _append_reason(reasons, structuring, "structuring_pattern")

    operator_outage = _operator_outage_mask(source)
    reasons = _append_reason(reasons, operator_outage, "operator_outage_cluster")

    unusual_location = _unusual_location_mask(source)
    reasons = _append_reason(reasons, unusual_location, "unusual_remote_location")

    receiver_profile_location_mismatch = _receiver_profile_location_mismatch_mask(source)
    reasons = _append_reason(
        reasons,
        receiver_profile_location_mismatch,
        "receiver_profile_location_mismatch",
    )

    result["business_rule_reasons"] = reasons
    result["business_rule_label"] = reasons.ne("").astype(int)
    result["anomaly_label"] = (
        result[model_label_column].astype(int) | result["business_rule_label"].astype(int)
    ).astype(int)
    return result


__all__ = ["apply_business_rules"]
