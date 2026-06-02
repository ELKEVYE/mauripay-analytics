from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from mauripay.detection.io import project_backend_root
from mauripay.detection.business_rules import apply_business_rules
from mauripay.detection.metrics import evaluate_detection
from mauripay.detection.predict_autoencoder import prepare_autoencoder_data
from mauripay.detection.train_autoencoder import (
    build_error_analysis,
    find_label_column,
    normalize_label_values,
)


DEFAULT_PERCENTILES = [90.0, 92.0, 94.0, 95.0, 96.0, 97.0, 98.0, 99.0, 99.5]
MIN_SELECTION_PRECISION = 0.84


def _load_labels(df: pd.DataFrame, dataset_name: str) -> tuple[str, list[int]]:
    label_column = find_label_column(list(df.columns))
    if label_column is None:
        raise ValueError(f"{dataset_name} requires a label column such as is_anomaly")
    y_true = normalize_label_values(df[label_column])
    if len(set(y_true)) < 2:
        raise ValueError(f"{dataset_name} must contain normal and anomaly rows")
    return label_column, y_true


def _evaluate_scores(
    y_true: list[int],
    scores: np.ndarray,
    threshold: float,
) -> dict[str, Any]:
    y_pred = (scores > threshold).astype(int).tolist()
    return evaluate_detection(y_true, y_pred, scores.tolist())


def _threshold_candidates(
    y_true: list[int],
    scores: np.ndarray,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for percentile in DEFAULT_PERCENTILES:
        threshold = float(np.percentile(scores, percentile))
        metrics = _evaluate_scores(y_true, scores, threshold)
        candidates.append(
            {
                "percentile": percentile,
                "threshold": threshold,
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1_score": metrics["f1_score"],
                "confusion_matrix": metrics["confusion_matrix"],
                "roc_auc": metrics.get("roc_auc"),
                "predicted_anomalies": int((scores > threshold).sum()),
            }
        )
    return candidates


def _best_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    safe_candidates = [
        candidate
        for candidate in candidates
        if float(candidate["precision"]) >= MIN_SELECTION_PRECISION
    ]
    return max(
        safe_candidates or candidates,
        key=lambda item: (
            float(item["f1_score"]),
            float(item["recall"]),
            float(item["precision"]),
        ),
    )


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def evaluate_autoencoder_thresholds(
    validation_data: str | Path,
    test_data: list[str | Path] | None = None,
    model_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    backend_root = project_backend_root()
    model_directory = Path(model_dir) if model_dir else backend_root / "models"
    output_directory = Path(output_dir) if output_dir else backend_root / "outputs"
    output_directory.mkdir(parents=True, exist_ok=True)

    preprocessor_path = model_directory / "autoencoder_preprocessor.joblib"
    model_path = model_directory / "autoencoder.joblib"

    validation_df, detector, validation_X, _ = prepare_autoencoder_data(
        validation_data,
        model_directory,
    )
    validation_label, validation_y = _load_labels(validation_df, "validation_data")
    validation_scores = detector.score_samples(validation_X)

    candidates = _threshold_candidates(validation_y, validation_scores)
    selected = _best_candidate(candidates)
    detector.threshold_percentile = float(selected["percentile"])
    detector.threshold_ = float(selected["threshold"])
    detector.save(model_path)

    validation_result = apply_business_rules(
        validation_df,
        detector.results(validation_X),
    )
    validation_evaluation = evaluate_detection(
        validation_y,
        validation_result["anomaly_label"].tolist(),
        validation_result["anomaly_score"].tolist(),
    )
    validation_evaluation["label_column"] = validation_label
    validation_evaluation["dataset_path"] = str(Path(validation_data))
    validation_evaluation["selected_threshold"] = selected

    error_analysis = build_error_analysis(
        df=validation_df,
        y_true=validation_y,
        result=validation_result,
        output_directory=output_directory,
        label_column=validation_label,
    )

    test_results: list[dict[str, Any]] = []
    for data_path in test_data or []:
        test_df, _, test_X, _ = prepare_autoencoder_data(data_path, model_directory)
        test_label, test_y = _load_labels(test_df, f"test_data {data_path}")
        test_result = apply_business_rules(
            test_df,
            detector.results(test_X),
        )
        test_evaluation = evaluate_detection(
            test_y,
            test_result["anomaly_label"].tolist(),
            test_result["anomaly_score"].tolist(),
        )
        test_evaluation["label_column"] = test_label
        test_evaluation["dataset_path"] = str(Path(data_path))
        test_results.append(test_evaluation)

    comparison_json = output_directory / "autoencoder_threshold_comparison.json"
    comparison_csv = output_directory / "autoencoder_threshold_comparison.csv"
    _write_json(comparison_json, candidates)
    pd.DataFrame(candidates).to_csv(comparison_csv, index=False)

    report = {
        "evaluation_date": datetime.now(timezone.utc).isoformat(),
        "validation_data": str(Path(validation_data)),
        "test_data": [str(Path(path)) for path in (test_data or [])],
        "model": str(model_path),
        "preprocessor": str(preprocessor_path),
        "threshold_selection_objective": (
            f"maximize_f1_then_recall_then_precision_with_precision_at_least_"
            f"{MIN_SELECTION_PRECISION}"
        ),
        "selected_threshold": selected,
        "threshold_candidates": candidates,
        "validation_evaluation": validation_evaluation,
        "test_results": test_results,
        "error_analysis": error_analysis,
        "threshold_comparison": str(comparison_json),
        "threshold_comparison_csv": str(comparison_csv),
    }
    report_path = output_directory / "autoencoder_threshold_evaluation.json"
    _write_json(report_path, report)

    metadata_path = model_directory / "metadata_autoencoder.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    else:
        metadata = {}
    metadata["threshold_evaluation"] = {
        "evaluation_date": report["evaluation_date"],
        "validation_data": report["validation_data"],
        "test_data": report["test_data"],
        "selected_threshold": selected,
        "report": str(report_path),
    }
    metadata["model_parameters"] = detector.parameters
    _write_json(metadata_path, metadata)

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Automatically choose the saved Autoencoder threshold on validation data"
    )
    parser.add_argument("--validation-data", required=True)
    parser.add_argument("--test-data", nargs="*", default=None)
    parser.add_argument("--model-dir", default=None)
    parser.add_argument("--output-dir", default=None)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    report = evaluate_autoencoder_thresholds(
        validation_data=args.validation_data,
        test_data=args.test_data,
        model_dir=args.model_dir,
        output_dir=args.output_dir,
    )
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
