from __future__ import annotations

import argparse

from mauripay.detection.predict import predict_anomalies
from mauripay.detection.train import train_models
from mauripay.detection.tune import tune_models


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MauriPay analytics CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    train_parser = subparsers.add_parser("train", help="Train IF and LOF detectors")
    train_parser.add_argument("--data", required=True)
    train_parser.add_argument("--contamination", type=float, default=0.02)
    train_parser.add_argument("--n-estimators", type=int, default=100)
    train_parser.add_argument("--n-neighbors", type=int, default=20)
    train_parser.add_argument("--test-size", type=float, default=0.0)

    tune_parser = subparsers.add_parser("tune", help="Tune IF and LOF detector settings")
    tune_parser.add_argument("--data", required=True)
    tune_parser.add_argument("--test-size", type=float, default=0.3)

    predict_parser = subparsers.add_parser("predict", help="Predict anomalies")
    predict_parser.add_argument("--model", required=True, choices=["isolation_forest", "lof"])
    predict_parser.add_argument("--data", required=True)
    predict_parser.add_argument("--output", default=None)

    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "train":
        train_models(
            data_path=args.data,
            contamination=args.contamination,
            n_estimators=args.n_estimators,
            n_neighbors=args.n_neighbors,
            test_size=args.test_size,
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
            output=args.output,
        )


if __name__ == "__main__":
    main()
