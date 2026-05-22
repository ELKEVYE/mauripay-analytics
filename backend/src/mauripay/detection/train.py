from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mauripay.detection.features import LABEL_COLUMNS, TransactionFeatureEngineer
from mauripay.detection.iforest import IsolationForestDetector
from mauripay.detection.io import load_table, project_backend_root
from mauripay.detection.lof import LOFDetector
from mauripay.detection.metrics import evaluate_detection
from mauripay.detection.model_registry import model_path

try:
    from mauripay.synthetic.validate import validate_columns, validate_pydantic_rows
except ImportError:  # pragma: no cover - keeps detection usable without synthetic module
    validate_columns = None
    validate_pydantic_rows = None


def find_label_column(columns: list[str]) -> str | None:
    for column in columns:
        if column.lower() in LABEL_COLUMNS:
            return column
    return None


def normalize_label_values(values) -> list[int]:
    lowered = values.astype(str).str.lower()
    return lowered.isin(["true", "1", "yes", "anomaly", "fraud"]).astype(int).tolist()


def train_models(
    data_path: str | Path,
    model_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    contamination: float = 0.02,
    n_estimators: int = 100,
    max_samples: str = "auto",
    random_state: int = 42,
    n_neighbors: int = 20,
    metric: str = "minkowski",
) -> dict[str, Any]:
    backend_root = project_backend_root()
    model_directory = Path(model_dir) if model_dir else backend_root / "models"
    output_directory = Path(output_dir) if output_dir else backend_root / "outputs"
    model_directory.mkdir(parents=True, exist_ok=True)
    output_directory.mkdir(parents=True, exist_ok=True)

    df = load_table(data_path)
    validation_report: dict[str, Any] = {}
    if validate_columns is not None:
        validation_report["columns"] = validate_columns(df)
    if validate_pydantic_rows is not None:
        validation_report["pydantic_rows"] = validate_pydantic_rows(df)

    feature_engineer = TransactionFeatureEngineer()
    X = feature_engineer.fit_transform(df)

    if len(df) <= n_neighbors:
        raise ValueError(
            f"Dataset has {len(df)} rows but LOF n_neighbors={n_neighbors}. "
            "Use more rows or lower --n-neighbors."
        )

    detectors = {
        "isolation_forest": IsolationForestDetector(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=random_state,
            max_samples=max_samples,
        ),
        "lof": LOFDetector(
            n_neighbors=n_neighbors,
            contamination=contamination,
            metric=metric,
        ),
    }

    metadata: dict[str, Any] = {
        "training_date": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(Path(data_path)),
        "number_of_rows": len(df),
        "contamination": contamination,
        "feature_engineering": feature_engineer.metadata(),
        "validation": validation_report,
        "model_parameters": {},
        "models": {},
    }

    label_column = find_label_column(list(df.columns))
    y_true = normalize_label_values(df[label_column]) if label_column else None

    for name, detector in detectors.items():
        detector.fit(X)
        saved_path = detector.save(model_path(model_directory, name))
        metadata["models"][name] = str(saved_path)
        metadata["model_parameters"][name] = detector.parameters

        if y_true is not None:
            result = detector.results(X)
            evaluation = evaluate_detection(
                y_true,
                result["anomaly_label"].tolist(),
                result["anomaly_score"].tolist(),
            )
            evaluation["label_column"] = label_column
            eval_path = output_directory / f"evaluation_{name}.json"
            eval_path.write_text(
                json.dumps(evaluation, indent=2, default=str),
                encoding="utf-8",
            )

    preprocessor_path = model_directory / "preprocessor.joblib"
    feature_engineer.save(preprocessor_path)
    metadata["preprocessor"] = str(preprocessor_path)
    metadata["label_column_used_for_evaluation"] = label_column

    metadata_path = model_directory / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
    return metadata


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train MauriPay anomaly detectors")
    parser.add_argument("--data", required=True, help="Input CSV/JSON/Parquet dataset")
    parser.add_argument("--model-dir", default=None, help="Directory for saved models")
    parser.add_argument("--output-dir", default=None, help="Directory for evaluation JSON")
    parser.add_argument("--contamination", type=float, default=0.02)
    parser.add_argument("--n-estimators", type=int, default=100)
    parser.add_argument("--max-samples", default="auto")
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--n-neighbors", type=int, default=20)
    parser.add_argument("--metric", default="minkowski")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    metadata = train_models(
        data_path=args.data,
        model_dir=args.model_dir,
        output_dir=args.output_dir,
        contamination=args.contamination,
        n_estimators=args.n_estimators,
        max_samples=args.max_samples,
        random_state=args.random_state,
        n_neighbors=args.n_neighbors,
        metric=args.metric,
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
