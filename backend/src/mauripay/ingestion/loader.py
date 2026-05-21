from __future__ import annotations

from pathlib import Path
from typing import overload

from mauripay.ingestion.common import IngestionResult, ensure_existing_path
from mauripay.ingestion.csv_adapter import (
    load_csv_transactions,
    load_csv_transactions_report,
)
from mauripay.ingestion.json_adapter import (
    load_json_transactions,
    load_json_transactions_report,
    load_jsonl_transactions,
    load_jsonl_transactions_report,
)
from mauripay.ingestion.parquet_adapter import (
    load_parquet_transactions,
    load_parquet_transactions_report,
)
from mauripay.ingestion.schema import Transaction


@overload
def load_transactions(
    input_path: str | Path,
    *,
    report: bool = False,
) -> list[Transaction]: ...


@overload
def load_transactions(
    input_path: str | Path,
    *,
    report: bool,
) -> list[Transaction] | IngestionResult: ...


def load_transactions(
    input_path: str | Path,
    *,
    report: bool = False,
) -> list[Transaction] | IngestionResult:
    """
    Load MauriPay transactions by inferring the adapter from the file extension.
    """

    path = ensure_existing_path(input_path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        if report:
            return load_csv_transactions_report(path)
        return load_csv_transactions(path)

    if suffix == ".json":
        if report:
            return load_json_transactions_report(path)
        return load_json_transactions(path)

    if suffix == ".jsonl":
        if report:
            return load_jsonl_transactions_report(path)
        return load_jsonl_transactions(path)

    if suffix == ".parquet":
        if report:
            return load_parquet_transactions_report(path)
        return load_parquet_transactions(path)

    raise ValueError(
        "Format d'ingestion non supporte. Extensions acceptees: "
        ".csv, .json, .jsonl, .parquet"
    )


__all__ = ["load_transactions"]
