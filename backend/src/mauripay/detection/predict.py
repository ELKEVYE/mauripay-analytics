from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from mauripay.detection.features import LABEL_COLUMNS, TransactionFeatureEngineer
from mauripay.detection.io import load_table, project_backend_root
from mauripay.detection.metrics import evaluate_detection
from mauripay.detection.model_registry import load_detector


def find_label_column(columns: list[str]) -> str | None:
    for column in columns:
        if column.lower() in LABEL_COLUMNS:
            return column
    return None


def normalize_label_values(values: pd.Series) -> list[int]:
    lowered = values.astype(str).str.lower()
    return lowered.isin(["true", "1", "yes", "anomaly", "fraud"]).astype(int).tolist()


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
    preprocessor_filename = (
        "autoencoder_preprocessor.joblib"
        if algorithm == "autoencoder"
        else "preprocessor.joblib"
    )
    preprocessor = TransactionFeatureEngineer.load(model_directory / preprocessor_filename)
    detector = load_detector(model_directory, algorithm)

    X = preprocessor.transform(df)
    detector_result = detector.results(X)
    if algorithm == "autoencoder":
        from mauripay.detection.business_rules import apply_business_rules

        detector_result = apply_business_rules(df, detector_result)
    result = pd.concat([df.reset_index(drop=True), detector_result], axis=1)
    result.to_csv(output_path, index=False)

    label_column = find_label_column(list(df.columns))
    if label_column is not None:
        y_true = normalize_label_values(df[label_column])
        evaluation = evaluate_detection(
            y_true,
            detector_result["anomaly_label"].astype(int).tolist(),
            detector_result["anomaly_score"].astype(float).tolist(),
        )
        evaluation["label_column"] = label_column
        evaluation["dataset_path"] = str(Path(data_path))
        evaluation["prediction_file"] = str(output_path)
        eval_path = output_path.parent / f"evaluation_{algorithm}.json"
        eval_path.write_text(
            json.dumps(evaluation, indent=2, default=str),
            encoding="utf-8",
        )

        if algorithm == "autoencoder":
            from mauripay.detection.train_autoencoder import build_error_analysis

            build_error_analysis(
                df=df,
                y_true=y_true,
                result=detector_result,
                output_directory=output_path.parent,
                label_column=label_column,
            )

    return output_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Predict MauriPay anomalies")
    parser.add_argument(
        "--model",
        required=True,
        choices=["isolation_forest", "lof", "autoencoder"],
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
