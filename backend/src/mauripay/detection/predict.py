from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from mauripay.detection.features import LABEL_COLUMNS, TransactionFeatureEngineer
from mauripay.detection.business_rules import apply_business_rules
from mauripay.detection.io import load_table, project_backend_root
from mauripay.detection.metrics import evaluate_by_anomaly_type, evaluate_detection
from mauripay.detection.model_registry import MODEL_FILENAMES, load_detector


PREDICTION_MODELS = sorted([*MODEL_FILENAMES, "ensemble"])
ENSEMBLE_ALGORITHMS = ("isolation_forest", "lof", "autoencoder")


def find_label_column(columns: list[str]) -> str | None:
    for column in columns:
        if column.lower() in LABEL_COLUMNS:
            return column
    return None


def normalize_label_values(values: pd.Series) -> list[int]:
    lowered = values.astype(str).str.lower()
    return lowered.isin(["true", "1", "yes", "anomaly", "fraud"]).astype(int).tolist()


def write_prediction_evaluation(
    df: pd.DataFrame,
    detector_result: pd.DataFrame,
    data_path: str | Path,
    output_path: Path,
    algorithm: str,
) -> None:
    label_column = find_label_column(list(df.columns))
    if label_column is None:
        return

    y_true = normalize_label_values(df[label_column])
    evaluation = evaluate_detection(
        y_true,
        detector_result["anomaly_label"].astype(int).tolist(),
        detector_result["anomaly_score"].astype(float).tolist(),
    )
    evaluation["label_column"] = label_column
    evaluation["dataset_path"] = str(Path(data_path))
    evaluation["prediction_file"] = str(output_path)

    if "anomaly_type" in df.columns:
        evaluation["by_anomaly_type"] = evaluate_by_anomaly_type(
            df["anomaly_type"],
            detector_result["anomaly_label"].astype(int).tolist(),
            detector_result["anomaly_score"].astype(float).tolist(),
        )

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


def combine_ensemble_predictions(
    data_path: str | Path,
    prediction_paths: dict[str, str | Path],
    output: str | Path,
) -> Path:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    missing_predictions = [
        algorithm
        for algorithm in ENSEMBLE_ALGORITHMS
        if algorithm not in prediction_paths
    ]
    if missing_predictions:
        raise ValueError(
            "Missing predictions required by the IF+LOF+Autoencoder ensemble: "
            + ", ".join(missing_predictions)
        )

    base = load_table(data_path).reset_index(drop=True)
    prediction_results = {
        algorithm: pd.read_csv(prediction_paths[algorithm])
        for algorithm in ENSEMBLE_ALGORITHMS
    }
    return combine_ensemble_results(
        df=base,
        prediction_results=prediction_results,
        data_path=data_path,
        output=output,
    )


def combine_ensemble_results_with_frame(
    df: pd.DataFrame,
    prediction_results: dict[str, pd.DataFrame],
    data_path: str | Path,
    output: str | Path,
) -> tuple[Path, pd.DataFrame]:
    """Build the ensemble without reloading the dataset or prediction CSV files."""
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    missing_predictions = [
        algorithm
        for algorithm in ENSEMBLE_ALGORITHMS
        if algorithm not in prediction_results
    ]
    if missing_predictions:
        raise ValueError(
            "Missing predictions required by the IF+LOF+Autoencoder ensemble: "
            + ", ".join(missing_predictions)
        )

    predictions = [
        prediction_results[algorithm][["anomaly_label", "anomaly_score"]].rename(
            columns={
                "anomaly_label": f"{algorithm}_label",
                "anomaly_score": f"{algorithm}_score",
            }
        )
        for algorithm in ENSEMBLE_ALGORITHMS
    ]
    base = df.reset_index(drop=True)
    votes = pd.concat([item.filter(like="_label") for item in predictions], axis=1)
    scores = pd.concat([item.filter(like="_score") for item in predictions], axis=1)
    ensemble_result = pd.concat([base, *predictions], axis=1)
    ensemble_result["ensemble_vote_count"] = votes.sum(axis=1).astype(int)
    ensemble_result["anomaly_score"] = scores.mean(axis=1)
    if_label = ensemble_result["isolation_forest_label"].astype(int).eq(1)
    lof_label = ensemble_result["lof_label"].astype(int).eq(1)
    autoencoder_label = ensemble_result["autoencoder_label"].astype(int).eq(1)
    classical_consensus = if_label & lof_label
    autoencoder_only = autoencoder_label & ~if_label & ~lof_label
    ensemble_result["classical_consensus_label"] = classical_consensus.astype(int)
    ensemble_result["autoencoder_only_label"] = autoencoder_only.astype(int)
    ensemble_result["anomaly_label"] = (
        classical_consensus | autoencoder_only
    ).astype(int)
    ensemble_result["algorithm"] = "ensemble"
    ensemble_result.to_csv(output_path, index=False)

    write_prediction_evaluation(
        df=base,
        detector_result=ensemble_result,
        data_path=data_path,
        output_path=output_path,
        algorithm="ensemble",
    )

    return output_path, ensemble_result


