from __future__ import annotations

import argparse

from mauripay.detection.evaluate_autoencoder_thresholds import (
    evaluate_autoencoder_thresholds,
)
from mauripay.detection.predict import PREDICTION_MODELS, predict_anomalies
from mauripay.detection.train import train_models
from mauripay.detection.tune import tune_models
from mauripay.detection.train_autoencoder import train_autoencoder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MauriPay analytics CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    train_parser = subparsers.add_parser(
        "train",
        help="Train IF/LOF and optionally the autoencoder",
    )
    train_parser.add_argument("--data", required=True)
    train_parser.add_argument("--model-dir", default=None)
    train_parser.add_argument("--output-dir", default=None)
    train_parser.add_argument("--contamination", type=float, default=0.02)
    train_parser.add_argument("--n-estimators", type=int, default=100)
    train_parser.add_argument("--n-neighbors", type=int, default=20)
    train_parser.add_argument("--test-size", type=float, default=0.0)
    train_parser.add_argument(
        "--lof-max-train-rows",
        type=int,
        default=20000,
        help="Maximum rows used to fit LOF; use 0 to train LOF on all rows.",
    )
    train_parser.add_argument(
        "--include-autoencoder",
        action="store_true",
        help="Also train the PyTorch autoencoder detector",
    )
    train_parser.add_argument("--autoencoder-epochs", type=int, default=50)
    train_parser.add_argument("--autoencoder-batch-size", type=int, default=128)
    train_parser.add_argument("--autoencoder-threshold-percentile", type=float, default=98.0)
    train_parser.add_argument(
        "--no-autoencoder-threshold-optimization",
        action="store_true",
    )
    train_parser.add_argument("--autoencoder-device", default=None, choices=["cpu", "cuda"])

    autoencoder_parser = subparsers.add_parser(
        "train-autoencoder",
        help="Train the PyTorch autoencoder detector",
    )
    autoencoder_parser.add_argument("--data", required=True)
    autoencoder_parser.add_argument("--model-dir", default=None)
    autoencoder_parser.add_argument("--output-dir", default=None)
    autoencoder_parser.add_argument("--encoding-dim", type=int, default=8)
    autoencoder_parser.add_argument("--hidden-dims", type=int, nargs=2, default=[32, 16])
    autoencoder_parser.add_argument("--learning-rate", type=float, default=1e-3)
    autoencoder_parser.add_argument("--epochs", type=int, default=50)
    autoencoder_parser.add_argument("--batch-size", type=int, default=128)
    autoencoder_parser.add_argument("--threshold-percentile", type=float, default=98.0)
    autoencoder_parser.add_argument(
        "--no-threshold-optimization",
        action="store_true",
    )
    autoencoder_parser.add_argument("--random-state", type=int, default=42)
    autoencoder_parser.add_argument("--device", default=None, choices=["cpu", "cuda"])

    threshold_parser = subparsers.add_parser(
        "evaluate-autoencoder-thresholds",
        help="Choose the saved Autoencoder threshold on validation data",
    )
    threshold_parser.add_argument("--validation-data", required=True)
    threshold_parser.add_argument("--test-data", nargs="*", default=None)
    threshold_parser.add_argument("--model-dir", default=None)
    threshold_parser.add_argument("--output-dir", default=None)

    tune_parser = subparsers.add_parser("tune", help="Tune IF and LOF detector settings")
    tune_parser.add_argument("--data", required=True)
    tune_parser.add_argument("--test-size", type=float, default=0.3)

    predict_parser = subparsers.add_parser("predict", help="Predict anomalies")
    predict_parser.add_argument(
        "--model",
        required=True,
        choices=PREDICTION_MODELS,
    )
    predict_parser.add_argument("--data", required=True)
    predict_parser.add_argument("--model-dir", default=None)
    predict_parser.add_argument("--output", default=None)

    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "train":
        train_models(
            data_path=args.data,
            model_dir=args.model_dir,
            output_dir=args.output_dir,
            contamination=args.contamination,
            n_estimators=args.n_estimators,
            n_neighbors=args.n_neighbors,
            test_size=args.test_size,
            include_autoencoder=args.include_autoencoder,
            lof_max_train_rows=args.lof_max_train_rows or None,
            autoencoder_epochs=args.autoencoder_epochs,
            autoencoder_batch_size=args.autoencoder_batch_size,
            autoencoder_threshold_percentile=args.autoencoder_threshold_percentile,
            autoencoder_optimize_threshold=not args.no_autoencoder_threshold_optimization,
            autoencoder_device=args.autoencoder_device,
        )
        return

    if args.command == "train-autoencoder":
        train_autoencoder(
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
        return

    if args.command == "evaluate-autoencoder-thresholds":
        evaluate_autoencoder_thresholds(
            validation_data=args.validation_data,
            test_data=args.test_data,
            model_dir=args.model_dir,
            output_dir=args.output_dir,
        )
        return

    if args.command == "tune":
        tune_models(
            data_path=args.data,
            test_size=args.test_size,
        )
        return

    if args.command == "predict":
        predict_anomalies(
            algorithm=args.model,
            data_path=args.data,
            model_dir=args.model_dir,
            output=args.output,
        )


if __name__ == "__main__":
    main()
