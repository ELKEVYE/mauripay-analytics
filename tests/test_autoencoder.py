from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mauripay.detection.autoencoder import AutoencoderDetector  # noqa: E402
from mauripay.detection.business_rules import apply_business_rules  # noqa: E402
from mauripay.detection.evaluate_autoencoder_thresholds import (  # noqa: E402
    evaluate_autoencoder_thresholds,
)
from mauripay.detection.predict import predict_anomalies  # noqa: E402
from mauripay.detection.predict_autoencoder import (  # noqa: E402
    build_arg_parser,
    predict_autoencoder,
)
from mauripay.detection.train_autoencoder import (  # noqa: E402
    build_arg_parser as build_train_arg_parser,
)
from mauripay.detection.train_autoencoder import (  # noqa: E402
    build_error_analysis,
    optimize_threshold,
    train_autoencoder,
)
from mauripay.cli import build_parser as build_main_cli_parser  # noqa: E402
from mauripay.features.geographic import add_geographic_features  # noqa: E402
from mauripay.features.risk_signals import add_risk_signal_features  # noqa: E402
from mauripay.features.temporal import add_temporal_features  # noqa: E402
from mauripay.synthetic.generator import generate_transactions  # noqa: E402


TORCH_AVAILABLE = importlib.util.find_spec("torch") is not None


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed")
class AutoencoderDetectorTests(unittest.TestCase):
    def sample_matrix(self, rows: int = 24, columns: int = 6) -> np.ndarray:
        rng = np.random.default_rng(42)
        return rng.normal(0, 1, size=(rows, columns)).astype(np.float32)

    def make_detector(self) -> AutoencoderDetector:
        return AutoencoderDetector(
            encoding_dim=3,
            hidden_dims=(8, 4),
            epochs=2,
            batch_size=8,
            threshold_percentile=95,
            random_state=42,
            device="cpu",
        )

    def test_autoencoder_fit(self):
        X = self.sample_matrix()
        detector = self.make_detector()

        fitted = detector.fit(X)

        self.assertIs(fitted, detector)
        self.assertIsNotNone(detector.model)
        self.assertEqual(detector.input_dim_, X.shape[1])

    def test_autoencoder_predict_binary(self):
        X = self.sample_matrix()
        detector = self.make_detector().fit(X)

        predictions = detector.predict(X)

        self.assertTrue(set(predictions.tolist()) <= {0, 1})

    def test_autoencoder_scores_length(self):
        X = self.sample_matrix()
        detector = self.make_detector().fit(X)

        scores = detector.score_samples(X)

        self.assertEqual(len(scores), len(X))
        self.assertTrue(np.all(np.isfinite(scores)))

    def test_autoencoder_threshold_created(self):
        X = self.sample_matrix()
        detector = self.make_detector().fit(X)

        self.assertIsNotNone(detector.threshold_)
        self.assertTrue(np.isfinite(detector.threshold_))

    def test_autoencoder_results_format(self):
        X = self.sample_matrix()
        detector = self.make_detector().fit(X)

        result = detector.results(X)

        self.assertEqual(
            set(["anomaly_label", "anomaly_score", "algorithm"]),
            set(result.columns),
        )
        self.assertEqual(len(result), len(X))
        self.assertEqual(set(result["algorithm"]), {"autoencoder"})

    def test_autoencoder_save_load(self):
        X = self.sample_matrix()
        detector = self.make_detector().fit(X)

        with TemporaryDirectory() as temp_dir:
            path = detector.save(Path(temp_dir) / "autoencoder.joblib")
            loaded = AutoencoderDetector.load(path)

        self.assertEqual(loaded.input_dim_, detector.input_dim_)
        self.assertEqual(loaded.threshold_, detector.threshold_)
        self.assertEqual(len(loaded.predict(X)), len(X))

    def test_autoencoder_parameters(self):
        detector = self.make_detector()

        parameters = detector.parameters

        self.assertEqual(parameters["encoding_dim"], 3)
        self.assertEqual(parameters["hidden_dims"], (8, 4))
        self.assertEqual(parameters["epochs"], 2)
        self.assertEqual(parameters["batch_size"], 8)
        self.assertEqual(parameters["threshold_percentile"], 95)

    def test_autoencoder_rejects_invalid_hyperparameters(self):
        invalid_kwargs = [
            {"encoding_dim": 0},
            {"hidden_dims": (8, 0)},
            {"learning_rate": 0},
            {"epochs": 0},
            {"batch_size": 0},
            {"threshold_percentile": 100},
            {"device": "tpu"},
        ]

        for kwargs in invalid_kwargs:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    AutoencoderDetector(**kwargs)

    def test_autoencoder_rejects_non_finite_features(self):
        X = self.sample_matrix()
        X[0, 0] = np.nan

        with self.assertRaisesRegex(ValueError, "finite"):
            self.make_detector().fit(X)

    def test_autoencoder_rejects_feature_dimension_mismatch(self):
        X = self.sample_matrix(columns=6)
        detector = self.make_detector().fit(X)

        with self.assertRaisesRegex(ValueError, "features"):
            detector.score_samples(self.sample_matrix(columns=5))

    def test_autoencoder_small_dataset(self):
        X = self.sample_matrix(rows=1)
        detector = self.make_detector()

        detector.fit(X)

        self.assertIsNotNone(detector.threshold_)
        self.assertEqual(len(detector.score_samples(X)), 1)


