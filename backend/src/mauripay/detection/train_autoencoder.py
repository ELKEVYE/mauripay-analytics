from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from mauripay.detection.autoencoder import AutoencoderDetector
from mauripay.detection.business_rules import apply_business_rules
from mauripay.detection.features import LABEL_COLUMNS, TransactionFeatureEngineer
from mauripay.detection.io import load_table, project_backend_root
from mauripay.detection.metrics import evaluate_detection


def find_label_column(columns: list[str]) -> str | None:
    for column in columns:
        if column.lower() in LABEL_COLUMNS:
            return column
    return None


def normalize_label_values(values) -> list[int]:
    lowered = values.astype(str).str.lower()
    return lowered.isin(["true", "1", "yes", "anomaly", "fraud"]).astype(int).tolist()


def optimize_threshold(
    y_true: list[int],
    anomaly_scores: list[float] | np.ndarray,
    percentiles: list[float] | np.ndarray | None = None,
) -> dict[str, Any]:
    """Choose the reconstruction-error threshold that maximizes F1-score."""
    score_array = np.asarray(anomaly_scores, dtype=float)
    if score_array.size == 0:
        raise ValueError("Cannot optimize threshold with no anomaly scores")

    percentile_grid = (
        np.asarray(percentiles, dtype=float)
        if percentiles is not None
        else np.arange(80.0, 99.6, 0.5)
    )
    percentile_grid = percentile_grid[
        (percentile_grid > 0)
        & (percentile_grid < 100)
        & np.isfinite(percentile_grid)
    ]
    if percentile_grid.size == 0:
        raise ValueError("Threshold optimization requires percentiles between 0 and 100")

    candidates: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    best_sort_key: tuple[float, float, float] | None = None

    for percentile in percentile_grid:
        threshold = float(np.percentile(score_array, percentile))
        y_pred = (score_array > threshold).astype(int).tolist()
        metrics = evaluate_detection(y_true, y_pred, score_array.tolist())
        candidate = {
            "percentile": float(percentile),
            "threshold": threshold,
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1_score": metrics["f1_score"],
            "confusion_matrix": metrics["confusion_matrix"],
        }
        candidates.append(candidate)

        sort_key = (
            float(metrics["f1_score"]),
            float(metrics["recall"]),
            float(metrics["precision"]),
        )
        if best is None or best_sort_key is None or sort_key > best_sort_key:
            best = candidate
            best_sort_key = sort_key

    if best is None:
        raise RuntimeError("Threshold optimization did not produce any candidate")

    return {
        "selected": best,
        "candidates": candidates,
        "objective": "maximize_f1_then_recall_then_precision",
    }


def build_error_analysis(
    df: pd.DataFrame,
    y_true: list[int],
    result: pd.DataFrame,
    output_directory: Path,
    label_column: str,
) -> dict[str, Any]:
    """Export false-positive and false-negative details for model improvement."""
    analysis_df = df.reset_index(drop=True).copy()
    analysis_df["true_label"] = y_true
    analysis_df["predicted_label"] = result["anomaly_label"].astype(int).tolist()
    analysis_df["anomaly_score"] = result["anomaly_score"].astype(float).tolist()
    analysis_df["classification_error"] = np.select(
        [
            (analysis_df["true_label"] == 0) & (analysis_df["predicted_label"] == 1),
            (analysis_df["true_label"] == 1) & (analysis_df["predicted_label"] == 0),
        ],
        ["false_positive", "false_negative"],
        default="correct",
    )

    error_rows = analysis_df[analysis_df["classification_error"] != "correct"].copy()
    error_path = output_directory / "autoencoder_classification_errors.csv"
    error_rows.to_csv(error_path, index=False)

    def value_counts(column: str, frame: pd.DataFrame) -> dict[str, int]:
        if column not in frame.columns or frame.empty:
            return {}
        return {
            str(key): int(value)
            for key, value in frame[column].fillna("UNKNOWN").value_counts().head(10).items()
        }

    false_positives = error_rows[error_rows["classification_error"] == "false_positive"]
    false_negatives = error_rows[error_rows["classification_error"] == "false_negative"]
    business_columns = [
        "anomaly_type",
        "transaction_type",
        "channel",
        "operator",
        "status",
        "sender_wilaya",
        "receiver_wilaya",
    ]

    def clean_summary(frame: pd.DataFrame) -> dict[str, float | None]:
        summary = frame["anomaly_score"].describe().to_dict()
        return {
            str(key): None if pd.isna(value) else float(value)
            for key, value in summary.items()
        }

    analysis = {
        "label_column": label_column,
        "total_rows": int(len(analysis_df)),
        "error_rows": int(len(error_rows)),
        "false_positives": int(len(false_positives)),
        "false_negatives": int(len(false_negatives)),
        "error_file": str(error_path),
        "false_positive_rate_on_normal": (
            float(len(false_positives) / max((analysis_df["true_label"] == 0).sum(), 1))
        ),
        "false_negative_rate_on_anomalies": (
            float(len(false_negatives) / max((analysis_df["true_label"] == 1).sum(), 1))
        ),
        "score_summary": {
            "correct": clean_summary(
                analysis_df[analysis_df["classification_error"] == "correct"]
            ),
            "false_positive": clean_summary(false_positives),
            "false_negative": clean_summary(false_negatives),
        },
        "false_positive_top_values": {
            column: value_counts(column, false_positives) for column in business_columns
        },
        "false_negative_top_values": {
            column: value_counts(column, false_negatives) for column in business_columns
        },
    }

    analysis_path = output_directory / "autoencoder_error_analysis.json"
    analysis["analysis_file"] = str(analysis_path)
    analysis_path.write_text(json.dumps(analysis, indent=2, default=str), encoding="utf-8")
    return analysis


