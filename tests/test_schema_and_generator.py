from __future__ import annotations

import csv
import importlib.util
import json
import random
import sys
import tempfile
import unittest
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mauripay.ingestion import load_transactions  # noqa: E402
from mauripay.ingestion.csv_adapter import (  # noqa: E402
    load_csv_transactions,
    load_csv_transactions_report,
)
from mauripay.ingestion.json_adapter import (  # noqa: E402
    load_json_transactions,
    load_jsonl_transactions,
)
from mauripay.ingestion.parquet_adapter import load_parquet_transactions  # noqa: E402
from mauripay.features.geographic import add_geographic_features  # noqa: E402
from mauripay.features.encoding import one_hot_encode_categories  # noqa: E402
from mauripay.features.engineering import (  # noqa: E402
    build_features,
    model_feature_columns,
    transactions_to_polars_dataframe,
)
from mauripay.features.scaling import (  # noqa: E402
    min_max_scale_features,
    zscore_scale_features,
)
from mauripay.features.temporal import (  # noqa: E402
    add_flow_ratio_features,
    add_temporal_features,
)
from mauripay.ingestion.schema import BillProvider, Operator, Transaction  # noqa: E402
from mauripay.synthetic.config import (  # noqa: E402
    BILL_PROVIDERS,
    BILL_PROVIDER_WEIGHTS,
    OPERATORS,
    OPERATOR_WEIGHTS,
)
from mauripay.synthetic.generator import (  # noqa: E402
    create_accounts,
    generate_tontine_transactions,
    generate_transactions,
    parse_utc_datetime,
)
from mauripay.synthetic.exporters import export_csv, export_parquet  # noqa: E402
from mauripay.synthetic.validate import compute_tontine_stats  # noqa: E402


def valid_payload() -> dict[str, object]:
    return {
        "timestamp": "2026-02-20T21:15:00+00:00",
        "sender_id": "ACC_00001",
        "receiver_id": "ACC_00002",
        "amount": Decimal("15000.00"),
        "currency": "MRU",
        "transaction_type": "TRANSFER",
        "channel": "USSD",
        "operator": "Bankily",
        "sender_wilaya": "Nouakchott-Ouest",
        "receiver_wilaya": "Nouakchott-Nord",
        "status": "SUCCESS",
        "fees": Decimal("150.00"),
        "is_ramadan": True,
        "bill_provider": None,
        "origin_country": None,
        "is_anomaly": False,
        "anomaly_type": "NONE",
    }


def valid_file_payload() -> dict[str, object]:
    return {
        "transaction_id": "550e8400-e29b-41d4-a716-446655440001",
        "timestamp": "2026-02-20T21:15:00Z",
        "sender_id": "ACC_00001",
        "receiver_id": "ACC_00002",
        "amount": "15000.00",
        "currency": "MRU",
        "transaction_type": "TRANSFER",
        "channel": "USSD",
        "operator": "Bankily",
        "sender_wilaya": "Nouakchott-Ouest",
        "receiver_wilaya": "Nouakchott-Nord",
        "status": "SUCCESS",
        "fees": "150.00",
        "is_ramadan": "True",
        "bill_provider": "",
        "origin_country": "",
        "is_anomaly": "False",
        "anomaly_type": "NONE",
    }


