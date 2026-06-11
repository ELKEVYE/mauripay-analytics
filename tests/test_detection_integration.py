from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mauripay.detection.features import TransactionFeatureEngineer  # noqa: E402
from mauripay.detection.iforest import IsolationForestDetector  # noqa: E402
from mauripay.detection.lof import LOFDetector  # noqa: E402
from mauripay.detection.metrics import evaluate_by_anomaly_type, evaluate_detection  # noqa: E402
from mauripay.detection.predict import predict_anomalies  # noqa: E402
from mauripay.detection.train import train_models  # noqa: E402
from mauripay.detection.tune import tune_models  # noqa: E402
from mauripay.synthetic.generator import generate_transactions  # noqa: E402


TORCH_AVAILABLE = importlib.util.find_spec("torch") is not None


def sample_dataframe(rows: int = 120) -> pd.DataFrame:
    transactions = generate_transactions(
        rows=rows,
        num_accounts=60,
        seed=123,
        anomaly_rate=0.04,
        tontine_rate=0.0,
        structuring_rate=0.01,
        high_frequency_rate=0.01,
    )
    return pd.DataFrame([tx.model_dump(mode="json") for tx in transactions])


class DetectionIntegrationTests(unittest.TestCase):
    def test_feature_engineering_ignores_ids_and_labels(self):
        dataframe = sample_dataframe()
        engineer = TransactionFeatureEngineer()
        matrix = engineer.fit_transform(dataframe)

        self.assertEqual(matrix.shape[0], len(dataframe))
        self.assertIn("transaction_id", engineer.selection.ignored_columns)
        self.assertIn("sender_id", engineer.selection.ignored_columns)
        self.assertIn("receiver_id", engineer.selection.ignored_columns)
        self.assertIn("is_anomaly", engineer.selection.ignored_columns)
        self.assertIn("anomaly_type", engineer.selection.ignored_columns)
        self.assertIn("amount", engineer.selection.numerical_columns)
        self.assertIn("tx_count_5min", engineer.selection.numerical_columns)
        self.assertIn("sender_unique_receivers_1h", engineer.selection.numerical_columns)
        self.assertIn("amount_log", engineer.selection.numerical_columns)
        self.assertIn("amount_vs_sender_past_avg_7d", engineer.selection.numerical_columns)
        self.assertIn("domain_risk_score", engineer.selection.numerical_columns)
        self.assertIn("fees_to_amount_ratio", engineer.selection.numerical_columns)
        self.assertIn("receiver_unique_senders_24h", engineer.selection.numerical_columns)
        self.assertIn("operator_failure_rate_1h", engineer.selection.numerical_columns)
        self.assertIn("hour_sin", engineer.selection.numerical_columns)
        self.assertIn("transaction_type", engineer.selection.categorical_columns)
        self.assertIn("hour", engineer.selection.derived_datetime_columns)
        self.assertIn("temporal", engineer.selection.project_feature_layers)
        self.assertIn("risk", engineer.selection.project_feature_layers)
        self.assertIn("risk_signals", engineer.selection.project_feature_layers)
        self.assertIn("amount_to_sender_mean_7d", engineer.selection.numerical_columns)
        self.assertIn("failed_zero_fee_signal", engineer.selection.numerical_columns)
        self.assertIn("sender_receiver_is_new_wilaya", engineer.selection.numerical_columns)
        self.assertIn("structuring_signal", engineer.selection.numerical_columns)

    def test_iforest_trains_predicts_and_loads(self):
        dataframe = sample_dataframe()
        engineer = TransactionFeatureEngineer()
        matrix = engineer.fit_transform(dataframe)

        detector = IsolationForestDetector(contamination=0.05, n_estimators=20)
        detector.fit(matrix)
        result = detector.results(matrix)

        self.assertEqual(
            set(["anomaly_label", "anomaly_score", "algorithm"]),
            set(result.columns),
        )
        self.assertTrue(set(result["anomaly_label"].unique()) <= {0, 1})

        with TemporaryDirectory() as temp_dir:
            path = detector.save(Path(temp_dir) / "iforest.joblib")
            loaded = IsolationForestDetector.load(path)
            self.assertEqual(len(loaded.predict(matrix)), len(dataframe))

    def test_lof_uses_novelty_and_predicts(self):
        dataframe = sample_dataframe()
        engineer = TransactionFeatureEngineer()
        matrix = engineer.fit_transform(dataframe)

        detector = LOFDetector(contamination=0.05, n_neighbors=10)
        detector.fit(matrix)
        result = detector.results(matrix)

        self.assertTrue(detector.model.novelty)
        self.assertEqual(len(result), len(dataframe))
        self.assertEqual(set(result["algorithm"]), {"lof"})

    def test_evaluation_when_label_exists(self):
        metrics = evaluate_detection(
            y_true=[0, 0, 1, 1],
            y_pred=[0, 1, 1, 0],
            y_score=[0.1, 0.7, 0.8, 0.2],
        )

        self.assertIn("precision", metrics)
        self.assertIn("recall", metrics)
        self.assertIn("f1_score", metrics)
        self.assertIn("accuracy", metrics)
        self.assertIn("confusion_matrix", metrics)
        self.assertIn("roc_auc", metrics)

    def test_per_anomaly_type_evaluation(self):
        metrics = evaluate_by_anomaly_type(
            pd.Series(["NONE", "HIGH_AMOUNT", "STRUCTURING", "NONE"]),
            y_pred=[0, 1, 0, 1],
            y_score=[0.1, 0.9, 0.2, 0.8],
        )

        self.assertIn("HIGH_AMOUNT", metrics)
        self.assertIn("STRUCTURING", metrics)
        self.assertEqual(metrics["HIGH_AMOUNT"]["support"], 1)

    def test_train_and_predict_entry_points(self):
        dataframe = sample_dataframe()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            data_path = temp_path / "transactions.csv"
            model_dir = temp_path / "models"
            output_dir = temp_path / "outputs"
            prediction_path = output_dir / "predictions.csv"
            dataframe.to_csv(data_path, index=False)

            metadata = train_models(
                data_path=data_path,
                model_dir=model_dir,
                output_dir=output_dir,
                n_estimators=20,
                n_neighbors=10,
                contamination=0.05,
                test_size=0.25,
                lof_max_train_rows=30,
            )

            self.assertTrue((model_dir / "isolation_forest.joblib").exists())
            self.assertTrue((model_dir / "lof.joblib").exists())
            self.assertTrue((model_dir / "preprocessor.joblib").exists())
            self.assertEqual(metadata["number_of_rows"], len(dataframe))
            self.assertEqual(metadata["evaluation_mode"], "holdout")
            self.assertEqual(metadata["model_parameters"]["lof"]["training_rows"], 30)
            self.assertIn("by_anomaly_type", metadata["evaluations"]["isolation_forest"])
            self.assertTrue((output_dir / "evaluation_isolation_forest.json").exists())
            self.assertTrue((output_dir / "evaluation_lof.json").exists())

            output_path = predict_anomalies(
                algorithm="lof",
                data_path=data_path,
                model_dir=model_dir,
                output=prediction_path,
            )
            predictions = pd.read_csv(output_path)

            self.assertIn("anomaly_label", predictions.columns)
            self.assertIn("anomaly_score", predictions.columns)
            self.assertIn("algorithm", predictions.columns)

            ensemble_output_path = predict_anomalies(
                algorithm="ensemble",
                data_path=data_path,
                model_dir=model_dir,
                output=output_dir / "ensemble_predictions.csv",
            )
            ensemble_predictions = pd.read_csv(ensemble_output_path)

            self.assertIn("isolation_forest_label", ensemble_predictions.columns)
            self.assertIn("lof_label", ensemble_predictions.columns)
            self.assertIn("ensemble_vote_count", ensemble_predictions.columns)
            self.assertEqual(set(ensemble_predictions["algorithm"]), {"ensemble"})
            self.assertTrue((output_dir / "evaluation_ensemble.json").exists())

    def test_tuning_writes_summary_and_results(self):
        dataframe = sample_dataframe()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            data_path = temp_path / "transactions.csv"
            output_dir = temp_path / "outputs"
            dataframe.to_csv(data_path, index=False)

            summary = tune_models(
                data_path=data_path,
                output_dir=output_dir,
                contaminations=[0.04],
                iforest_estimators=[20],
                iforest_max_samples=["auto"],
                lof_neighbors=[10],
                lof_metrics=["minkowski"],
                test_size=0.25,
            )

            self.assertTrue((output_dir / "tuning_results.csv").exists())
            self.assertTrue((output_dir / "tuning_summary.json").exists())
            self.assertIn("best", summary)

    @unittest.skipUnless(TORCH_AVAILABLE, "torch not installed")
    def test_train_models_with_autoencoder_predicts_all_detectors_end_to_end(self):
        dataframe = sample_dataframe(rows=80)

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            data_path = temp_path / "transactions.csv"
            model_dir = temp_path / "models"
            output_dir = temp_path / "outputs"
            prediction_dir = temp_path / "predictions"
            dataframe.to_csv(data_path, index=False)

            metadata = train_models(
                data_path=data_path,
                model_dir=model_dir,
                output_dir=output_dir,
                n_estimators=20,
                n_neighbors=10,
                contamination=0.05,
                include_autoencoder=True,
                autoencoder_epochs=1,
                autoencoder_batch_size=16,
                autoencoder_optimize_threshold=False,
                autoencoder_device="cpu",
            )

            self.assertTrue((model_dir / "isolation_forest.joblib").exists())
            self.assertTrue((model_dir / "lof.joblib").exists())
            self.assertTrue((model_dir / "autoencoder.joblib").exists())
            self.assertTrue((model_dir / "autoencoder_preprocessor.joblib").exists())
            self.assertTrue((output_dir / "evaluation_autoencoder.json").exists())
            self.assertIn("autoencoder", metadata["models"])
            self.assertIn("autoencoder", metadata["model_parameters"])
            self.assertEqual(
                metadata["autoencoder"]["normal_rows_used_for_training"],
                int(dataframe["is_anomaly"].eq(False).sum()),
            )

            expected_columns = {
                "anomaly_label",
                "anomaly_score",
                "algorithm",
            }
            for algorithm in ["isolation_forest", "lof", "autoencoder"]:
                output_path = predict_anomalies(
                    algorithm=algorithm,
                    data_path=data_path,
                    model_dir=model_dir,
                    output=prediction_dir / f"{algorithm}.csv",
                )
                predictions = pd.read_csv(output_path)

                self.assertEqual(len(predictions), len(dataframe))
                self.assertTrue(expected_columns <= set(predictions.columns))
                self.assertEqual(set(predictions["algorithm"]), {algorithm})
                self.assertTrue(set(predictions["anomaly_label"].unique()) <= {0, 1})
                self.assertIn("business_rule_label", predictions.columns)
                self.assertIn("business_rule_reasons", predictions.columns)

                if algorithm == "autoencoder":
                    self.assertIn("autoencoder_label", predictions.columns)
                else:
                    self.assertIn(f"{algorithm}_model_label", predictions.columns)


if __name__ == "__main__":
    unittest.main()

