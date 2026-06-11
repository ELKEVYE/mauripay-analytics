from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException

from mauripay.api.routes._utils import backend_path
from mauripay.api.schemas import (
    DetectionRunResponse,
    ModelStatusResponse,
    PredictRequest,
    TrainRequest,
    TrainResponse,
)
from mauripay.detection.io import load_table, project_backend_root
from mauripay.detection.features import LABEL_COLUMNS
from mauripay.detection.metrics import evaluate_by_anomaly_type, evaluate_detection
from mauripay.detection.model_registry import MODEL_FILENAMES
from mauripay.detection.predict import predict_anomalies
from mauripay.detection.train import normalize_label_values, train_models

router = APIRouter(prefix="/detect", tags=["detection"])


def _backend_path(path: str | Path) -> Path:
    return backend_path(path)


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

    trained_count = sum(1 for model in models if model["trained"])
    models.append(
        {
            "algorithm": "ensemble",
            "trained": trained_count > 0,
            "path": str(backend_root / "models"),
            "parameters": {"strategy": "majority_vote", "members": trained_count},
        }
    )
    return models


def _predict_one(
    algorithm: str,
    data_path: Path,
    output_path: Path | None,
    model_dir: Path | None,
) -> Path:
    return predict_anomalies(
        algorithm=algorithm,
        data_path=data_path,
        output=output_path,
        model_dir=model_dir,
    )


def _predict_ensemble(
    data_path: Path,
    output_path: Path | None,
    model_dir: Path | None,
) -> Path:
    backend_root = project_backend_root()
    model_directory = model_dir or backend_root / "models"
    output = output_path or backend_root / "outputs" / "anomaly_predictions_ensemble.csv"
    output.parent.mkdir(parents=True, exist_ok=True)

    algorithms = [
        algorithm
        for algorithm, filename in MODEL_FILENAMES.items()
        if (model_directory / filename).exists()
    ]
    if not algorithms:
        raise FileNotFoundError(f"No trained model found in {model_directory}")

    predictions = []
    for algorithm in algorithms:
        path = _predict_one(
            algorithm=algorithm,
            data_path=data_path,
            output_path=output.parent / f"_ensemble_{algorithm}.csv",
            model_dir=model_directory,
        )
        frame = pd.read_csv(path)
        predictions.append(
            frame[["anomaly_label", "anomaly_score"]].rename(
                columns={
                    "anomaly_label": f"{algorithm}_label",
                    "anomaly_score": f"{algorithm}_score",
                }
            )
        )

    base = load_table(data_path).reset_index(drop=True)
    votes = pd.concat([item.filter(like="_label") for item in predictions], axis=1)
    scores = pd.concat([item.filter(like="_score") for item in predictions], axis=1)
    ensemble_result = pd.concat([base, *predictions], axis=1)
    ensemble_result["ensemble_vote_count"] = votes.sum(axis=1).astype(int)
    ensemble_result["anomaly_score"] = scores.mean(axis=1)
    ensemble_result["anomaly_label"] = (ensemble_result["ensemble_vote_count"] >= 1).astype(int)
    ensemble_result["algorithm"] = "ensemble"
    ensemble_result.to_csv(output, index=False)

    evaluation = _evaluation_from_predictions(ensemble_result)
    if evaluation is not None:
        evaluation["dataset_path"] = str(data_path)
        evaluation["prediction_file"] = str(output)
        evaluation_path = output.parent / "evaluation_ensemble.json"
        evaluation_path.write_text(
            json.dumps(evaluation, indent=2, default=str),
            encoding="utf-8",
        )

    return output


@router.get("/models", response_model=ModelStatusResponse)
def list_models() -> ModelStatusResponse:
    return {
        "available_algorithms": sorted([*MODEL_FILENAMES, "ensemble"]),
        "models": _model_status(),
        "metadata": _load_metadata(),
    }


@router.post("/train", response_model=TrainResponse)
def train_detection_models(request: TrainRequest) -> TrainResponse:
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
            include_autoencoder=request.include_autoencoder,
            lof_max_train_rows=request.lof_max_train_rows,
            autoencoder_epochs=request.autoencoder_epochs,
            autoencoder_batch_size=request.autoencoder_batch_size,
            autoencoder_threshold_percentile=request.autoencoder_threshold_percentile,
            autoencoder_optimize_threshold=request.autoencoder_optimize_threshold,
            autoencoder_device=request.autoencoder_device,
            model_dir=_backend_path(request.model_dir) if request.model_dir else None,
            output_dir=_backend_path(request.output_dir) if request.output_dir else None,
        )
    except Exception as exc:  # pragma: no cover - FastAPI converts this for clients
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "trained",
        "algorithms": ["isolation_forest", "lof"]
        + (["autoencoder"] if request.include_autoencoder else []),
        "metadata": metadata,
    }


@router.post("/predict", response_model=DetectionRunResponse)
def predict_detection(request: PredictRequest) -> DetectionRunResponse:
    data_path = _backend_path(request.data_path)
    if not data_path.exists():
        raise HTTPException(status_code=404, detail=f"Data file not found: {data_path}")

    output_path = _backend_path(request.output_path) if request.output_path else None

    try:
        model_dir = _backend_path(request.model_dir) if request.model_dir else None
        if request.algorithm == "ensemble":
            predictions_path = _predict_ensemble(data_path, output_path, model_dir)
        else:
            predictions_path = predict_anomalies(
                algorithm=request.algorithm,
                data_path=data_path,
                output=output_path,
                model_dir=model_dir,
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
        "total_transactions": len(predictions),
        "anomalies_detected": int(predictions["anomaly_label"].sum()),
        "results_path": str(predictions_path),
        "evaluation": evaluation,
        "preview": predictions[preview_columns].head(10).to_dict(orient="records"),
    }
