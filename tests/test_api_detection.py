from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mauripay.api.app import create_app  # noqa: E402
from mauripay.api.routes import detect as detect_module  # noqa: E402


SAMPLE_PATH = "src/mauripay/ingestion/samples/sample.csv"


def api_request(method: str, path: str, **kwargs) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def test_stats_endpoint_returns_expected_fields():
    response = api_request(
        "GET",
        "/stats",
        params={"dataset_path": SAMPLE_PATH},
    )

    assert response.status_code == 200
    assert {
        "total_transactions",
        "total_amount",
        "average_amount",
        "anomalies_count",
        "failure_rate",
        "by_type",
        "by_channel",
    } <= set(response.json())


def test_geo_endpoint_returns_wilaya_aggregates():
    response = api_request(
        "GET",
        "/geo",
        params={"dataset_path": SAMPLE_PATH},
    )

    assert response.status_code == 200
    wilayas = response.json()["wilayas"]
    assert wilayas
    assert {
        "wilaya",
        "transactions",
        "total_amount",
        "anomalies_count",
        "failure_rate",
    } <= set(wilayas[0])


def test_detect_endpoint_returns_anomalies_detected(monkeypatch):
    predictions = pd.DataFrame(
        [
            {
                "transaction_id": "TX-1",
                "anomaly_label": 1,
                "anomaly_score": 0.95,
                "algorithm": "isolation_forest",
            },
            {
                "transaction_id": "TX-2",
                "anomaly_label": 0,
                "anomaly_score": 0.05,
                "algorithm": "isolation_forest",
            },
        ]
    )
    monkeypatch.setattr(
        detect_module,
        "predict_anomalies",
        lambda **_: Path("mock_predictions.csv"),
    )
    monkeypatch.setattr(detect_module.pd, "read_csv", lambda *_args, **_kwargs: predictions)

    response = api_request(
        "POST",
        "/detect",
        json={
            "algorithm": "isolation_forest",
            "data_path": SAMPLE_PATH,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["anomalies_detected"] == 1
    assert payload["total_transactions"] == 2


def test_prediction_preview_can_return_all_anomalies():
    predictions = pd.DataFrame(
        [
            {
                "transaction_id": f"TX-{index}",
                "anomaly_label": 1,
                "anomaly_score": 0.8,
            }
            for index in range(105)
        ]
    )

    preview = detect_module._prediction_preview(predictions, limit=None)

    assert len(preview) == 105
    assert preview[0]["transaction_id"] == "TX-0"
    assert preview[-1]["transaction_id"] == "TX-104"
