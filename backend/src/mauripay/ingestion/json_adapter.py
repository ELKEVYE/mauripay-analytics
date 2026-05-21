from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mauripay.ingestion.common import (
    IngestionResult,
    ensure_existing_path,
    records_to_ingestion_result,
    records_to_transactions,
)
from mauripay.ingestion.schema import Transaction


def _extract_records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict) and isinstance(data.get("transactions"), list):
        records = data["transactions"]
    else:
        raise ValueError(
            "Le JSON doit contenir une liste de transactions ou une cle "
            "'transactions'"
        )

    if not all(isinstance(record, dict) for record in records):
        raise ValueError("Chaque transaction JSON doit etre un objet")

    return records


def load_json_transactions(input_path: str | Path) -> list[Transaction]:
    """
    Load and validate MauriPay transactions from a JSON file.
    """

    path = ensure_existing_path(input_path)

    with path.open(encoding="utf-8") as file:
        data = json.load(file)

    return records_to_transactions(_extract_records(data), source=str(path))


def load_json_transactions_report(input_path: str | Path) -> IngestionResult:
    """
    Load MauriPay transactions from a JSON file and return all row errors.
    """

    path = ensure_existing_path(input_path)

    with path.open(encoding="utf-8") as file:
        data = json.load(file)

    return records_to_ingestion_result(_extract_records(data), source=str(path))


def _iter_json_lines(path: Path):
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()

            if not stripped:
                continue

            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"JSON Lines invalide dans {path}, ligne {line_number}: "
                    f"{exc.msg}"
                ) from exc

            if not isinstance(record, dict):
                raise ValueError(
                    f"Chaque ligne JSON Lines doit etre un objet dans {path}, "
                    f"ligne {line_number}"
                )

            yield record


def load_jsonl_transactions(input_path: str | Path) -> list[Transaction]:
    """
    Load and validate MauriPay transactions from a JSON Lines file.
    """

    path = ensure_existing_path(input_path)
    return records_to_transactions(_iter_json_lines(path), source=str(path))


def load_jsonl_transactions_report(input_path: str | Path) -> IngestionResult:
    """
    Load MauriPay transactions from JSON Lines and return all row errors.
    """

    path = ensure_existing_path(input_path)
    return records_to_ingestion_result(_iter_json_lines(path), source=str(path))


__all__ = [
    "load_json_transactions",
    "load_json_transactions_report",
    "load_jsonl_transactions",
    "load_jsonl_transactions_report",
]
