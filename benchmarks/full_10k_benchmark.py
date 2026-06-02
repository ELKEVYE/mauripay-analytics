from __future__ import annotations

import argparse
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mauripay.detection.autoencoder import AutoencoderDetector  # noqa: E402
from mauripay.detection.features import TransactionFeatureEngineer  # noqa: E402
from mauripay.detection.iforest import IsolationForestDetector  # noqa: E402
from mauripay.detection.lof import LOFDetector  # noqa: E402
from mauripay.detection.metrics import evaluate_detection  # noqa: E402
from mauripay.detection.train import find_label_column, normalize_label_values  # noqa: E402
from mauripay.synthetic.exporters import export_csv  # noqa: E402
from mauripay.synthetic.generator import generate_transactions  # noqa: E402


DEFAULT_DATA = Path("data/generated/mauripay_s_10k.csv")
DEFAULT_OUTPUT = Path("benchmarks/results/full_10k_benchmark.json")
SCENARIOS = {
    "full_10k": {
        "data": DEFAULT_DATA,
        "output": DEFAULT_OUTPUT,
        "rows": 10_000,
        "display_name": "MauriPay-S 10K",
    },
    "full_100k": {
        "data": Path("data/generated/mauripay_m_100k.csv"),
        "output": Path("benchmarks/results/full_100k_benchmark.json"),
        "rows": 100_000,
        "display_name": "MauriPay-M 100K",
    },
    "full_1m": {
        "data": Path("data/generated/mauripay_l_1m.parquet"),
        "output": Path("benchmarks/results/full_1m_benchmark.json"),
        "rows": 1_000_000,
        "display_name": "MauriPay-L 1M",
    },
}


def timed_step(label: str, function):
    start = time.perf_counter()
    result = function()
    elapsed = time.perf_counter() - start
    print(f"{label}: {elapsed:.2f}s")
    return result, elapsed


def ensure_dataset(path: Path, rows: int, seed: int, force: bool) -> None:
    if path.exists() and not force:
        print(f"Dataset found: {path}")
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    transactions, _ = timed_step(
        f"Generate {rows:,} transactions",
        lambda: generate_transactions(rows=rows, seed=seed),
    )
    if path.suffix.lower() == ".parquet":
        from mauripay.synthetic.exporters import export_parquet

        timed_step(f"Export Parquet to {path}", lambda: export_parquet(transactions, path))
    else:
        timed_step(f"Export CSV to {path}", lambda: export_csv(transactions, path))


def load_dataframe(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".json":
        return pd.read_json(path)
    raise ValueError(
        "Unsupported benchmark data format. Use .csv, .json, or .parquet"
    )


def model_metrics(
    model_name: str,
    detector,
    X_train,
    X_eval,
    y_true: list[int],
) -> dict[str, Any]:
    _, train_seconds = timed_step(
        f"Train {model_name}",
        lambda: detector.fit(X_train),
    )
    result, inference_seconds = timed_step(
        f"Infer {model_name}",
        lambda: detector.results(X_eval),
    )
    metrics = evaluate_detection(
        y_true,
        result["anomaly_label"].tolist(),
        result["anomaly_score"].tolist(),
    )
    metrics.update(
        {
            "model": model_name,
            "train_time_seconds": train_seconds,
            "inference_time_seconds": inference_seconds,
            "n_detected_anomalies": int(result["anomaly_label"].sum()),
            "parameters": detector.parameters,
        }
    )
    return metrics


def benchmark_full_dataset(args: argparse.Namespace) -> dict[str, Any]:
    scenario = SCENARIOS[args.benchmark]
    selected_models = set(args.models)
    ensure_dataset(args.data, rows=args.rows, seed=args.seed, force=args.force)

    df, load_seconds = timed_step("Load dataset", lambda: load_dataframe(args.data))
    label_column = find_label_column(list(df.columns))
    if label_column is None:
        raise ValueError("Benchmark requires a label column such as is_anomaly")

    y_true = normalize_label_values(df[label_column])
    normal_mask = pd.Series(y_true).eq(0).to_numpy()
    df_normal = df.loc[normal_mask].copy()
    if df_normal.empty:
        raise ValueError("No normal transactions found for autoencoder training")

    X_full = None
    feature_fit_seconds = None
    shared_feature_count = None
    if selected_models & {"isolation_forest", "lof"}:
        shared_features = TransactionFeatureEngineer()
        X_full, feature_fit_seconds = timed_step(
            "Fit shared features on full dataset",
            lambda: shared_features.fit_transform(df),
        )
        shared_feature_count = int(X_full.shape[1])

    X_auto_train = None
    X_auto_full = None
    ae_feature_fit_seconds = None
    ae_feature_transform_seconds = None
    autoencoder_feature_count = None
    if "autoencoder" in selected_models:
        autoencoder_features = TransactionFeatureEngineer()
        X_auto_train, ae_feature_fit_seconds = timed_step(
            "Fit autoencoder features on normal rows",
            lambda: autoencoder_features.fit_transform(df_normal),
        )
        X_auto_full, ae_feature_transform_seconds = timed_step(
            "Transform full dataset for autoencoder",
            lambda: autoencoder_features.transform(df),
        )
        autoencoder_feature_count = int(X_auto_full.shape[1])

    results = []
    if "isolation_forest" in selected_models:
        results.append(
            model_metrics(
                "isolation_forest",
                IsolationForestDetector(
                    n_estimators=args.n_estimators,
                    contamination=args.contamination,
                    random_state=args.seed,
                    max_samples=args.max_samples,
                ),
                X_full,
                X_full,
                y_true,
            )
        )
    if "lof" in selected_models:
        results.append(
            model_metrics(
                "lof",
                LOFDetector(
                    n_neighbors=args.n_neighbors,
                    contamination=args.contamination,
                    metric=args.metric,
                ),
                X_full,
                X_full,
                y_true,
            )
        )
    if "autoencoder" in selected_models:
        results.append(
            model_metrics(
                "autoencoder",
                AutoencoderDetector(
                    encoding_dim=args.encoding_dim,
                    hidden_dims=args.hidden_dims,
                    learning_rate=args.learning_rate,
                    epochs=args.epochs,
                    batch_size=args.batch_size,
                    threshold_percentile=args.threshold_percentile,
                    random_state=args.seed,
                    device=args.device,
                ),
                X_auto_train,
                X_auto_full,
                y_true,
            )
        )

    return {
        "benchmark": args.benchmark,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "machine": platform.platform(),
        "python_version": platform.python_version(),
        "dataset": str(args.data),
        "dataset_name": scenario["display_name"],
        "rows": int(len(df)),
        "label_column": label_column,
        "normal_rows": int((pd.Series(y_true) == 0).sum()),
        "anomaly_rows": int((pd.Series(y_true) == 1).sum()),
        "load_time_seconds": load_seconds,
        "feature_engineering": {
            "shared_feature_count": shared_feature_count,
            "shared_fit_transform_seconds": feature_fit_seconds,
            "autoencoder_feature_count": autoencoder_feature_count,
            "autoencoder_fit_transform_seconds": ae_feature_fit_seconds,
            "autoencoder_transform_seconds": ae_feature_transform_seconds,
        },
        "results": results,
    }


def benchmark_full_10k(args: argparse.Namespace) -> dict[str, Any]:
    return benchmark_full_dataset(args)
