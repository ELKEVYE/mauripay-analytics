from __future__ import annotations

import csv
from pathlib import Path

from mauripay.ingestion.common import (
    IngestionResult,
    ensure_existing_path,
    normalize_payload,
    normalize_value,
    records_to_ingestion_result,
    records_to_transactions,
)
from mauripay.ingestion.schema import Transaction


def load_csv_transactions(input_path: str | Path) -> list[Transaction]:
    """
    Load and validate MauriPay transactions from a CSV file.
    """

    path = ensure_existing_path(input_path)

    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return records_to_transactions(reader, source=str(path))


def load_csv_transactions_report(input_path: str | Path) -> IngestionResult:
    """
    Load MauriPay transactions from a CSV file and return all row errors.
    """

    path = ensure_existing_path(input_path)

    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return records_to_ingestion_result(reader, source=str(path))


__all__ = [
    "load_csv_transactions",
    "load_csv_transactions_report",
    "normalize_payload",
    "normalize_value",
    "records_to_ingestion_result",
    "records_to_transactions",
]