def train_autoencoder(
    data_path: str | Path,
    model_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    encoding_dim: int = 8,
    hidden_dims: list[int] | tuple[int, int] = (32, 16),
    learning_rate: float = 1e-3,
    epochs: int = 50,
    batch_size: int = 128,
    threshold_percentile: float = 98.0,
    optimize_decision_threshold: bool = True,
    random_state: int | None = 42,
    device: str | None = None,
) -> dict[str, Any]:
    backend_root = project_backend_root()
    model_directory = Path(model_dir) if model_dir else backend_root / "models"
    output_directory = Path(output_dir) if output_dir else backend_root / "outputs"
    model_directory.mkdir(parents=True, exist_ok=True)
    output_directory.mkdir(parents=True, exist_ok=True)

    df = load_table(data_path)
    label_column = find_label_column(list(df.columns))
    if label_column is None:
        raise ValueError(
            "Autoencoder training requires a label column to select normal rows. "
            f"Expected one of: {', '.join(sorted(LABEL_COLUMNS))}"
        )

    y_true = normalize_label_values(df[label_column])
    normal_mask = [label == 0 for label in y_true]
    df_normal = df.loc[normal_mask].copy()
    if df_normal.empty:
        raise ValueError("No normal transactions found for autoencoder training")

    feature_engineer = TransactionFeatureEngineer()
    X_train_normal = feature_engineer.fit_transform(df_normal)

    detector = AutoencoderDetector(
        encoding_dim=encoding_dim,
        hidden_dims=hidden_dims,
        learning_rate=learning_rate,
        epochs=epochs,
        batch_size=batch_size,
        threshold_percentile=threshold_percentile,
        random_state=random_state,
        device=device,
    )
    detector.fit(X_train_normal)

    X_full = feature_engineer.transform(df)
    anomaly_scores = detector.score_samples(X_full)
    threshold_optimization: dict[str, Any] | None = None
    has_two_label_classes = len(set(y_true)) == 2
    if optimize_decision_threshold and has_two_label_classes:
        threshold_optimization = optimize_threshold(
            y_true,
            anomaly_scores,
        )
        selected_threshold = threshold_optimization["selected"]
        detector.threshold_ = float(selected_threshold["threshold"])
        detector.threshold_percentile = float(selected_threshold["percentile"])

    result = apply_business_rules(df, detector.results(X_full))
    evaluation = evaluate_detection(
        y_true,
        result["anomaly_label"].tolist(),
        result["anomaly_score"].tolist(),
    )
    evaluation["label_column"] = label_column
    if threshold_optimization is not None:
        evaluation["threshold_optimization"] = threshold_optimization["selected"]
    elif optimize_decision_threshold and not has_two_label_classes:
        evaluation["threshold_optimization_skipped"] = (
            "requires both normal and anomaly labels"
        )
    eval_path = output_directory / "evaluation_autoencoder.json"
    eval_path.write_text(json.dumps(evaluation, indent=2, default=str), encoding="utf-8")

    error_analysis = build_error_analysis(
        df=df,
        y_true=y_true,
        result=result,
        output_directory=output_directory,
        label_column=label_column,
    )

    model_path = model_directory / "autoencoder.joblib"
    preprocessor_path = model_directory / "autoencoder_preprocessor.joblib"
    detector.save(model_path)
    feature_engineer.save(preprocessor_path)

    metadata: dict[str, Any] = {
        "training_date": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(Path(data_path)),
        "number_of_rows": len(df),
        "normal_rows_used_for_training": len(df_normal),
        "label_column_used_for_training": label_column,
        "model": str(model_path),
        "preprocessor": str(preprocessor_path),
        "evaluation": str(eval_path),
        "error_analysis": error_analysis,
        "feature_engineering": feature_engineer.metadata(),
        "model_parameters": detector.parameters,
        "training_loss": detector.training_loss_,
    }
    if threshold_optimization is not None:
        metadata["threshold_optimization"] = threshold_optimization
    metadata_path = model_directory / "metadata_autoencoder.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
    return metadata


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train MauriPay autoencoder on normal transactions only"
    )
    parser.add_argument("--data", required=True, help="Input CSV/JSON/Parquet dataset")
    parser.add_argument("--model-dir", default=None, help="Directory for saved model")
    parser.add_argument("--output-dir", default=None, help="Directory for evaluation JSON")
    parser.add_argument("--encoding-dim", type=int, default=8)
    parser.add_argument("--hidden-dims", type=int, nargs=2, default=[32, 16])
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--threshold-percentile", type=float, default=98.0)
    parser.add_argument(
        "--no-threshold-optimization",
        action="store_true",
        help="Keep the percentile threshold instead of selecting the best F1 threshold",
    )
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--device", default=None, choices=["cpu", "cuda"])
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    metadata = train_autoencoder(
        data_path=args.data,
        model_dir=args.model_dir,
        output_dir=args.output_dir,
        encoding_dim=args.encoding_dim,
        hidden_dims=args.hidden_dims,
        learning_rate=args.learning_rate,
        epochs=args.epochs,
        batch_size=args.batch_size,
        threshold_percentile=args.threshold_percentile,
        optimize_decision_threshold=not args.no_threshold_optimization,
        random_state=args.random_state,
        device=args.device,
    )
    print(json.dumps(metadata, indent=2, default=str))


if __name__ == "__main__":
    main()