class AutoencoderPredictionCliTests(unittest.TestCase):
    def test_predict_parser_accepts_threshold_percentile(self):
        args = build_arg_parser().parse_args(
            [
                "--data",
                "transactions.csv",
                "--threshold-percentile",
                "95",
            ]
        )

        self.assertEqual(args.threshold_percentile, 95)

    def test_generic_predict_parser_accepts_autoencoder(self):
        from mauripay.detection.predict import build_arg_parser as build_predict_parser

        args = build_predict_parser().parse_args(
            [
                "--model",
                "autoencoder",
                "--data",
                "transactions.csv",
            ]
        )

        self.assertEqual(args.model, "autoencoder")

    def test_main_cli_accepts_autoencoder_commands(self):
        pipeline_args = build_main_cli_parser().parse_args(
            [
                "train",
                "--data",
                "transactions.csv",
                "--include-autoencoder",
                "--autoencoder-epochs",
                "1",
            ]
        )
        train_args = build_main_cli_parser().parse_args(
            [
                "train-autoencoder",
                "--data",
                "transactions.csv",
                "--epochs",
                "1",
            ]
        )
        predict_args = build_main_cli_parser().parse_args(
            [
                "predict",
                "--model",
                "autoencoder",
                "--data",
                "transactions.csv",
            ]
        )

        self.assertEqual(pipeline_args.command, "train")
        self.assertTrue(pipeline_args.include_autoencoder)
        self.assertEqual(pipeline_args.autoencoder_epochs, 1)
        self.assertEqual(train_args.command, "train-autoencoder")
        self.assertEqual(train_args.epochs, 1)
        self.assertEqual(predict_args.model, "autoencoder")


