from __future__ import annotations

import json
import re
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_JSON = PROJECT_ROOT / "benchmarks" / "results" / "full_10k_benchmark.json"
BENCHMARK_MARKDOWN = PROJECT_ROOT / "benchmarks" / "results_full.md"


class BenchmarkDocumentationTests(unittest.TestCase):
    def test_full_10k_markdown_table_matches_json_results(self):
        benchmark = json.loads(BENCHMARK_JSON.read_text(encoding="utf-8"))
        markdown = BENCHMARK_MARKDOWN.read_text(encoding="utf-8")

        self.assertIn(f"Lignes : {benchmark['rows']}", markdown)
        self.assertIn(f"Normales : {benchmark['normal_rows']}", markdown)
        self.assertIn(f"Anomalies : {benchmark['anomaly_rows']}", markdown)

        rows = {}
        for line in markdown.splitlines():
            if not line.startswith("| MauriPay-S 10K |"):
                continue
            parts = [part.strip() for part in line.strip("|").split("|")]
            rows[parts[1]] = parts[2:]

        display_names = {
            "isolation_forest": "Isolation Forest",
            "lof": "LOF",
            "autoencoder": "Autoencoder",
        }
        for result in benchmark["results"]:
            row = rows[display_names[result["model"]]]
            expected = [
                f"{result['precision']:.4f}",
                f"{result['recall']:.4f}",
                f"{result['f1_score']:.4f}",
                f"{result['roc_auc']:.4f}",
                f"{result['train_time_seconds']:.4f}",
                f"{result['inference_time_seconds']:.4f}",
                str(result["n_detected_anomalies"]),
            ]
            self.assertEqual(row, expected)

    def test_full_10k_markdown_date_matches_json_timestamp(self):
        benchmark = json.loads(BENCHMARK_JSON.read_text(encoding="utf-8"))
        markdown = BENCHMARK_MARKDOWN.read_text(encoding="utf-8")

        match = re.search(r"Date : (?P<date>.+)", markdown)
        self.assertIsNotNone(match)
        generated_at = datetime.fromisoformat(benchmark["generated_at"])
        local_time = generated_at.astimezone(timezone(timedelta(hours=2)))

        self.assertEqual(match.group("date"), local_time.strftime("%Y-%m-%d %H:%M:%S +02:00"))


if __name__ == "__main__":
    unittest.main()
