from __future__ import annotations

import argparse
import time
from pathlib import Path

from mauripay.features import build_features
from mauripay.ingestion import load_transactions
from mauripay.synthetic.exporters import export_parquet
from mauripay.synthetic.generator import generate_transactions


DEFAULT_OUTPUT = Path("data/generated/mauripay_l_1m.parquet")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark ingestion + feature engineering on Parquet data."
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=1_000_000,
        help="Number of synthetic transactions to generate when output is missing.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Parquet file path.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Synthetic generator seed.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate the Parquet file even if it already exists.",
    )
    parser.add_argument(
        "--dataframe-engine",
        choices=["pandas", "polars"],
        default="polars",
        help="Engine used to materialize transactions before feature engineering.",
    )
    return parser.parse_args()


def timed_step(label: str, function):
    start = time.perf_counter()
    result = function()
    elapsed = time.perf_counter() - start
    print(f"{label}: {elapsed:.2f}s")
    return result, elapsed


def ensure_parquet_dataset(output_path: Path, rows: int, seed: int, force: bool) -> None:
    if output_path.exists() and not force:
        print(f"Dataset found: {output_path}")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    transactions, _ = timed_step(
        f"Generate {rows:,} transactions",
        lambda: generate_transactions(rows=rows, seed=seed),
    )
    timed_step(
        f"Export Parquet to {output_path}",
        lambda: export_parquet(transactions, output_path),
    )


def main() -> None:
    args = parse_args()

    ensure_parquet_dataset(
        output_path=args.output,
        rows=args.rows,
        seed=args.seed,
        force=args.force,
    )

    transactions, ingest_seconds = timed_step(
        "Load Parquet transactions",
        lambda: load_transactions(args.output),
    )
    features, feature_seconds = timed_step(
        f"Build features ({args.dataframe_engine})",
        lambda: build_features(
            transactions,
            dataframe_engine=args.dataframe_engine,
        ),
    )

    print("")
    print("Benchmark summary")
    print("-----------------")
    print(f"rows_loaded: {len(transactions):,}")
    print(f"feature_rows: {len(features):,}")
    print(f"feature_columns: {len(features.columns):,}")
    print(f"ingestion_seconds: {ingest_seconds:.2f}")
    print(f"feature_seconds: {feature_seconds:.2f}")
    print(f"total_seconds: {ingest_seconds + feature_seconds:.2f}")


if __name__ == "__main__":
    main()
