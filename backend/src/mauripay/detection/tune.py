from __future__ import annotations

import argparse
import json
from itertools import product
from pathlib import Path
from typing import Any

import pandas as pd

from mauripay.detection.features import TransactionFeatureEngineer
from mauripay.detection.iforest import IsolationForestDetector
from mauripay.detection.io import load_table, project_backend_root
from mauripay.detection.lof import LOFDetector
from mauripay.detection.train import evaluate_detector, find_label_column, split_dataframe


# Contaminations cover the true anomaly rate (~7.3% for default generator params).
# With structuring_rate=0.003×6txns and high_frequency_rate=0.002×20txns plus 2%
# simple anomalies, the real anomaly rate is roughly 7-8%.
DEFAULT_CONTAMINATIONS = [0.04, 0.06, 0.068, 0.08, 0.10, 0.12]
DEFAULT_IFOREST_ESTIMATORS = [200, 300]
DEFAULT_IFOREST_MAX_SAMPLES = ["auto", "0.8"]
DEFAULT_LOF_NEIGHBORS = [20, 35, 50, 75]
DEFAULT_LOF_METRICS = ["minkowski", "manhattan", "cosine"]


def parse_float_list(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def parse_int_list(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def parse_str_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _max_samples_value(value: str) -> str | float:
    if value == "auto":
        return value
    return float(value)


def _row(
    algorithm: str,
    evaluation: dict[str, object],
    contamination: float,
    extra_params: dict[str, Any],
    test_size: float,
) -> dict[str, Any]:
    return {
        "algorithm": algorithm,
        "precision": evaluation.get("precision"),
        "recall": evaluation.get("recall"),
        "f1_score": evaluation.get("f1_score"),
        "accuracy": evaluation.get("accuracy"),
        "roc_auc": evaluation.get("roc_auc"),
        "contamination": contamination,
        "test_size": test_size,
        **extra_params,
    }


def tune_models(
    data_path: str | Path,
    output_dir: str | Path | None = None,
    contaminations: list[float] | None = None,
    iforest_estimators: list[int] | None = None,
    iforest_max_samples: list[str] | None = None,
    lof_neighbors: list[int] | None = None,
    lof_metrics: list[str] | None = None,
    test_size: float = 0.3,
    split_seed: int = 42,
) -> dict[str, Any]:
    output_directory = Path(output_dir) if output_dir else project_backend_root() / "outputs"
    output_directory.mkdir(parents=True, exist_ok=True)

    contaminations = contaminations or DEFAULT_CONTAMINATIONS
    iforest_estimators = iforest_estimators or DEFAULT_IFOREST_ESTIMATORS
    iforest_max_samples = iforest_max_samples or DEFAULT_IFOREST_MAX_SAMPLES
    lof_neighbors = lof_neighbors or DEFAULT_LOF_NEIGHBORS
    lof_metrics = lof_metrics or DEFAULT_LOF_METRICS

    df = load_table(data_path)
    label_column = find_label_column(list(df.columns))
    if label_column is None:
        raise ValueError("Tuning requires a label column for evaluation")

    train_df, eval_df = split_dataframe(df, label_column, test_size, split_seed)
    feature_engineer = TransactionFeatureEngineer()
    X_train = feature_engineer.fit_transform(train_df)
    X_eval = feature_engineer.transform(eval_df)

    rows: list[dict[str, Any]] = []

    for contamination, n_estimators, max_samples in product(
        contaminations,
        iforest_estimators,
        iforest_max_samples,
    ):
        detector = IsolationForestDetector(
            contamination=contamination,
            n_estimators=n_estimators,
            max_samples=_max_samples_value(max_samples),
            random_state=42,
        )
        detector.fit(X_train)
        evaluation = evaluate_detector(detector, X_eval, eval_df, label_column)
        rows.append(
            _row(
                "isolation_forest",
                evaluation,
                contamination,
                {"n_estimators": n_estimators, "max_samples": max_samples},
                test_size,
            )
        )

    for contamination, n_neighbors, metric in product(
        contaminations,
        lof_neighbors,
        lof_metrics,
    ):
        if len(train_df) <= n_neighbors:
            continue
        detector = LOFDetector(
            contamination=contamination,
            n_neighbors=n_neighbors,
            metric=metric,
        )
        detector.fit(X_train)
        evaluation = evaluate_detector(detector, X_eval, eval_df, label_column)
        rows.append(
            _row(
                "lof",
                evaluation,
                contamination,
                {"n_neighbors": n_neighbors, "metric": metric},
                test_size,
            )
        )

    results = pd.DataFrame(rows).sort_values(
        ["f1_score", "roc_auc"],
        ascending=[False, False],
        na_position="last",
    )
    csv_path = output_directory / "tuning_results.csv"
    results.to_csv(csv_path, index=False)

    best_row = results.iloc[0].where(pd.notna(results.iloc[0]), None).to_dict()
    summary = {
        "data_path": str(data_path),
        "train_rows": len(train_df),
        "evaluation_rows": len(eval_df),
        "test_size": test_size,
        "split_seed": split_seed,
        "best": best_row,
        "results_csv": str(csv_path),
    }
    summary_path = output_directory / "tuning_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tune MauriPay IF/LOF detectors")
    parser.add_argument("--data", required=True)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--contaminations", default=",".join(map(str, DEFAULT_CONTAMINATIONS)))
    parser.add_argument("--iforest-estimators", default=",".join(map(str, DEFAULT_IFOREST_ESTIMATORS)))
    parser.add_argument("--iforest-max-samples", default=",".join(DEFAULT_IFOREST_MAX_SAMPLES))
    parser.add_argument("--lof-neighbors", default=",".join(map(str, DEFAULT_LOF_NEIGHBORS)))
    parser.add_argument("--lof-metrics", default=",".join(DEFAULT_LOF_METRICS))
    parser.add_argument("--test-size", type=float, default=0.3)
    parser.add_argument("--split-seed", type=int, default=42)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    summary = tune_models(
        data_path=args.data,
        output_dir=args.output_dir,
        contaminations=parse_float_list(args.contaminations),
        iforest_estimators=parse_int_list(args.iforest_estimators),
        iforest_max_samples=parse_str_list(args.iforest_max_samples),
        lof_neighbors=parse_int_list(args.lof_neighbors),
        lof_metrics=parse_str_list(args.lof_metrics),
        test_size=args.test_size,
        split_seed=args.split_seed,
    )
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
