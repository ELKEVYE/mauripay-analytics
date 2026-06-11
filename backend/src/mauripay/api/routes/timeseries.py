from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Query

from mauripay.api.routes._utils import (
    anomaly_mask,
    load_dataset,
    numeric_amount,
    require_columns,
)
from mauripay.api.schemas import HealthResponse, TimeseriesResponse

router = APIRouter(prefix="/timeseries", tags=["timeseries"])


@router.get("/health", response_model=HealthResponse)
def timeseries_health() -> HealthResponse:
    return {"status": "ready", "module": "timeseries"}


@router.get("", response_model=TimeseriesResponse)
def get_timeseries(
    dataset_path: str = Query(..., description="CSV/JSON/Parquet path, relative to backend or absolute"),
) -> TimeseriesResponse:
    dataframe = load_dataset(dataset_path)
    require_columns(dataframe, ["timestamp", "amount"])
    frame = dataframe.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
    frame = frame.dropna(subset=["timestamp"])
    frame["amount"] = numeric_amount(frame)
    frame["is_anomaly_api"] = anomaly_mask(frame).astype(int)
    frame["day"] = frame["timestamp"].dt.date.astype(str)
    frame["hour"] = frame["timestamp"].dt.hour
    frame["week"] = frame["timestamp"].dt.tz_convert(None).dt.to_period("W").astype(str)

    transactions_by_day = (
        frame.groupby("day").size().reset_index(name="transactions").to_dict(orient="records")
    )
    amounts_by_hour = (
        frame.groupby("hour")["amount"].sum().reset_index(name="total_amount").to_dict(orient="records")
    )
    anomalies_by_week = (
        frame.groupby("week")["is_anomaly_api"].sum().reset_index(name="anomalies").to_dict(orient="records")
    )

    if "operator" in frame.columns:
        volume_by_operator = (
            frame.groupby("operator").size().reset_index(name="transactions").to_dict(orient="records")
        )
    else:
        volume_by_operator = []

    wilaya_columns = [column for column in ["sender_wilaya", "receiver_wilaya"] if column in frame.columns]
    if wilaya_columns:
        wilayas = pd.concat([frame[column].rename("wilaya") for column in wilaya_columns])
        volume_by_wilaya = wilayas.value_counts().reset_index(name="transactions").to_dict(orient="records")
    else:
        volume_by_wilaya = []

    return {
        "transactions_by_day": transactions_by_day,
        "amounts_by_hour": amounts_by_hour,
        "anomalies_by_week": anomalies_by_week,
        "volume_by_operator": volume_by_operator,
        "volume_by_wilaya": volume_by_wilaya,
    }
