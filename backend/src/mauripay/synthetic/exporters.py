# backend/src/mauripay/synthetic/exporters.py

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
from typing import Any


COLUMNS = [
    "transaction_id",
    "timestamp",
    "sender_id",
    "receiver_id",
    "amount",
    "currency",
    "transaction_type",
    "channel",
    "operator",
    "sender_wilaya",
    "receiver_wilaya",
    "status",
    "fees",
    "is_ramadan",
    "bill_provider",
    "origin_country",
    "is_anomaly",
    "anomaly_type",
]


def ensure_parent_dir(output_path: str | Path) -> Path:
    """
    Crée le dossier parent si nécessaire.

    Exemple :
    data/generated/mauripay_s.csv

    Si data/generated/ n'existe pas, il sera créé.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def normalize_transaction(transaction: Any) -> dict[str, Any]:
    """
    Convertit une transaction Pydantic ou un dictionnaire
    en dictionnaire exportable.

    - Les champs manquants deviennent ""
    - Les valeurs None deviennent ""
    - L'ordre des colonnes est contrôlé par COLUMNS
    """
    if hasattr(transaction, "model_dump"):
        data = transaction.model_dump(mode="json")
    elif isinstance(transaction, dict):
        data = transaction
    else:
        raise TypeError(
            "transaction doit être un modèle Pydantic ou un dict"
        )

    normalized: dict[str, Any] = {}

    for column in COLUMNS:
        value = data.get(column)

        if value is None:
            normalized[column] = ""
        else:
            normalized[column] = value

    return normalized


def export_csv(transactions: list[Any], output_path: str | Path) -> Path:
    """
    Exporte les transactions en CSV.
    """
    path = ensure_parent_dir(output_path)

    rows = [normalize_transaction(tx) for tx in transactions]

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return path


def export_json(transactions: list[Any], output_path: str | Path) -> Path:
    """
    Exporte les transactions en JSON.
    """
    path = ensure_parent_dir(output_path)

    rows = [normalize_transaction(tx) for tx in transactions]

    with path.open("w", encoding="utf-8") as file:
        json.dump(rows, file, ensure_ascii=False, indent=2)

    return path


def export_parquet(transactions: list[Any], output_path: str | Path) -> Path:
    """
    Exporte les transactions en Parquet.

    Le format Parquet est utile pour les gros volumes de données,
    par exemple 100 000 ou 1 000 000 transactions.

    Dépendances nécessaires :
        pip install pandas pyarrow
    """
    path = ensure_parent_dir(output_path)

    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError(
            "Pour exporter en Parquet, installe pandas : "
            "pip install pandas pyarrow"
        ) from exc

    if importlib.util.find_spec("pyarrow") is None:
        raise ImportError(
            "Pour exporter en Parquet, installe pyarrow : "
            "pip install pyarrow"
        )

    rows = [normalize_transaction(tx) for tx in transactions]

    dataframe = pd.DataFrame(rows, columns=COLUMNS)

    dataframe.to_parquet(
        path,
        index=False,
        engine="pyarrow",
    )

    return path


def export_transactions(
    transactions: list[Any],
    output_path: str | Path,
) -> Path:
    """
    Exporte les transactions selon l'extension du fichier.

    Extensions supportées :
    - .csv
    - .json
    - .parquet
    """
    path = Path(output_path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return export_csv(transactions, path)

    if suffix == ".json":
        return export_json(transactions, path)

    if suffix == ".parquet":
        return export_parquet(transactions, path)

    raise ValueError(
        "Format non supporté. Utilise .csv, .json ou .parquet"
    )
