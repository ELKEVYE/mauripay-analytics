from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Query

from mauripay.api.routes._utils import (
    anomaly_mask,
    failure_mask,
    load_dataset,
    numeric_amount,
)
from mauripay.api.schemas import GeoResponse, HealthResponse

router = APIRouter(prefix="/geo", tags=["geography"])


@router.get("/health", response_model=HealthResponse)
def geo_health() -> HealthResponse:
    return {"status": "ready", "module": "geo"}


@router.get("", response_model=GeoResponse)
def get_geo(
    dataset_path: str = Query(..., description="CSV/JSON/Parquet path, relative to backend or absolute"),
) -> GeoResponse:
    dataframe = load_dataset(dataset_path)
    frame = dataframe.copy()
    frame["amount"] = numeric_amount(frame)
    frame["is_anomaly_api"] = anomaly_mask(frame).astype(int)
    frame["is_failed_api"] = failure_mask(frame).astype(int)

    wilaya_frames = []
    if "sender_wilaya" in frame.columns:
        wilaya_frames.append(
            frame[["sender_wilaya", "amount", "is_anomaly_api", "is_failed_api"]].rename(
                columns={"sender_wilaya": "wilaya"}
            )
        )
    if "receiver_wilaya" in frame.columns:
        wilaya_frames.append(
            frame[["receiver_wilaya", "amount", "is_anomaly_api", "is_failed_api"]].rename(
                columns={"receiver_wilaya": "wilaya"}
            )
        )

    if not wilaya_frames:
        return {"wilayas": []}

    geo_frame = pd.concat(wilaya_frames, ignore_index=True).dropna(subset=["wilaya"])
    grouped = geo_frame.groupby("wilaya").agg(
        transactions=("wilaya", "size"),
        total_amount=("amount", "sum"),
        anomalies_count=("is_anomaly_api", "sum"),
        failure_rate=("is_failed_api", "mean"),
    )
    grouped = grouped.reset_index().sort_values("transactions", ascending=False)

    return {
        "wilayas": [
            {
                "wilaya": str(row["wilaya"]),
                "transactions": int(row["transactions"]),
                "total_amount": float(row["total_amount"]),
                "anomalies_count": int(row["anomalies_count"]),
                "failure_rate": float(row["failure_rate"]),
            }
            for row in grouped.to_dict(orient="records")
        ]
    }
