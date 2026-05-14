from __future__ import annotations

import random
import sys
import unittest
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mauripay.ingestion.schema import Transaction  # noqa: E402
from mauripay.synthetic.generator import (  # noqa: E402
    create_accounts,
    generate_tontine_transactions,
    generate_transactions,
    parse_utc_datetime,
)
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

    def test_bill_pay_requires_bill_provider(self):
        payload = valid_payload()
        payload["transaction_type"] = "BILL_PAY"
        payload["bill_provider"] = None

        with self.assertRaises(ValidationError):
            Transaction(**payload)


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


if __name__ == "__main__":
    unittest.main()
