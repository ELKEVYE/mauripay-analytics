from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import HTTPException

from mauripay.detection.io import load_table, project_backend_root


def backend_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return project_backend_root() / candidate


def load_dataset(path: str | Path) -> pd.DataFrame:
    data_path = backend_path(path)
    if not data_path.exists():
        raise HTTPException(status_code=404, detail=f"Data file not found: {data_path}")

    try:
        return load_table(data_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def require_columns(dataframe: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in dataframe.columns]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(missing)}",
        )


def anomaly_mask(dataframe: pd.DataFrame) -> pd.Series:
    if "anomaly_label" in dataframe.columns:
        return dataframe["anomaly_label"].fillna(0).astype(int).eq(1)
    if "is_anomaly" in dataframe.columns:
        return dataframe["is_anomaly"].astype(str).str.lower().isin(
            {"true", "1", "yes", "anomaly", "fraud"}
        )
    return pd.Series(False, index=dataframe.index)


def failure_mask(dataframe: pd.DataFrame) -> pd.Series:
    if "status" not in dataframe.columns:
        return pd.Series(False, index=dataframe.index)
    return dataframe["status"].astype(str).str.upper().eq("FAILED")


def numeric_amount(dataframe: pd.DataFrame) -> pd.Series:
    require_columns(dataframe, ["amount"])
    return pd.to_numeric(dataframe["amount"], errors="coerce").fillna(0.0)


def value_counts(dataframe: pd.DataFrame, column: str) -> dict[str, int]:
    if column not in dataframe.columns:
        return {}
    counts = dataframe[column].fillna("UNKNOWN").astype(str).value_counts()
    return {str(key): int(value) for key, value in counts.items()}
