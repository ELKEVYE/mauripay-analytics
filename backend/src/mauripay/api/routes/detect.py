from __future__ import annotations

import gc
import json
import logging
import re
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException

from mauripay.api.routes._utils import backend_path
from mauripay.api.schemas import (
    DetectionRunResponse,
    ModelStatusResponse,
    PredictAllRequest,
    PredictAllResponse,
    PredictRequest,
    TrainRequest,
    TrainResponse,
)
from mauripay.detection.io import load_table, project_backend_root
from mauripay.detection.features import LABEL_COLUMNS, TransactionFeatureEngineer
from mauripay.detection.metrics import evaluate_by_anomaly_type, evaluate_detection
from mauripay.detection.model_registry import MODEL_FILENAMES
from mauripay.detection.predict import (
    ENSEMBLE_ALGORITHMS,
    combine_ensemble_results_with_frame,
    predict_anomalies,
    predict_anomalies_from_frame,
)
from mauripay.detection.train import normalize_label_values, train_models

router = APIRouter(prefix="/detect", tags=["detection"])
logger = logging.getLogger(__name__)
PREDICTION_ALGORITHMS = (
    "isolation_forest",
    "lof",
    "autoencoder",
    "ensemble",
)
PREDICT_ALL_MODEL_PREVIEW_LIMIT = 20
PREDICT_ALL_ENSEMBLE_PREVIEW_LIMIT: int | None = None


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
            "trained": all(
                (backend_root / "models" / MODEL_FILENAMES[algorithm]).exists()
                for algorithm in ENSEMBLE_ALGORITHMS
            ),
            "path": str(backend_root / "models"),
            "parameters": {
                "strategy": "classical_consensus_plus_autoencoder_only",
                "members": list(ENSEMBLE_ALGORITHMS),
                "rule": "(isolation_forest=1 AND lof=1) OR "
                "(autoencoder=1 AND isolation_forest=0 AND lof=0)",
            },
        }
    )
    return models


def _prediction_preview(
    predictions: pd.DataFrame,
    limit: int | None = 20,
) -> list[dict[str, object]]:
    preview_columns = [
        column
        for column in [
            "transaction_id",
            "timestamp",
            "amount",
            "transaction_type",
            "channel",
            "anomaly_type",
            "operator",
            "status",
            "sender_wilaya",
            "receiver_wilaya",
            "anomaly_label",
            "anomaly_score",
            "business_rule_reasons",
            "algorithm",
        ]
        if column in predictions.columns
    ]
    anomalies = predictions.loc[predictions["anomaly_label"].astype(int).eq(1)]
    if limit is not None:
        anomalies = anomalies.head(limit)
    return anomalies[preview_columns].to_dict(orient="records")


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
        "preview": _prediction_preview(predictions, limit=10),
    }


@router.post("", response_model=DetectionRunResponse)
def detect_anomalies(request: PredictRequest) -> DetectionRunResponse:
    """Compatibility endpoint for clients expecting POST /detect."""
    return predict_detection(request)


@router.post("/predict-all", response_model=PredictAllResponse)
def predict_all_models(request: PredictAllRequest) -> PredictAllResponse:
    data_path = _backend_path(request.data_path)
    if not data_path.exists():
        raise HTTPException(status_code=404, detail=f"Data file not found: {data_path}")

    backend_root = project_backend_root()
    model_dir = backend_root / "models"
    missing = [
        algorithm
        for algorithm in PREDICTION_ALGORITHMS
        if algorithm != "ensemble"
        if not (model_dir / MODEL_FILENAMES[algorithm]).exists()
    ]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Missing trained models: {', '.join(missing)}",
        )

    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", data_path.stem).strip("_") or "dataset"
    output_dir = backend_root / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Loading prediction dataset once: %s", data_path)
    dataframe = load_table(data_path)
    results = []
    prediction_results: dict[str, pd.DataFrame] = {}

    logger.info("Building shared classical feature matrix for %s rows", len(dataframe))
    classical_preprocessor = TransactionFeatureEngineer.load(
        model_dir / "preprocessor.joblib"
    )
    classical_X = classical_preprocessor.transform(dataframe)

    for algorithm in ("isolation_forest", "lof"):
        logger.info("Running %s prediction", algorithm)
        output_path = output_dir / f"{safe_stem}_{algorithm}.csv"
        try:
            predictions_path, detector_result = predict_anomalies_from_frame(
                algorithm=algorithm,
                df=dataframe,
                data_path=data_path,
                output=output_path,
                model_dir=model_dir,
                X=classical_X,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"{algorithm}: {exc}",
            ) from exc

        preview_frame = pd.concat(
            [dataframe.reset_index(drop=True), detector_result], axis=1
        )
        results.append(
            {
                "algorithm": algorithm,
                "total_transactions": len(detector_result),
                "anomalies_detected": int(detector_result["anomaly_label"].sum()),
                "output_path": predictions_path.relative_to(backend_root).as_posix(),
                "preview": _prediction_preview(
                    preview_frame,
                    limit=PREDICT_ALL_MODEL_PREVIEW_LIMIT,
                ),
            }
        )
        prediction_results[algorithm] = detector_result[
            ["anomaly_label", "anomaly_score"]
        ].copy()
        del preview_frame, detector_result

    del classical_X, classical_preprocessor
    gc.collect()

    logger.info("Building autoencoder feature matrix for %s rows", len(dataframe))
    autoencoder_preprocessor = TransactionFeatureEngineer.load(
        model_dir / "autoencoder_preprocessor.joblib"
    )
    autoencoder_X = autoencoder_preprocessor.transform(dataframe)
    output_path = output_dir / f"{safe_stem}_autoencoder.csv"
    try:
        predictions_path, detector_result = predict_anomalies_from_frame(
            algorithm="autoencoder",
            df=dataframe,
            data_path=data_path,
            output=output_path,
            model_dir=model_dir,
            X=autoencoder_X,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"autoencoder: {exc}") from exc

    preview_frame = pd.concat(
        [dataframe.reset_index(drop=True), detector_result], axis=1
    )
    results.append(
        {
            "algorithm": "autoencoder",
            "total_transactions": len(detector_result),
            "anomalies_detected": int(detector_result["anomaly_label"].sum()),
            "output_path": predictions_path.relative_to(backend_root).as_posix(),
            "preview": _prediction_preview(
                preview_frame,
                limit=PREDICT_ALL_MODEL_PREVIEW_LIMIT,
            ),
        }
    )
    prediction_results["autoencoder"] = detector_result[
        ["anomaly_label", "anomaly_score"]
    ].copy()
    del autoencoder_X, autoencoder_preprocessor, preview_frame, detector_result
    gc.collect()

    logger.info("Combining ensemble predictions in memory")
    ensemble_path, ensemble_predictions = combine_ensemble_results_with_frame(
        df=dataframe,
        data_path=data_path,
        prediction_results=prediction_results,
        output=output_dir / f"{safe_stem}_ensemble.csv",
    )
    results.append(
        {
            "algorithm": "ensemble",
            "total_transactions": len(ensemble_predictions),
            "anomalies_detected": int(ensemble_predictions["anomaly_label"].sum()),
            "output_path": ensemble_path.relative_to(backend_root).as_posix(),
            "preview": _prediction_preview(
                ensemble_predictions,
                limit=PREDICT_ALL_ENSEMBLE_PREVIEW_LIMIT,
            ),
        }
    )

    return {
        "status": "predicted",
        "data_path": request.data_path,
        "results": results,
    }
