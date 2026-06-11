from __future__ import annotations

import json
from pathlib import Path
from shutil import copyfileobj

from fastapi import APIRouter, File, HTTPException, UploadFile

from mauripay.api.routes._utils import backend_path
from mauripay.api.schemas import (
    GenerateDatasetRequest,
    GenerateDatasetResponse,
    HealthResponse,
    IngestResponse,
)
from mauripay.detection.io import project_backend_root
from mauripay.ingestion.common import IngestionError, IngestionResult
from mauripay.ingestion.loader import load_transactions
from mauripay.synthetic.exporters import export_transactions
from mauripay.synthetic.generator import compute_basic_stats, generate_transactions

router = APIRouter(prefix="/ingest", tags=["ingestion"])


def _backend_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return project_backend_root() / candidate


def _serialize_error(error: IngestionError) -> dict[str, object]:
    return {
        "source": error.source,
        "row_number": error.row_number,
        "errors": error.errors,
        "payload": error.payload,
    }


def _write_errors_file(result: IngestionResult, filename: str) -> str | None:
    if not result.errors:
        return None

    reports_dir = project_backend_root() / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = Path(filename).stem or "ingestion"
    errors_path = reports_dir / f"{safe_stem}_ingestion_errors.json"
    payload = [_serialize_error(error) for error in result.errors]
    errors_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return str(errors_path.relative_to(project_backend_root()))


@router.get("/health", response_model=HealthResponse)
def ingestion_health() -> HealthResponse:
    return {"status": "ready", "module": "ingest"}


@router.post("", response_model=IngestResponse)
def ingest_file(file: UploadFile = File(...)) -> IngestResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".csv", ".json", ".jsonl", ".parquet"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Use CSV, JSON, JSONL or Parquet.",
        )

    uploads_dir = backend_path("data/uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    saved_path = uploads_dir / Path(file.filename or f"upload{suffix}").name

    try:
        with saved_path.open("wb") as output:
            copyfileobj(file.file, output)
        result = load_transactions(saved_path, report=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        file.file.close()

    if not isinstance(result, IngestionResult):
        raise HTTPException(status_code=500, detail="Unexpected ingestion result")

    errors_file = _write_errors_file(result, saved_path.name)
    return {
        "rows": result.total_rows,
        "valid_rows": result.valid_rows,
        "invalid_rows": result.invalid_rows,
        "errors_file": errors_file,
    }


@router.post("/generate", response_model=GenerateDatasetResponse)
def generate_dataset(request: GenerateDatasetRequest) -> GenerateDatasetResponse:
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
