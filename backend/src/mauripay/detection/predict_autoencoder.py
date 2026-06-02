from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from mauripay.detection.autoencoder import AutoencoderDetector
from mauripay.detection.business_rules import apply_business_rules
from mauripay.detection.features import TransactionFeatureEngineer
from mauripay.detection.io import load_table, project_backend_root
from mauripay.detection.metrics import evaluate_detection
from mauripay.detection.train_autoencoder import (
    build_error_analysis,
    find_label_column,
    normalize_label_values,
)


def load_autoencoder_artifacts(
    model_dir: str | Path | None = None,
) -> tuple[AutoencoderDetector, TransactionFeatureEngineer, Path]:
    backend_root = project_backend_root()
    model_directory = Path(model_dir) if model_dir else backend_root / "models"
    preprocessor = TransactionFeatureEngineer.load(
        model_directory / "autoencoder_preprocessor.joblib"
    )
    detector = AutoencoderDetector.load(model_directory / "autoencoder.joblib")
    return detector, preprocessor, model_directory


def prepare_autoencoder_data(
    data_path: str | Path,
    model_dir: str | Path | None = None,
) -> tuple[pd.DataFrame, AutoencoderDetector, np.ndarray, Path]:
    detector, preprocessor, model_directory = load_autoencoder_artifacts(model_dir)
    df = load_table(data_path)
    X = preprocessor.transform(df)
    return df, detector, X, model_directory


def predict_autoencoder(
    data_path: str | Path,
    model_dir: str | Path | None = None,
    output: str | Path | None = None,
    threshold_percentile: float | None = None,
) -> Path:
    if threshold_percentile is not None and not 0 < threshold_percentile < 100:
        raise ValueError("threshold_percentile must be between 0 and 100")

    backend_root = project_backend_root()
    model_directory = Path(model_dir) if model_dir else backend_root / "models"
    output_path = (
        Path(output)
        if output
        else backend_root / "outputs" / "anomaly_predictions_autoencoder.csv"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df, detector, X, _ = prepare_autoencoder_data(data_path, model_directory)
    if threshold_percentile is not None:
        detector.threshold_percentile = threshold_percentile
        detector.threshold_ = float(
            np.percentile(detector.score_samples(X), threshold_percentile)
        )

    detector_result = apply_business_rules(df, detector.results(X))
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
        evaluation["selected_threshold"] = {
            "percentile": detector.threshold_percentile,
            "threshold": detector.threshold_,
        }

        eval_path = output_path.parent / "evaluation_autoencoder.json"
        eval_path.write_text(
            json.dumps(evaluation, indent=2, default=str),
            encoding="utf-8",
        )
        build_error_analysis(
            df=df,
            y_true=y_true,
            result=detector_result,
            output_directory=output_path.parent,
            label_column=label_column,
        )
    return output_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Predict MauriPay anomalies with a separately trained autoencoder"
    )
    parser.add_argument("--data", required=True, help="Input CSV/JSON/Parquet dataset")
    parser.add_argument("--model-dir", default=None, help="Directory containing model files")
    parser.add_argument("--output", default=None, help="Output prediction CSV")
    parser.add_argument(
        "--threshold-percentile",
        type=float,
        default=None,
        help="Override the saved threshold with this percentile of input reconstruction errors",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    output_path = predict_autoencoder(
        data_path=args.data,
        model_dir=args.model_dir,
        output=args.output,
        threshold_percentile=args.threshold_percentile,
    )
    print(f"Autoencoder predictions saved to {output_path}")


if __name__ == "__main__":
    main()
