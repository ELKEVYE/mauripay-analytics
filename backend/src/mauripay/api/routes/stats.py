from __future__ import annotations

from fastapi import APIRouter, Query

from mauripay.api.routes._utils import (
    anomaly_mask,
    failure_mask,
    load_dataset,
    numeric_amount,
    value_counts,
)
from mauripay.api.schemas import HealthResponse, StatsResponse

router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("/health", response_model=HealthResponse)
def stats_health() -> HealthResponse:
    return {"status": "ready", "module": "stats"}


@router.get("", response_model=StatsResponse)
def get_stats(
    dataset_path: str = Query(..., description="CSV/JSON/Parquet path, relative to backend or absolute"),
) -> StatsResponse:
    dataframe = load_dataset(dataset_path)
    amounts = numeric_amount(dataframe)
    total = len(dataframe)

    return {
        "total_transactions": total,
        "total_amount": float(amounts.sum()),
        "average_amount": float(amounts.mean()) if total else 0.0,
        "anomalies_count": int(anomaly_mask(dataframe).sum()),
        "failure_rate": float(failure_mask(dataframe).mean()) if total else 0.0,
        "by_type": value_counts(dataframe, "transaction_type"),
        "by_channel": value_counts(dataframe, "channel"),
    }
