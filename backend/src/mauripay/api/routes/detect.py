from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mauripay.detection.io import project_backend_root
from mauripay.detection.features import LABEL_COLUMNS
from mauripay.detection.metrics import evaluate_by_anomaly_type, evaluate_detection
from mauripay.detection.model_registry import MODEL_FILENAMES
from mauripay.detection.predict import predict_anomalies
from mauripay.detection.train import normalize_label_values, train_models

AlgorithmName = Literal["isolation_forest", "lof"]

router = APIRouter(prefix="/detect", tags=["detection"])


class TrainRequest(BaseModel):
    data_path: str = Field(..., description="CSV/JSON/Parquet path, relative to backend or absolute")
    contamination: float = Field(0.02, gt=0, lt=1)
    n_estimators: int = Field(100, ge=1)
    max_samples: str = "auto"
    random_state: int = 42
    n_neighbors: int = Field(20, ge=1)
    metric: str = "minkowski"
    test_size: float = Field(0.0, ge=0, lt=1)
    split_seed: int = 42
    model_dir: str | None = None
    output_dir: str | None = None


class PredictRequest(BaseModel):
    algorithm: AlgorithmName
    data_path: str = Field(..., description="CSV/JSON/Parquet path, relative to backend or absolute")
    output_path: str | None = Field(None, description="Optional CSV output path")
    model_dir: str | None = Field(None, description="Optional model directory")


def _backend_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return project_backend_root() / candidate


def _load_metadata() -> dict[str, object]:
    metadata_path = project_backend_root() / "models" / "metadata.json"
    if not metadata_path.exists():
        return {}
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def _evaluation_from_predictions(predictions: pd.DataFrame) -> dict[str, object] | None:
    label_column = next(
        (column for column in predictions.columns if column.lower() in LABEL_COLUMNS),
        None,
    )
    if label_column is None:
        return None

    evaluation = evaluate_detection(
        normalize_label_values(predictions[label_column]),
        predictions["anomaly_label"].astype(int).tolist(),
        predictions["anomaly_score"].astype(float).tolist(),
    )
    evaluation["label_column"] = label_column

    if "anomaly_type" in predictions.columns:
        evaluation["by_anomaly_type"] = evaluate_by_anomaly_type(
            predictions["anomaly_type"],
            predictions["anomaly_label"].astype(int).tolist(),
            predictions["anomaly_score"].astype(float).tolist(),
        )

    return evaluation


def _model_status() -> list[dict[str, object]]:
    backend_root = project_backend_root()
    metadata = _load_metadata()
    model_parameters = metadata.get("model_parameters", {}) if metadata else {}
    models = []

    for algorithm, filename in MODEL_FILENAMES.items():
        path = backend_root / "models" / filename
        models.append(
            {
                "algorithm": algorithm,
                "trained": path.exists(),
                "path": str(path),
                "parameters": model_parameters.get(algorithm, {}),
            }
        )

    return models


@router.get("/models")
def list_models() -> dict[str, object]:
    return {
        "available_algorithms": sorted(MODEL_FILENAMES),
        "models": _model_status(),
        "metadata": _load_metadata(),
    }


@router.post("/train")
def train_detection_models(request: TrainRequest) -> dict[str, object]:
    data_path = _backend_path(request.data_path)
    if not data_path.exists():
        raise HTTPException(status_code=404, detail=f"Data file not found: {data_path}")

    try:
        metadata = train_models(
            data_path=data_path,
            contamination=request.contamination,
            n_estimators=request.n_estimators,
            max_samples=request.max_samples,
            random_state=request.random_state,
            n_neighbors=request.n_neighbors,
            metric=request.metric,
            test_size=request.test_size,
            split_seed=request.split_seed,
            model_dir=_backend_path(request.model_dir) if request.model_dir else None,
            output_dir=_backend_path(request.output_dir) if request.output_dir else None,
        )
    except Exception as exc:  # pragma: no cover - FastAPI converts this for clients
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "trained",
        "algorithms": ["isolation_forest", "lof"],
        "metadata": metadata,
    }


@router.post("/predict")
def predict_detection(request: PredictRequest) -> dict[str, object]:
    data_path = _backend_path(request.data_path)
    if not data_path.exists():
        raise HTTPException(status_code=404, detail=f"Data file not found: {data_path}")

    output_path = _backend_path(request.output_path) if request.output_path else None

    try:
        predictions_path = predict_anomalies(
            algorithm=request.algorithm,
            data_path=data_path,
            output=output_path,
            model_dir=_backend_path(request.model_dir) if request.model_dir else None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - FastAPI converts this for clients
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    predictions = pd.read_csv(predictions_path)
    preview_columns = [
        column
        for column in [
            "transaction_id",
            "timestamp",
            "amount",
            "transaction_type",
            "sender_wilaya",
            "receiver_wilaya",
            "anomaly_label",
            "anomaly_score",
            "algorithm",
        ]
        if column in predictions.columns
    ]

    evaluation = _evaluation_from_predictions(predictions)

    return {
        "status": "predicted",
        "algorithm": request.algorithm,
        "rows": len(predictions),
        "output_path": str(predictions_path),
        "anomaly_count": int(predictions["anomaly_label"].sum()),
        "evaluation": evaluation,
        "preview": predictions[preview_columns].head(10).to_dict(orient="records"),
    }
