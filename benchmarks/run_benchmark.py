from __future__ import annotations

import argparse
import sys
from pathlib import Path


BENCHMARKS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BENCHMARKS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from benchmarks.full_10k_benchmark import SCENARIOS, benchmark_full_dataset  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run MauriPay detection benchmarks.")
    parser.add_argument(
        "--benchmark",
        choices=sorted(SCENARIOS),
        default="full_10k",
        help="Benchmark scenario to run.",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=None,
        help="Input dataset path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="JSON output path.",
    )
    parser.add_argument("--rows", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--contamination", type=float, default=0.02)
    parser.add_argument("--n-estimators", type=int, default=100)
    parser.add_argument("--max-samples", default="auto")
    parser.add_argument("--n-neighbors", type=int, default=20)
    parser.add_argument("--metric", default="minkowski")
    parser.add_argument(
        "--models",
        nargs="+",
        choices=["isolation_forest", "lof", "autoencoder"],
        default=["isolation_forest", "lof", "autoencoder"],
        help="Models to run in this benchmark.",
    )
    parser.add_argument("--encoding-dim", type=int, default=8)
    parser.add_argument("--hidden-dims", type=int, nargs=2, default=[32, 16])
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--threshold-percentile", type=float, default=98.0)
    parser.add_argument("--device", choices=["cpu", "cuda"], default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scenario = SCENARIOS[args.benchmark]
    if args.data is None:
        args.data = scenario["data"]
    if args.output is None:
        args.output = scenario["output"]
    if args.rows is None:
        args.rows = scenario["rows"]

    metrics = benchmark_full_dataset(args)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        __import__("json").dumps(metrics, indent=2, default=str),
        encoding="utf-8",
    )

    print("")
    print("Benchmark summary")
    print("-----------------")
    print(f"rows: {metrics['rows']}")
    for result in metrics["results"]:
        print(
            "{model}: precision={precision:.4f}, recall={recall:.4f}, "
            "f1={f1_score:.4f}, roc_auc={roc_auc:.4f}, train={train:.4f}s, "
            "infer={infer:.4f}s, detected={detected}".format(
                model=result["model"],
                precision=result["precision"],
                recall=result["recall"],
                f1_score=result["f1_score"],
                roc_auc=result.get("roc_auc", float("nan")),
                train=result["train_time_seconds"],
                infer=result["inference_time_seconds"],
                detected=result["n_detected_anomalies"],
            )
        )
    print(f"results_json: {args.output}")


if __name__ == "__main__":
    main()
