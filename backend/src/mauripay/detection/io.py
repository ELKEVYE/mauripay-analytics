from __future__ import annotations

from pathlib import Path

import pandas as pd


def project_backend_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_table(path: str | Path) -> pd.DataFrame:
    input_path = Path(path)
    if not input_path.exists():
        raise FileNotFoundError(f"Data file not found: {input_path}")

    suffix = input_path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(input_path)
    if suffix == ".json":
        return pd.read_json(input_path)
    if suffix == ".parquet":
        return pd.read_parquet(input_path)

    raise ValueError("Unsupported data format. Use .csv, .json, or .parquet")