def combine_ensemble_results(
    df: pd.DataFrame,
    prediction_results: dict[str, pd.DataFrame],
    data_path: str | Path,
    output: str | Path,
) -> Path:
    output_path, _ = combine_ensemble_results_with_frame(
        df=df,
        prediction_results=prediction_results,
        data_path=data_path,
        output=output,
    )
    return output_path


def predict_anomalies_from_frame(
    algorithm: str,
    df: pd.DataFrame,
    data_path: str | Path,
    model_dir: str | Path,
    output: str | Path,
    X: object | None = None,
) -> tuple[Path, pd.DataFrame]:
    """Predict from an already loaded frame and optionally precomputed features."""
    model_directory = Path(model_dir)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if X is None:
        preprocessor_filename = (
            "autoencoder_preprocessor.joblib"
            if algorithm == "autoencoder"
            else "preprocessor.joblib"
        )
        preprocessor = TransactionFeatureEngineer.load(
            model_directory / preprocessor_filename
        )
        X = preprocessor.transform(df)

    detector = load_detector(model_directory, algorithm)
    detector_result = detector.results(X)
    detector_result = apply_business_rules(df, detector_result)
    result = pd.concat([df.reset_index(drop=True), detector_result], axis=1)
    result.to_csv(output_path, index=False)

    write_prediction_evaluation(
        df=df,
        detector_result=detector_result,
        data_path=data_path,
        output_path=output_path,
        algorithm=algorithm,
    )
    return output_path, detector_result


def predict_ensemble(
    data_path: str | Path,
    model_dir: str | Path | None = None,
    output: str | Path | None = None,
) -> Path:
    backend_root = project_backend_root()
    model_directory = Path(model_dir) if model_dir else backend_root / "models"
    output_path = (
        Path(output)
        if output
        else backend_root / "outputs" / "anomaly_predictions_ensemble.csv"
    )
    missing_algorithms = [
        algorithm
        for algorithm in ENSEMBLE_ALGORITHMS
        if not (model_directory / MODEL_FILENAMES[algorithm]).exists()
    ]
    if missing_algorithms:
        raise FileNotFoundError(
            "Missing trained model(s) required by the IF+LOF+Autoencoder ensemble: "
            + ", ".join(missing_algorithms)
        )

    with TemporaryDirectory() as temp_dir:
        prediction_paths = {
            algorithm: predict_anomalies(
                algorithm=algorithm,
                data_path=data_path,
                model_dir=model_directory,
                output=Path(temp_dir) / f"{algorithm}.csv",
            )
            for algorithm in ENSEMBLE_ALGORITHMS
        }
        return combine_ensemble_predictions(
            data_path=data_path,
            prediction_paths=prediction_paths,
            output=output_path,
        )


def predict_anomalies(
    algorithm: str,
    data_path: str | Path,
    model_dir: str | Path | None = None,
    output: str | Path | None = None,
) -> Path:
    if algorithm == "ensemble":
        return predict_ensemble(
            data_path=data_path,
            model_dir=model_dir,
            output=output,
        )

    backend_root = project_backend_root()
    model_directory = Path(model_dir) if model_dir else backend_root / "models"
    output_path = (
        Path(output)
        if output
        else backend_root / "outputs" / f"anomaly_predictions_{algorithm}.csv"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    predictions_path, _ = predict_anomalies_from_frame(
        algorithm=algorithm,
        df=load_table(data_path),
        data_path=data_path,
        model_dir=model_directory,
        output=output_path,
    )
    return predictions_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Predict MauriPay anomalies")
    parser.add_argument(
        "--model",
        required=True,
        choices=PREDICTION_MODELS,
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