class SchemaValidationTests(unittest.TestCase):
    def test_valid_transaction_is_accepted(self):
        transaction = Transaction(**valid_payload())

        self.assertEqual(transaction.sender_id, "ACC_00001")
        self.assertEqual(transaction.receiver_id, "ACC_00002")
        self.assertEqual(transaction.currency, "MRU")

    def test_same_sender_and_receiver_is_rejected(self):
        payload = valid_payload()
        payload["receiver_id"] = payload["sender_id"]

        with self.assertRaises(ValidationError):
            Transaction(**payload)

    def test_sender_receiver_same_rejected(self):
        payload = valid_payload()
        payload["receiver_id"] = payload["sender_id"]

        with self.assertRaises(ValidationError):
            Transaction(**payload)

    def test_invalid_amount_rejected(self):
        payload = valid_payload()
        payload["amount"] = Decimal("0.00")

        with self.assertRaises(ValidationError):
            Transaction(**payload)

    def test_invalid_currency_rejected(self):
        payload = valid_payload()
        payload["currency"] = "EUR"

        with self.assertRaises(ValidationError):
            Transaction(**payload)

    def test_bill_pay_requires_bill_provider(self):
        payload = valid_payload()
        payload["transaction_type"] = "BILL_PAY"
        payload["bill_provider"] = None

        with self.assertRaises(ValidationError):
            Transaction(**payload)

    def test_amount_accepts_cdc_upper_limit(self):
        payload = valid_payload()
        payload["amount"] = Decimal("10000000.00")
        payload["fees"] = Decimal("100000.00")

        transaction = Transaction(**payload)

        self.assertEqual(transaction.amount, Decimal("10000000.00"))

    def test_configured_operators_are_accepted_by_schema(self):
        enum_values = {operator.value for operator in Operator}

        self.assertEqual(set(OPERATORS), enum_values)
        self.assertEqual(set(OPERATOR_WEIGHTS), enum_values)
        self.assertAlmostEqual(sum(OPERATOR_WEIGHTS.values()), 1.0)

        for operator in OPERATORS:
            payload = valid_payload()
            payload["operator"] = operator

            transaction = Transaction(**payload)

            self.assertEqual(transaction.operator, operator)

    def test_configured_bill_providers_are_accepted_by_schema(self):
        enum_values = {provider.value for provider in BillProvider}

        self.assertEqual(set(BILL_PROVIDERS), enum_values)
        self.assertEqual(set(BILL_PROVIDER_WEIGHTS), enum_values)
        self.assertAlmostEqual(sum(BILL_PROVIDER_WEIGHTS.values()), 1.0)

        for provider in BILL_PROVIDERS:
            payload = valid_payload()
            payload["transaction_type"] = "BILL_PAY"
            payload["bill_provider"] = provider
            payload["fees"] = Decimal("0.00")

            transaction = Transaction(**payload)

            self.assertEqual(transaction.bill_provider, provider)


class GeneratorTests(unittest.TestCase):
    def test_generator_outputs_valid_transactions(self):
        transactions = generate_transactions(
            rows=100,
            num_accounts=50,
            seed=123,
            anomaly_rate=0.01,
            tontine_rate=0.01,
            structuring_rate=0.001,
            high_frequency_rate=0.001,
        )

        self.assertEqual(len(transactions), 100)
        self.assertTrue(all(isinstance(tx, Transaction) for tx in transactions))
        self.assertTrue({tx.currency for tx in transactions} <= {"MRU", "XOF", "USD"})

    def test_tontine_sequence_is_normal_group_behavior(self):
        random.seed(42)
        accounts = create_accounts(num_accounts=50)
        start = parse_utc_datetime("2026-01-01")
        end = parse_utc_datetime("2026-12-31", end_of_day=True)

        sequence = generate_tontine_transactions(
            accounts=accounts,
            start=start,
            end=end,
        )

        receiver_ids = {tx.receiver_id for tx in sequence}
        amounts = {tx.amount for tx in sequence}
        timestamps = [tx.timestamp for tx in sequence]

        self.assertGreaterEqual(len(sequence), 10)
        self.assertLessEqual(len(sequence), 30)
        self.assertEqual(len(receiver_ids), 1)
        self.assertEqual(len(amounts), 1)
        self.assertLessEqual(max(timestamps) - min(timestamps), timedelta(hours=2))
        self.assertTrue(all(tx.transaction_type == "TRANSFER" for tx in sequence))
        self.assertTrue(all(tx.is_anomaly is False for tx in sequence))
        self.assertEqual({tx.anomaly_type for tx in sequence}, {"NONE"})

    def test_validator_detects_tontine_like_group(self):
        import pandas as pd

        random.seed(42)
        accounts = create_accounts(num_accounts=50)
        start = parse_utc_datetime("2026-01-01")
        end = parse_utc_datetime("2026-12-31", end_of_day=True)
        sequence = generate_tontine_transactions(
            accounts=accounts,
            start=start,
            end=end,
        )
        dataframe = pd.DataFrame(
            [tx.model_dump(mode="json") for tx in sequence]
        )

        stats = compute_tontine_stats(dataframe)

        self.assertGreaterEqual(stats["candidate_group_count"], 1)
        self.assertGreaterEqual(stats["candidate_transaction_count"], 10)