class AutoencoderTrainingHelpersTests(unittest.TestCase):
    def test_optimize_threshold_selects_best_f1_candidate(self):
        optimization = optimize_threshold(
            y_true=[0, 0, 1, 1],
            anomaly_scores=[0.1, 0.2, 0.8, 0.9],
            percentiles=[25, 50, 75],
        )

        self.assertEqual(optimization["selected"]["f1_score"], 1.0)
        self.assertEqual(optimization["objective"], "maximize_f1_then_recall_then_precision")

    def test_error_analysis_exports_false_positive_and_false_negative_rows(self):
        dataframe = pd.DataFrame(
            {
                "transaction_id": ["tx1", "tx2", "tx3", "tx4"],
                "transaction_type": ["TRANSFER", "BILL_PAY", "TRANSFER", "CASH_OUT"],
                "channel": ["APP", "USSD", "APP", "AGENT"],
                "is_anomaly": [False, False, True, True],
                "anomaly_type": ["NONE", "NONE", "HIGH_AMOUNT", "STRUCTURING"],
            }
        )
        result = pd.DataFrame(
            {
                "anomaly_label": [0, 1, 1, 0],
                "anomaly_score": [0.1, 0.9, 0.8, 0.2],
            }
        )

        with TemporaryDirectory() as temp_dir:
            analysis = build_error_analysis(
                df=dataframe,
                y_true=[0, 0, 1, 1],
                result=result,
                output_directory=Path(temp_dir),
                label_column="is_anomaly",
            )

            self.assertEqual(analysis["false_positives"], 1)
            self.assertEqual(analysis["false_negatives"], 1)
            self.assertTrue(Path(analysis["error_file"]).exists())
            self.assertTrue(Path(analysis["analysis_file"]).exists())

    def test_train_parser_accepts_no_threshold_optimization(self):
        args = build_train_arg_parser().parse_args(
            [
                "--data",
                "transactions.csv",
                "--no-threshold-optimization",
            ]
        )

        self.assertTrue(args.no_threshold_optimization)

    @unittest.skipUnless(TORCH_AVAILABLE, "torch not installed")
    def test_autoencoder_train_predict_end_to_end_with_generic_predict(self):
        transactions = generate_transactions(
            rows=80,
            num_accounts=40,
            seed=321,
            anomaly_rate=0.08,
            tontine_rate=0.0,
            structuring_rate=0.0,
            high_frequency_rate=0.0,
        )
        dataframe = pd.DataFrame([tx.model_dump(mode="json") for tx in transactions])

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            data_path = temp_path / "transactions.csv"
            model_dir = temp_path / "models"
            output_dir = temp_path / "outputs"
            prediction_path = output_dir / "predictions_autoencoder.csv"
            dataframe.to_csv(data_path, index=False)

            metadata = train_autoencoder(
                data_path=data_path,
                model_dir=model_dir,
                output_dir=output_dir,
                epochs=1,
                batch_size=16,
                optimize_decision_threshold=False,
                device="cpu",
            )
            output_path = predict_anomalies(
                algorithm="autoencoder",
                data_path=data_path,
                model_dir=model_dir,
                output=prediction_path,
            )
            predictions = pd.read_csv(output_path)

            self.assertTrue(Path(metadata["model"]).exists())
            self.assertTrue(Path(metadata["preprocessor"]).exists())
            self.assertEqual(len(metadata["training_loss"]), 1)
            self.assertEqual(metadata["model_parameters"]["training_loss_epochs"], 1)
            self.assertIn("anomaly_label", predictions.columns)
            self.assertIn("anomaly_score", predictions.columns)
            self.assertIn("autoencoder_label", predictions.columns)
            self.assertIn("business_rule_label", predictions.columns)
            self.assertEqual(set(predictions["algorithm"]), {"autoencoder"})

    @unittest.skipUnless(TORCH_AVAILABLE, "torch not installed")
    def test_predict_autoencoder_exports_evaluation_when_labels_exist(self):
        transactions = generate_transactions(
            rows=80,
            num_accounts=40,
            seed=654,
            anomaly_rate=0.08,
            tontine_rate=0.0,
            structuring_rate=0.0,
            high_frequency_rate=0.0,
        )
        dataframe = pd.DataFrame([tx.model_dump(mode="json") for tx in transactions])

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            data_path = temp_path / "transactions.csv"
            model_dir = temp_path / "models"
            output_dir = temp_path / "outputs"
            prediction_path = output_dir / "predictions_autoencoder.csv"
            dataframe.to_csv(data_path, index=False)

            train_autoencoder(
                data_path=data_path,
                model_dir=model_dir,
                output_dir=output_dir,
                epochs=1,
                batch_size=16,
                optimize_decision_threshold=False,
                device="cpu",
            )
            output_path = predict_autoencoder(
                data_path=data_path,
                model_dir=model_dir,
                output=prediction_path,
            )
            evaluation_path = output_path.parent / "evaluation_autoencoder.json"
            analysis_path = output_path.parent / "autoencoder_error_analysis.json"

            self.assertTrue(evaluation_path.exists())
            self.assertTrue(analysis_path.exists())
            evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
            self.assertEqual(evaluation["label_column"], "is_anomaly")
            self.assertEqual(evaluation["prediction_file"], str(prediction_path))

    @unittest.skipUnless(TORCH_AVAILABLE, "torch not installed")
    def test_threshold_evaluation_does_not_export_short_evaluation_file(self):
        transactions = generate_transactions(
            rows=80,
            num_accounts=40,
            seed=987,
            anomaly_rate=0.08,
            tontine_rate=0.0,
            structuring_rate=0.0,
            high_frequency_rate=0.0,
        )
        dataframe = pd.DataFrame([tx.model_dump(mode="json") for tx in transactions])

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            data_path = temp_path / "transactions.csv"
            model_dir = temp_path / "models"
            train_output_dir = temp_path / "train_outputs"
            threshold_output_dir = temp_path / "threshold_outputs"
            dataframe.to_csv(data_path, index=False)

            train_autoencoder(
                data_path=data_path,
                model_dir=model_dir,
                output_dir=train_output_dir,
                epochs=1,
                batch_size=16,
                optimize_decision_threshold=False,
                device="cpu",
            )
            evaluate_autoencoder_thresholds(
                validation_data=data_path,
                model_dir=model_dir,
                output_dir=threshold_output_dir,
            )

            self.assertFalse(
                (threshold_output_dir / "evaluation_autoencoder.json").exists()
            )
            self.assertTrue(
                (threshold_output_dir / "autoencoder_threshold_evaluation.json").exists()
            )

    def test_business_rule_flags_failed_zero_fee_transactions(self):
        dataframe = pd.DataFrame(
            {
                "status": ["SUCCESS", "FAILED"],
                "fees": [100.0, 0.0],
            }
        )
        result = pd.DataFrame(
            {
                "anomaly_label": [0, 0],
                "anomaly_score": [0.1, 0.2],
                "algorithm": ["autoencoder", "autoencoder"],
            }
        )

        adjusted = apply_business_rules(dataframe, result)

        self.assertEqual(adjusted["anomaly_label"].tolist(), [0, 1])
        self.assertEqual(adjusted["autoencoder_label"].tolist(), [0, 0])
        self.assertEqual(adjusted["business_rule_label"].tolist(), [0, 1])
        self.assertEqual(adjusted["autoencoder_model_score"].tolist(), [0.1, 0.2])
        self.assertGreater(
            adjusted["anomaly_score"].iloc[1],
            adjusted["autoencoder_model_score"].max(),
        )

    def test_business_rules_flag_operator_outage_cluster(self):
        dataframe = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    ["2026-01-01 10:00", "2026-01-01 10:40", "2026-01-01 11:30"],
                    utc=True,
                ),
                "operator": ["Bankily", "Bankily", "Bankily"],
                "status": ["FAILED", "FAILED", "SUCCESS"],
                "fees": [0.0, 0.0, 100.0],
            }
        )
        result = pd.DataFrame(
            {
                "anomaly_label": [0, 0, 0],
                "anomaly_score": [0.1, 0.1, 0.1],
                "algorithm": ["autoencoder"] * 3,
            }
        )

        adjusted = apply_business_rules(dataframe, result)

        self.assertEqual(adjusted["anomaly_label"].tolist(), [1, 1, 0])
        self.assertIn("operator_outage_cluster", adjusted["business_rule_reasons"].iloc[1])

    def test_business_rules_flag_high_amount_sender_profile(self):
        dataframe = pd.DataFrame(
            {
                "timestamp": pd.date_range("2026-01-01", periods=4, freq="h"),
                "sender_id": ["A", "A", "A", "A"],
                "receiver_id": ["B", "B", "B", "B"],
                "amount": [10_000, 12_000, 11_000, 200_000],
                "fees": [100, 120, 110, 2_000],
                "status": ["SUCCESS"] * 4,
                "transaction_type": ["TRANSFER"] * 4,
                "sender_wilaya": ["Nouakchott-Ouest"] * 4,
                "receiver_wilaya": ["Nouakchott-Ouest"] * 4,
            }
        )
        result = pd.DataFrame(
            {
                "anomaly_label": [0, 0, 0, 0],
                "anomaly_score": [0.1, 0.1, 0.1, 0.1],
                "algorithm": ["autoencoder"] * 4,
            }
        )

        adjusted = apply_business_rules(dataframe, result)

        self.assertEqual(adjusted["anomaly_label"].tolist()[-1], 1)
        self.assertIn("high_amount_sender_profile", adjusted["business_rule_reasons"].iloc[-1])

    def test_business_rules_flag_high_amount_type_limit(self):
        dataframe = pd.DataFrame(
            {
                "transaction_type": ["BILL_PAY", "BILL_PAY", "AIRTIME"],
                "amount": [7_500, 25_000, 8_000],
                "fees": [75, 250, 80],
                "status": ["SUCCESS"] * 3,
            }
        )
        result = pd.DataFrame(
            {
                "anomaly_label": [0, 0, 0],
                "anomaly_score": [0.1, 0.1, 0.1],
                "algorithm": ["isolation_forest"] * 3,
            }
        )

        adjusted = apply_business_rules(dataframe, result)

        self.assertEqual(adjusted["anomaly_label"].tolist(), [0, 1, 1])
        self.assertIn("high_amount_type_limit", adjusted["business_rule_reasons"].iloc[1])
        self.assertIn("high_amount_type_limit", adjusted["business_rule_reasons"].iloc[2])

    def test_business_rules_do_not_force_new_far_sender_location(self):
        dataframe = pd.DataFrame(
            {
                "timestamp": pd.date_range("2026-01-01", periods=4, freq="h"),
                "sender_id": ["A", "A", "A", "A"],
                "receiver_id": ["B", "B", "B", "C"],
                "amount": [10_000, 12_000, 11_000, 15_000],
                "fees": [100, 120, 110, 150],
                "status": ["SUCCESS"] * 4,
                "transaction_type": ["TRANSFER"] * 4,
                "sender_wilaya": ["Nouakchott-Ouest"] * 4,
                "receiver_wilaya": [
                    "Nouakchott-Ouest",
                    "Nouakchott-Ouest",
                    "Nouakchott-Ouest",
                    "Dakhlet Nouadhibou",
                ],
            }
        )
        result = pd.DataFrame(
            {
                "anomaly_label": [0, 0, 0, 0],
                "anomaly_score": [0.1, 0.1, 0.1, 0.1],
                "algorithm": ["autoencoder"] * 4,
            }
        )

        adjusted = apply_business_rules(dataframe, result)

        self.assertEqual(adjusted["anomaly_label"].tolist()[-1], 0)
        self.assertNotIn("new_far_sender_location", adjusted["business_rule_reasons"].iloc[-1])

    def test_business_rules_flag_unusual_location_with_sender_history(self):
        dataframe = pd.DataFrame(
            {
                "timestamp": pd.date_range("2026-01-01", periods=4, freq="h"),
                "sender_id": ["A", "A", "A", "A"],
                "receiver_id": ["B", "B", "B", "C"],
                "amount": [10_000, 12_000, 11_000, 60_000],
                "fees": [100, 120, 110, 600],
                "status": ["SUCCESS"] * 4,
                "transaction_type": ["TRANSFER"] * 4,
                "sender_wilaya": ["Nouakchott-Ouest"] * 4,
                "receiver_wilaya": [
                    "Nouakchott-Ouest",
                    "Nouakchott-Ouest",
                    "Nouakchott-Ouest",
                    "Dakhlet Nouadhibou",
                ],
                "wilaya_distance_km": [0.0, 0.0, 0.0, 470.0],
            }
        )
        result = pd.DataFrame(
            {
                "anomaly_label": [0, 0, 0, 0],
                "anomaly_score": [0.1, 0.1, 0.1, 0.1],
                "algorithm": ["autoencoder"] * 4,
            }
        )

        adjusted = apply_business_rules(dataframe, result)

        self.assertEqual(adjusted["anomaly_label"].tolist()[-1], 1)
        self.assertIn("unusual_remote_location", adjusted["business_rule_reasons"].iloc[-1])

    def test_business_rules_flag_receiver_profile_location_mismatch(self):
        dataframe = pd.DataFrame(
            {
                "timestamp": pd.date_range("2026-01-01", periods=4, freq="h"),
                "sender_id": ["A", "B", "C", "A"],
                "receiver_id": ["B", "A", "A", "B"],
                "amount": [10_000, 11_000, 12_000, 15_000],
                "fees": [100, 110, 120, 150],
                "status": ["SUCCESS"] * 4,
                "transaction_type": ["TRANSFER"] * 4,
                "sender_wilaya": [
                    "Nouakchott-Ouest",
                    "Nouakchott-Sud",
                    "Nouakchott-Nord",
                    "Nouakchott-Ouest",
                ],
                "receiver_wilaya": [
                    "Nouakchott-Sud",
                    "Nouakchott-Ouest",
                    "Nouakchott-Ouest",
                    "Dakhlet Nouadhibou",
                ],
            }
        )
        result = pd.DataFrame(
            {
                "anomaly_label": [0, 0, 0, 0],
                "anomaly_score": [0.1, 0.1, 0.1, 0.1],
                "algorithm": ["autoencoder"] * 4,
            }
        )

        adjusted = apply_business_rules(dataframe, result)

        self.assertEqual(adjusted["anomaly_label"].tolist()[-1], 1)
        self.assertIn(
            "receiver_profile_location_mismatch",
            adjusted["business_rule_reasons"].iloc[-1],
        )

    def test_risk_features_include_client_sequence_context(self):
        dataframe = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    [
                        "2026-01-01 10:00",
                        "2026-01-01 10:02",
                        "2026-01-01 10:04",
                        "2026-01-01 10:06",
                    ],
                    utc=True,
                ),
                "sender_id": ["A", "A", "A", "A"],
                "receiver_id": ["B", "B", "B", "C"],
                "amount": [20_000, 20_500, 19_900, 50_000],
                "fees": [200, 205, 199, 500],
                "status": ["SUCCESS"] * 4,
                "transaction_type": ["TRANSFER"] * 4,
                "sender_wilaya": ["Nouakchott-Ouest"] * 4,
                "receiver_wilaya": [
                    "Nouakchott-Ouest",
                    "Nouakchott-Ouest",
                    "Nouakchott-Ouest",
                    "Dakhlet Nouadhibou",
                ],
                "is_ramadan": [False] * 4,
            }
        )

        features = add_risk_signal_features(
            add_geographic_features(add_temporal_features(dataframe))
        )

        self.assertIn("tx_count_5min_to_1h_ratio", features.columns)
        self.assertIn("sender_receiver_is_new_receiver", features.columns)
        self.assertIn("sender_distance_gap_km", features.columns)
        self.assertIn("same_receiver_similar_amount_5min", features.columns)
        self.assertEqual(features["same_receiver_similar_amount_5min"].iloc[2], 1)


if __name__ == "__main__":
    unittest.main()
