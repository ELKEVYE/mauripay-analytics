from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.model_selection import train_test_split

from mauripay.detection.features import LABEL_COLUMNS, TransactionFeatureEngineer
from mauripay.detection.iforest import IsolationForestDetector
from mauripay.detection.io import load_table, project_backend_root
from mauripay.detection.lof import LOFDetector
from mauripay.detection.metrics import evaluate_by_anomaly_type, evaluate_detection
from mauripay.detection.model_registry import model_path
from mauripay.detection.train_autoencoder import train_autoencoder

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


def split_dataframe(
    df: pd.DataFrame,
    label_column: str | None,
    test_size: float,
    split_seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if test_size <= 0:
        return df.copy(), df.copy()

    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1, or 0 to disable splitting")

    stratify = None
    if label_column is not None:
        labels = normalize_label_values(df[label_column])
        if len(set(labels)) > 1:
            stratify = labels

    train_df, eval_df = train_test_split(
        df,
        test_size=test_size,
        random_state=split_seed,
        shuffle=True,
        stratify=stratify,
    )
    return train_df.reset_index(drop=True), eval_df.reset_index(drop=True)


def evaluate_detector(
    detector,
    X,
    eval_df: pd.DataFrame,
    label_column: str,
) -> dict[str, object]:
    result = detector.results(X)
    y_true = normalize_label_values(eval_df[label_column])
    evaluation = evaluate_detection(
        y_true,
        result["anomaly_label"].tolist(),
        result["anomaly_score"].tolist(),
    )
    evaluation["label_column"] = label_column

    if "anomaly_type" in eval_df.columns:
        evaluation["by_anomaly_type"] = evaluate_by_anomaly_type(
            eval_df["anomaly_type"],
            result["anomaly_label"].tolist(),
            result["anomaly_score"].tolist(),
        )

    return evaluation


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
    include_autoencoder: bool = False,
    autoencoder_epochs: int = 50,
    autoencoder_batch_size: int = 128,
    autoencoder_threshold_percentile: float = 98.0,
    autoencoder_optimize_threshold: bool = True,
    autoencoder_device: str | None = None,
    test_size: float = 0.0,
    split_seed: int = 42,
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

    label_column = find_label_column(list(df.columns))
    train_df, eval_df = split_dataframe(df, label_column, test_size, split_seed)

    if len(train_df) <= n_neighbors:
        raise ValueError(
            f"Training dataset has {len(train_df)} rows but LOF n_neighbors={n_neighbors}. "
            "Use more rows or lower --n-neighbors."
        )

    feature_engineer = TransactionFeatureEngineer()
    X_train = feature_engineer.fit_transform(train_df)
    X_eval = feature_engineer.transform(eval_df)

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
        "training_rows": len(train_df),
        "evaluation_rows": len(eval_df),
        "evaluation_mode": "holdout" if test_size > 0 else "training_data",
        "test_size": test_size,
        "split_seed": split_seed,
        "contamination": contamination,
        "feature_engineering": feature_engineer.metadata(),
        "validation": validation_report,
        "model_parameters": {},
        "models": {},
        "evaluations": {},
    }

    for name, detector in detectors.items():
        detector.fit(X_train)
        saved_path = detector.save(model_path(model_directory, name))
        metadata["models"][name] = str(saved_path)
        metadata["model_parameters"][name] = detector.parameters

        if label_column is not None:
            evaluation = evaluate_detector(detector, X_eval, eval_df, label_column)
            metadata["evaluations"][name] = evaluation
            eval_path = output_directory / f"evaluation_{name}.json"
            eval_path.write_text(
                json.dumps(evaluation, indent=2, default=str),
                encoding="utf-8",
            )

    preprocessor_path = model_directory / "preprocessor.joblib"
    feature_engineer.save(preprocessor_path)
    metadata["preprocessor"] = str(preprocessor_path)
    metadata["label_column_used_for_evaluation"] = label_column

    if include_autoencoder:
        autoencoder_metadata = train_autoencoder(
            data_path=data_path,
            model_dir=model_directory,
            output_dir=output_directory,
            epochs=autoencoder_epochs,
            batch_size=autoencoder_batch_size,
            threshold_percentile=autoencoder_threshold_percentile,
            optimize_decision_threshold=autoencoder_optimize_threshold,
            random_state=random_state,
            device=autoencoder_device,
        )
        metadata["models"]["autoencoder"] = autoencoder_metadata["model"]
        metadata["model_parameters"]["autoencoder"] = autoencoder_metadata[
            "model_parameters"
        ]
        metadata["autoencoder"] = {
            "preprocessor": autoencoder_metadata["preprocessor"],
            "metadata": str(model_directory / "metadata_autoencoder.json"),
            "evaluation": autoencoder_metadata["evaluation"],
            "normal_rows_used_for_training": autoencoder_metadata[
                "normal_rows_used_for_training"
            ],
        }

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
    parser.add_argument(
        "--include-autoencoder",
        action="store_true",
        help="Also train the autoencoder after IF/LOF. Requires a label column.",
    )
    parser.add_argument("--autoencoder-epochs", type=int, default=50)
    parser.add_argument("--autoencoder-batch-size", type=int, default=128)
    parser.add_argument("--autoencoder-threshold-percentile", type=float, default=98.0)
    parser.add_argument(
        "--no-autoencoder-threshold-optimization",
        action="store_true",
        help="Keep the autoencoder percentile threshold instead of optimizing F1.",
    )
    parser.add_argument("--autoencoder-device", default=None, choices=["cpu", "cuda"])
    parser.add_argument("--test-size", type=float, default=0.0)
    parser.add_argument("--split-seed", type=int, default=42)
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
        include_autoencoder=args.include_autoencoder,
        autoencoder_epochs=args.autoencoder_epochs,
        autoencoder_batch_size=args.autoencoder_batch_size,
        autoencoder_threshold_percentile=args.autoencoder_threshold_percentile,
        autoencoder_optimize_threshold=not args.no_autoencoder_threshold_optimization,
        autoencoder_device=args.autoencoder_device,
        test_size=args.test_size,
        split_seed=args.split_seed,
    )
    print(json.dumps(metadata, indent=2, default=str))


if __name__ == "__main__":
    main()
