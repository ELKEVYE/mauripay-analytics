from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from mauripay.ingestion.schema import Transaction


EMPTY_VALUES = {"", "nan", "null"}


@dataclass(frozen=True)
class IngestionError:
    source: str
    row_number: int
    errors: list[dict[str, Any]]
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IngestionResult:
    transactions: list[Transaction]
    errors: list[IngestionError]
    total_rows: int

    @property
    def valid_rows(self) -> int:
        return len(self.transactions)

    @property
    def invalid_rows(self) -> int:
        return len(self.errors)

    @property
    def ok(self) -> bool:
        return not self.errors


def normalize_value(value: Any) -> Any:
    """
    Convert empty values from files into None for optional schema fields.
    """

    if value is None:
        return None

    try:
        if value != value:
            return None
    except TypeError:
        pass

    if isinstance(value, str) and value.strip().lower() in EMPTY_VALUES:
        return None

    return value


def normalize_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    """
    Prepare a raw input record for Transaction validation.
    """

    return {
        key: normalize_value(value)
        for key, value in record.items()
        if key is not None
    }


def records_to_ingestion_result(
    records: Iterable[Mapping[str, Any]],
    source: str = "records",
) -> IngestionResult:
    """
    Validate raw records and keep every row-level validation error.
    """

    transactions: list[Transaction] = []
    errors: list[IngestionError] = []
    total_rows = 0

    for row_number, record in enumerate(records, start=1):
        total_rows = row_number
        payload = normalize_payload(record)

        try:
            transactions.append(Transaction.model_validate(payload))
        except ValidationError as exc:
            errors.append(
                IngestionError(
                    source=source,
                    row_number=row_number,
                    errors=exc.errors(),
                    payload=payload,
                )
            )

    return IngestionResult(
        transactions=transactions,
        errors=errors,
        total_rows=total_rows,
    )


def records_to_transactions(
    records: Iterable[Mapping[str, Any]],
    source: str = "records",
) -> list[Transaction]:
    """
    Validate raw records and return Transaction models.
    """

    result = records_to_ingestion_result(records, source=source)

    if result.errors:
        first_error = result.errors[0]
        raise ValueError(
            f"Transaction invalide dans {source}, ligne "
            f"{first_error.row_number}: {first_error.errors}"
        )

    return result.transactions


def ensure_existing_path(input_path: str | Path) -> Path:
    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    return path


__all__ = [
    "IngestionError",
    "IngestionResult",
    "ensure_existing_path",
    "normalize_payload",
    "normalize_value",
    "records_to_ingestion_result",
    "records_to_transactions",
]
