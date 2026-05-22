from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from mauripay.detection.features import TransactionFeatureEngineer
from mauripay.detection.io import load_table, project_backend_root
from mauripay.detection.model_registry import load_detector


def predict_anomalies(
    algorithm: str,
    data_path: str | Path,
    model_dir: str | Path | None = None,
    output: str | Path | None = None,
) -> Path:
    backend_root = project_backend_root()
    model_directory = Path(model_dir) if model_dir else backend_root / "models"
    output_path = (
        Path(output)
        if output
        else backend_root / "outputs" / f"anomaly_predictions_{algorithm}.csv"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = load_table(data_path)
    preprocessor = TransactionFeatureEngineer.load(model_directory / "preprocessor.joblib")
    detector = load_detector(model_directory, algorithm)

    X = preprocessor.transform(df)
    result = pd.concat([df.reset_index(drop=True), detector.results(X)], axis=1)
    result.to_csv(output_path, index=False)
    return output_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Predict MauriPay anomalies")
    parser.add_argument(
        "--model",
        required=True,
        choices=["isolation_forest", "lof"],
        help="Trained detector to use",
    )
    parser.add_argument("--data", required=True, help="Input CSV/JSON/Parquet dataset")
    parser.add_argument("--model-dir", default=None, help="Directory containing models")
    parser.add_argument("--output", default=None, help="Output prediction CSV")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    output_path = predict_anomalies(
        algorithm=args.model,
        data_path=args.data,
        model_dir=args.model_dir,
        output=args.output,
    )
    print(f"Predictions saved to {output_path}")


if __name__ == "__main__":
    main()
