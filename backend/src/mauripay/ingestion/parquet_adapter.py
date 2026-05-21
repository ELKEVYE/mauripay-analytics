from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from mauripay.ingestion.common import (
    IngestionResult,
    ensure_existing_path,
    records_to_ingestion_result,
    records_to_transactions,
)
from mauripay.ingestion.schema import Transaction


def _iter_parquet_records(
    path: Path,
    batch_size: int = 10000,
) -> Iterable[Mapping[str, Any]]:
    try:
        import pyarrow.dataset as ds
    except ImportError:
        try:
            import pandas as pd
        except ImportError as exc:
            raise ImportError(
                "Pour lire un fichier Parquet, installe pandas ou pyarrow"
            ) from exc

        dataframe = pd.read_parquet(path)
        yield from dataframe.to_dict(orient="records")
        return

    dataset = ds.dataset(path, format="parquet")

    for batch in dataset.to_batches(batch_size=batch_size):
        yield from batch.to_pylist()


def load_parquet_transactions(input_path: str | Path) -> list[Transaction]:
    """
    Load and validate MauriPay transactions from a Parquet file.
    """

    path = ensure_existing_path(input_path)

    return records_to_transactions(_iter_parquet_records(path), source=str(path))


def load_parquet_transactions_report(
    input_path: str | Path,
    batch_size: int = 10000,
) -> IngestionResult:
    """
    Load MauriPay transactions from Parquet by batches and return all row errors.
    """

    path = ensure_existing_path(input_path)

    return records_to_ingestion_result(
        _iter_parquet_records(path, batch_size=batch_size),
        source=str(path),
    )


__all__ = ["load_parquet_transactions", "load_parquet_transactions_report"]
