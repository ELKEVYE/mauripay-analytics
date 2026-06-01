from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mauripay.detection.io import project_backend_root
from mauripay.synthetic.exporters import export_transactions
from mauripay.synthetic.generator import compute_basic_stats, generate_transactions

router = APIRouter(prefix="/ingest", tags=["ingestion"])


class GenerateDatasetRequest(BaseModel):
    rows: int = Field(10_000, gt=0, le=1_000_000)
    output_path: str = Field("data/generated/api_generated_10k.csv")
    accounts: int = Field(1_000, gt=1)
    start_date: str = "2026-01-01"
    end_date: str = "2026-12-31"
    seed: int | None = 42
    anomaly_rate: float = Field(0.02, ge=0, le=1)
    tontine_rate: float = Field(0.001, ge=0, le=1)
    structuring_rate: float = Field(0.003, ge=0, le=1)
    high_frequency_rate: float = Field(0.002, ge=0, le=1)


def _backend_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return project_backend_root() / candidate


@router.get("/health")
def ingestion_health() -> dict[str, str]:
    return {"status": "ready", "module": "ingest"}


@router.post("/generate")
def generate_dataset(request: GenerateDatasetRequest) -> dict[str, object]:
    output_path = _backend_path(request.output_path)

    try:
        transactions = generate_transactions(
            rows=request.rows,
            num_accounts=request.accounts,
            start_date=request.start_date,
            end_date=request.end_date,
            seed=request.seed,
            anomaly_rate=request.anomaly_rate,
            tontine_rate=request.tontine_rate,
            structuring_rate=request.structuring_rate,
            high_frequency_rate=request.high_frequency_rate,
        )
        saved_path = export_transactions(transactions, output_path)
        stats = compute_basic_stats(transactions)
    except Exception as exc:  # pragma: no cover - FastAPI converts this for clients
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "generated",
        "rows": request.rows,
        "output_path": str(saved_path),
        "stats": stats,
    }
