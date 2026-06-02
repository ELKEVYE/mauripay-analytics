from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover
    TestClient = None

from mauripay.api.app import create_app  # noqa: E402
from mauripay.synthetic.generator import generate_transactions  # noqa: E402


@unittest.skipIf(TestClient is None, "fastapi is not installed")
class DetectionApiTests(unittest.TestCase):
    def sample_csv(self, rows: int = 120) -> tuple[TemporaryDirectory, Path]:
        temp_dir = TemporaryDirectory()
        temp_path = Path(temp_dir.name)
        transactions = generate_transactions(
            rows=rows,
            num_accounts=60,
            seed=456,
            anomaly_rate=0.04,
            tontine_rate=0.0,
            structuring_rate=0.01,
            high_frequency_rate=0.01,
        )
        dataframe = pd.DataFrame([tx.model_dump(mode="json") for tx in transactions])
        data_path = temp_path / "transactions.csv"
        dataframe.to_csv(data_path, index=False)
        return temp_dir, data_path

    def test_generate_dataset_endpoint(self):
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        output_path = Path(temp_dir.name) / "generated.csv"
        client = TestClient(create_app())

        response = client.post(
            "/ingest/generate",
            json={
                "rows": 50,
                "accounts": 20,
                "seed": 789,
                "output_path": str(output_path),
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "generated")
        self.assertEqual(payload["rows"], 50)
        self.assertTrue(output_path.exists())
        self.assertIn("stats", payload)
    def test_models_endpoint_returns_iforest_and_lof(self):
        client = TestClient(create_app())
        response = client.get("/detect/models")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("isolation_forest", payload["available_algorithms"])
        self.assertIn("lof", payload["available_algorithms"])

    def test_train_and_predict_endpoints(self):
        temp_dir, data_path = self.sample_csv()
        self.addCleanup(temp_dir.cleanup)
        client = TestClient(create_app())

        model_dir = Path(temp_dir.name) / "models"
        api_output_dir = Path(temp_dir.name) / "outputs"

        train_response = client.post(
            "/detect/train",
            json={
                "data_path": str(data_path),
                "contamination": 0.05,
                "n_estimators": 20,
                "n_neighbors": 10,
                "test_size": 0.25,
                "model_dir": str(model_dir),
                "output_dir": str(api_output_dir),
            },
        )
        self.assertEqual(train_response.status_code, 200)
        self.assertEqual(train_response.json()["status"], "trained")

        output_path = Path(temp_dir.name) / "predictions.csv"
        predict_response = client.post(
            "/detect/predict",
            json={
                "algorithm": "isolation_forest",
                "data_path": str(data_path),
                "output_path": str(output_path),
                "model_dir": str(model_dir),
            },
        )
        self.assertEqual(predict_response.status_code, 200)
        payload = predict_response.json()
        self.assertEqual(payload["status"], "predicted")
        self.assertEqual(payload["algorithm"], "isolation_forest")
        self.assertEqual(payload["rows"], 120)
        self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