class IngestionAdapterTests(unittest.TestCase):
    def test_load_csv_valid_file(self):
        transactions = generate_transactions(
            rows=10000,
            num_accounts=500,
            seed=456,
            anomaly_rate=0.01,
            tontine_rate=0.001,
            structuring_rate=0.001,
            high_frequency_rate=0.001,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mauripay_s_10k.csv"
            export_csv(transactions, path)

            loaded_transactions = load_csv_transactions(path)

        self.assertEqual(len(loaded_transactions), 10000)
        self.assertTrue(all(isinstance(tx, Transaction) for tx in loaded_transactions))

    def test_csv_adapter_validates_rows_and_uses_default_fees(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "transactions.csv"
            payload = valid_file_payload()
            payload.pop("fees")

            with path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=list(payload))
                writer.writeheader()
                writer.writerow(payload)

            transactions = load_csv_transactions(path)

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].fees, Decimal("0.00"))
        self.assertIsNone(transactions[0].origin_country)

    def test_json_adapter_accepts_list_payload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "transactions.json"
            path.write_text(
                json.dumps([valid_file_payload()]),
                encoding="utf-8",
            )

            transactions = load_json_transactions(path)

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].sender_id, "ACC_00001")

    @unittest.skipIf(
        importlib.util.find_spec("pandas") is None
        or importlib.util.find_spec("pyarrow") is None,
        "pandas/pyarrow not installed",
    )
    def test_parquet_adapter_accepts_dataframe_payload(self):
        import pandas as pd

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "transactions.parquet"
            pd.DataFrame([valid_file_payload()]).to_parquet(path, index=False)

            transactions = load_parquet_transactions(path)

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].receiver_id, "ACC_00002")

    @unittest.skipIf(
        importlib.util.find_spec("pandas") is None
        or importlib.util.find_spec("pyarrow") is None,
        "pandas/pyarrow not installed",
    )
    def test_load_parquet_valid_file(self):
        transactions = generate_transactions(
            rows=2000,
            num_accounts=500,
            seed=789,
            anomaly_rate=0.01,
            tontine_rate=0.001,
            structuring_rate=0.001,
            high_frequency_rate=0.001,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mauripay_valid.parquet"
            export_parquet(transactions, path)

            loaded_transactions = load_parquet_transactions(path)

        self.assertEqual(len(loaded_transactions), 2000)
        self.assertTrue(all(isinstance(tx, Transaction) for tx in loaded_transactions))

    def test_adapter_rejects_invalid_business_rule(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "transactions.json"
            payload = valid_file_payload()
            payload["receiver_id"] = payload["sender_id"]
            path.write_text(json.dumps([payload]), encoding="utf-8")

            with self.assertRaises(ValueError):
                load_json_transactions(path)

    def test_csv_report_collects_errors_and_keeps_valid_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "transactions.csv"
            valid = valid_file_payload()
            invalid = valid_file_payload()
            invalid["receiver_id"] = invalid["sender_id"]

            with path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=list(valid))
                writer.writeheader()
                writer.writerow(valid)
                writer.writerow(invalid)
                writer.writerow(valid)

            result = load_csv_transactions_report(path)

        self.assertFalse(result.ok)
        self.assertEqual(result.total_rows, 3)
        self.assertEqual(result.valid_rows, 2)
        self.assertEqual(result.invalid_rows, 1)
        self.assertEqual(result.errors[0].row_number, 2)
        self.assertIn("receiver_id", result.errors[0].payload)

    def test_central_loader_detects_json_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "transactions.json"
            path.write_text(
                json.dumps({"transactions": [valid_file_payload()]}),
                encoding="utf-8",
            )

            transactions = load_transactions(path)

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].operator, "Bankily")

    def test_central_loader_can_return_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "transactions.json"
            invalid = valid_file_payload()
            invalid["amount"] = "-1.00"
            path.write_text(
                json.dumps([valid_file_payload(), invalid]),
                encoding="utf-8",
            )

            result = load_transactions(path, report=True)

        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.valid_rows, 1)
        self.assertEqual(result.invalid_rows, 1)

    def test_jsonl_adapter_reads_one_transaction_per_line(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "transactions.jsonl"
            path.write_text(
                "\n".join(
                    [
                        json.dumps(valid_file_payload()),
                        json.dumps(valid_file_payload()),
                    ]
                ),
                encoding="utf-8",
            )

            transactions = load_jsonl_transactions(path)

        self.assertEqual(len(transactions), 2)
        self.assertEqual(transactions[1].sender_id, "ACC_00001")


class TemporalFeatureTests(unittest.TestCase):
    def test_temporal_features_are_computed_per_sender(self):
        import pandas as pd

        dataframe = pd.DataFrame(
            [
                {
                    "timestamp": "2026-02-20T10:00:00Z",
                    "sender_id": "ACC_00001",
                    "amount": "100.00",
                    "is_ramadan": "False",
                },
                {
                    "timestamp": "2026-02-20T10:30:00Z",
                    "sender_id": "ACC_00001",
                    "amount": "200.00",
                    "is_ramadan": "True",
                },
                {
                    "timestamp": "2026-02-20T11:00:00Z",
                    "sender_id": "ACC_00001",
                    "amount": "300.00",
                    "is_ramadan": "False",
                },
                {
                    "timestamp": "2026-02-20T11:00:00Z",
                    "sender_id": "ACC_00002",
                    "amount": "999.00",
                    "is_ramadan": "False",
                },
            ]
        )

        features = add_temporal_features(dataframe)

        self.assertEqual(features.loc[2, "tx_count_1h"], 3)
        self.assertEqual(features.loc[2, "amount_sum_1h"], 600)
        self.assertEqual(features.loc[2, "amount_mean_1h"], 200)
        self.assertAlmostEqual(features.loc[2, "amount_std_1h"], 100)
        self.assertEqual(features.loc[2, "tx_count_24h"], 3)
        self.assertEqual(features.loc[2, "tx_count_7d"], 3)
        self.assertEqual(features.loc[3, "tx_count_1h"], 1)
        self.assertEqual(features.loc[2, "hour"], 11)
        self.assertEqual(features.loc[2, "day_of_week"], 4)
        self.assertEqual(features.loc[2, "is_weekend"], 0)
        self.assertEqual(features.loc[1, "is_ramadan"], 1)

    def test_flow_ratio_features_are_computed_for_sender_account(self):
        import pandas as pd

        dataframe = pd.DataFrame(
            [
                {
                    "timestamp": "2026-02-20T10:00:00Z",
                    "sender_id": "ACC_00002",
                    "receiver_id": "ACC_00001",
                    "amount": "100.00",
                },
                {
                    "timestamp": "2026-02-20T10:30:00Z",
                    "sender_id": "ACC_00001",
                    "receiver_id": "ACC_00003",
                    "amount": "50.00",
                },
            ]
        )

        features = add_flow_ratio_features(dataframe)

        self.assertEqual(features.loc[0, "incoming_amount_24h"], 0)
        self.assertEqual(features.loc[0, "outgoing_amount_24h"], 100)
        self.assertEqual(features.loc[0, "incoming_outgoing_ratio_24h"], 0)
        self.assertEqual(features.loc[1, "incoming_amount_24h"], 100)
        self.assertEqual(features.loc[1, "outgoing_amount_24h"], 50)
        self.assertEqual(features.loc[1, "incoming_outgoing_ratio_24h"], 2)


class GeographicFeatureTests(unittest.TestCase):
    def test_geographic_features_are_computed_from_wilayas(self):
        import pandas as pd

        dataframe = pd.DataFrame(
            [
                {
                    "sender_wilaya": "Nouakchott-Ouest",
                    "receiver_wilaya": "Nouakchott-Ouest",
                },
                {
                    "sender_wilaya": "Nouakchott-Ouest",
                    "receiver_wilaya": "Dakhlet Nouadhibou",
                },
            ]
        )

        features = add_geographic_features(dataframe)

        self.assertEqual(features.loc[0, "sender_wilaya_code"], 0)
        self.assertEqual(features.loc[0, "receiver_wilaya_code"], 0)
        self.assertEqual(features.loc[0, "is_cross_wilaya"], 0)
        self.assertEqual(features.loc[0, "wilaya_distance_km"], 0)
        self.assertEqual(features.loc[1, "sender_wilaya_code"], 0)
        self.assertEqual(features.loc[1, "receiver_wilaya_code"], 10)
        self.assertEqual(features.loc[1, "is_cross_wilaya"], 1)
        self.assertEqual(features.loc[1, "wilaya_distance_km"], 470)


class EncodingFeatureTests(unittest.TestCase):
    def test_categorical_features_are_one_hot_encoded(self):
        import pandas as pd

        dataframe = pd.DataFrame(
            [
                {
                    "transaction_type": "TRANSFER",
                    "channel": "USSD",
                    "operator": "Bankily",
                    "sender_wilaya": "Nouakchott-Ouest",
                    "receiver_wilaya": "Dakhlet Nouadhibou",
                    "currency": "MRU",
                },
                {
                    "transaction_type": "BILL_PAY",
                    "channel": "APP",
                    "operator": "Sedad",
                    "sender_wilaya": "Nouakchott-Sud",
                    "receiver_wilaya": "Nouakchott-Nord",
                    "currency": "USD",
                },
            ]
        )

        encoded = one_hot_encode_categories(dataframe)

        self.assertEqual(encoded.loc[0, "channel_USSD"], 1)
        self.assertEqual(encoded.loc[0, "channel_APP"], 0)
        self.assertEqual(encoded.loc[0, "operator_Bankily"], 1)
        self.assertEqual(encoded.loc[0, "operator_Sedad"], 0)
        self.assertEqual(encoded.loc[1, "transaction_type_BILL_PAY"], 1)
        self.assertEqual(encoded.loc[1, "currency_USD"], 1)
        self.assertIn("channel_AGENT", encoded.columns)
        self.assertEqual(encoded["channel_AGENT"].sum(), 0)


class ScalingFeatureTests(unittest.TestCase):
    def test_min_max_scaling_adds_scaled_columns(self):
        import pandas as pd

        dataframe = pd.DataFrame(
            {
                "amount": [100.0, 200.0, 300.0],
                "tx_count_1h": [1, 1, 1],
            }
        )

        scaled = min_max_scale_features(
            dataframe,
            columns=["amount", "tx_count_1h"],
        )

        self.assertEqual(scaled["amount_scaled"].tolist(), [0.0, 0.5, 1.0])
        self.assertEqual(scaled["tx_count_1h_scaled"].tolist(), [0.0, 0.0, 0.0])
        self.assertIn("amount", scaled.columns)

    def test_zscore_scaling_adds_zscore_columns(self):
        import pandas as pd

        dataframe = pd.DataFrame({"amount": [100.0, 200.0, 300.0]})

        scaled = zscore_scale_features(dataframe, columns=["amount"])

        self.assertAlmostEqual(scaled.loc[0, "amount_zscore"], -1.224744871, places=6)
        self.assertAlmostEqual(scaled.loc[1, "amount_zscore"], 0.0, places=6)
        self.assertAlmostEqual(scaled.loc[2, "amount_zscore"], 1.224744871, places=6)


class FeatureEngineeringPipelineTests(unittest.TestCase):
    def test_build_features_returns_numeric_ml_dataframe(self):
        first_payload = valid_payload()
        second_payload = valid_payload()
        second_payload["transaction_id"] = "550e8400-e29b-41d4-a716-446655440099"
        second_payload["timestamp"] = "2026-02-20T21:45:00+00:00"
        second_payload["amount"] = Decimal("20000.00")
        second_payload["receiver_wilaya"] = "Dakhlet Nouadhibou"
        second_payload["channel"] = "APP"
        second_payload["operator"] = "Sedad"
        second_payload["transaction_type"] = "BILL_PAY"
        second_payload["bill_provider"] = "SOMELEC"
        second_payload["fees"] = Decimal("0.00")

        transactions = [
            Transaction(**first_payload),
            Transaction(**second_payload),
        ]

        features = build_features(transactions)

        self.assertEqual(len(features), 2)
        self.assertIn("amount", features.columns)
        self.assertIn("amount_scaled", features.columns)
        self.assertIn("amount_zscore", features.columns)
        self.assertIn("tx_count_1h", features.columns)
        self.assertIn("incoming_amount_24h", features.columns)
        self.assertIn("outgoing_amount_24h", features.columns)
        self.assertIn("incoming_outgoing_ratio_24h", features.columns)
        self.assertIn("incoming_outgoing_ratio_24h_scaled", features.columns)
        self.assertIn("incoming_outgoing_ratio_24h_zscore", features.columns)
        self.assertIn("sender_wilaya_code", features.columns)
        self.assertIn("receiver_wilaya_code", features.columns)
        self.assertIn("is_cross_wilaya", features.columns)
        self.assertIn("wilaya_distance_km", features.columns)
        self.assertIn("channel_USSD", features.columns)
        self.assertIn("channel_APP", features.columns)
        self.assertIn("operator_Bankily", features.columns)
        self.assertIn("operator_Sedad", features.columns)
        self.assertIn("transaction_type_TRANSFER", features.columns)
        self.assertIn("transaction_type_BILL_PAY", features.columns)
        self.assertIn("is_anomaly", features.columns)
        self.assertNotIn("transaction_id", features.columns)
        self.assertNotIn("sender_id", features.columns)
        self.assertNotIn("timestamp", features.columns)
        self.assertNotIn("is_anomaly", model_feature_columns(features))

    @unittest.skipIf(
        importlib.util.find_spec("polars") is None,
        "polars not installed",
    )
    def test_build_features_pipeline_accepts_polars_engine(self):
        transactions = [
            Transaction(**valid_payload()),
            Transaction(
                **{
                    **valid_payload(),
                    "timestamp": "2026-02-20T22:00:00+00:00",
                    "amount": Decimal("25000.00"),
                    "receiver_id": "ACC_00003",
                }
            ),
        ]

        polars_frame = transactions_to_polars_dataframe(transactions)
        features = build_features(transactions, dataframe_engine="polars")

        self.assertEqual(polars_frame.height, 2)
        self.assertEqual(len(features), 2)
        self.assertIn("amount_scaled", features.columns)
        self.assertIn("amount_zscore", features.columns)


if __name__ == "__main__":
    unittest.main()
