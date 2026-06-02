from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from mauripay.features.geographic import add_geographic_features
from mauripay.features.risk_signals import add_risk_signal_features
from mauripay.features.temporal import add_flow_ratio_features, add_temporal_features


LABEL_COLUMNS = {
    "is_anomaly",
    "anomaly_type",
    "anomaly_label",
    "label",
    "target",
    "fraud",
    "is_fraud",
}

ID_COLUMNS = {
    "transaction_id",
    "sender_id",
    "receiver_id",
}

DATE_NAME_HINTS = ("timestamp", "date", "datetime", "created_at", "updated_at")


@dataclass
class FeatureSelection:
    input_columns: list[str] = field(default_factory=list)
    ignored_columns: list[str] = field(default_factory=list)
    numerical_columns: list[str] = field(default_factory=list)
    categorical_columns: list[str] = field(default_factory=list)
    datetime_columns: list[str] = field(default_factory=list)
    derived_datetime_columns: list[str] = field(default_factory=list)
    project_feature_layers: list[str] = field(default_factory=list)
    feature_names: list[str] = field(default_factory=list)


class TransactionFeatureEngineer:
    """Dynamic feature engineering for MauriPay transaction datasets."""

    def __init__(self) -> None:
        self.selection = FeatureSelection()
        self._preprocessor: ColumnTransformer | None = None

    @staticmethod
    def _is_id_column(column: str) -> bool:
        lower = column.lower()
        return lower in ID_COLUMNS or lower == "id" or lower.endswith("_id")

    @staticmethod
    def _is_label_column(column: str) -> bool:
        return column.lower() in LABEL_COLUMNS

    @staticmethod
    def _is_datetime_like(series: pd.Series, column: str) -> bool:
        lower = column.lower()
        if not any(hint in lower for hint in DATE_NAME_HINTS):
            return False
        parsed = pd.to_datetime(series, utc=True, errors="coerce")
        return bool(parsed.notna().mean() >= 0.8)

    @staticmethod
    def _truthy_to_number(series: pd.Series) -> pd.Series:
        if series.dtype == bool:
            return series.astype(int)

        lowered = series.astype(str).str.lower()
        known_boolean = lowered.isin(["true", "false", "1", "0", "yes", "no"])
        if known_boolean.mean() >= 0.8:
            return lowered.map(
                {
                    "true": 1,
                    "1": 1,
                    "yes": 1,
                    "false": 0,
                    "0": 0,
                    "no": 0,
                }
            )

        return series

    @staticmethod
    def _derived_names(column: str) -> list[str]:
        prefix = "" if column == "timestamp" else f"{column}_"
        return [
            f"{prefix}hour",
            f"{prefix}day_of_week",
            f"{prefix}day_of_month",
            f"{prefix}month",
            f"{prefix}is_weekend",
        ]

    def _prepare_datetime_features(
        self,
        df: pd.DataFrame,
        datetime_columns: list[str],
    ) -> pd.DataFrame:
        working = df.copy()

        for column in datetime_columns:
            parsed = pd.to_datetime(working[column], utc=True, errors="coerce")
            hour, day_of_week, day_of_month, month, is_weekend = self._derived_names(
                column
            )
            working[hour] = parsed.dt.hour
            working[day_of_week] = parsed.dt.dayofweek
            working[day_of_month] = parsed.dt.day
            working[month] = parsed.dt.month
            working[is_weekend] = parsed.dt.dayofweek.isin([5, 6]).astype("Int64")

        return working.drop(columns=datetime_columns, errors="ignore")

    @staticmethod
    def _has_columns(df: pd.DataFrame, columns: set[str]) -> bool:
        return columns <= set(df.columns)

    def _add_project_features(self, df: pd.DataFrame, *, fit: bool) -> pd.DataFrame:
        """Add reusable project features before IDs are removed."""
        working = df.copy()
        applied_layers: list[str] = []

        if self._has_columns(working, {"sender_id", "timestamp", "amount"}):
            working = add_temporal_features(working)
            applied_layers.append("temporal")

        if self._has_columns(working, {"sender_id", "receiver_id", "timestamp", "amount"}):
            working = add_flow_ratio_features(working)
            applied_layers.append("flow_ratio")

        if self._has_columns(working, {"sender_wilaya", "receiver_wilaya"}):
            working = add_geographic_features(working)
            applied_layers.append("geographic")

        working = add_risk_signal_features(working)
        applied_layers.append("risk_signals")

        if fit:
            self.selection.project_feature_layers = applied_layers

        return working

    def _prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        working = self._add_project_features(df, fit=False)
        working = self._prepare_datetime_features(working, self.selection.datetime_columns)

        for column in working.columns:
            if column in self.selection.categorical_columns:
                working[column] = working[column].fillna("UNKNOWN").astype(str)
            else:
                working[column] = self._truthy_to_number(working[column])

        return working

    def fit(self, df: pd.DataFrame) -> "TransactionFeatureEngineer":
        if df.empty:
            raise ValueError("Cannot fit feature engineering on an empty dataset")

        input_columns = list(df.columns)
        enriched = self._add_project_features(df, fit=True)
        enriched_columns = list(enriched.columns)
        ignored = [
            column
            for column in enriched_columns
            if self._is_id_column(column) or self._is_label_column(column)
        ]
        candidate_columns = [column for column in enriched_columns if column not in ignored]
        datetime_columns = [
            column
            for column in candidate_columns
            if self._is_datetime_like(enriched[column], column)
        ]

        self.selection.input_columns = input_columns
        self.selection.ignored_columns = ignored + datetime_columns
        self.selection.datetime_columns = datetime_columns
        self.selection.derived_datetime_columns = [
            derived
            for column in datetime_columns
            for derived in self._derived_names(column)
        ]

        prepared = self._prepare_datetime_features(enriched[candidate_columns], datetime_columns)

        numerical_columns: list[str] = []
        categorical_columns: list[str] = []

        for column in prepared.columns:
            series = self._truthy_to_number(prepared[column])
            numeric_series = pd.to_numeric(series, errors="coerce")
            if numeric_series.notna().sum() == 0:
                categorical_columns.append(column)
            elif pd.api.types.is_numeric_dtype(series) or numeric_series.notna().mean() >= 0.8:
                prepared[column] = numeric_series
                numerical_columns.append(column)
            else:
                categorical_columns.append(column)

        if not numerical_columns and not categorical_columns:
            raise ValueError("No usable numerical or categorical feature columns found")

        self.selection.numerical_columns = numerical_columns
        self.selection.categorical_columns = categorical_columns

        for column in numerical_columns:
            prepared[column] = pd.to_numeric(prepared[column], errors="coerce")

        for column in categorical_columns:
            prepared[column] = prepared[column].fillna("UNKNOWN").astype(str)

        self._preprocessor = ColumnTransformer(
            transformers=[
                (
                    "num",
                    Pipeline(
                        steps=[
                            ("imputer", SimpleImputer(strategy="median")),
                            ("scaler", StandardScaler()),
                        ]
                    ),
                    numerical_columns,
                ),
                (
                    "cat",
                    Pipeline(
                        steps=[
                            ("imputer", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
                            (
                                "encoder",
                                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                            ),
                        ]
                    ),
                    categorical_columns,
                ),
            ],
            remainder="drop",
        )
        self._preprocessor.fit(prepared[numerical_columns + categorical_columns])
        self.selection.feature_names = self.feature_names
        return self

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        if self._preprocessor is None:
            raise RuntimeError("Feature engineer is not fitted. Call fit() first.")

        prepared = self._prepare(df)

        for column in self.selection.numerical_columns:
            if column not in prepared.columns:
                prepared[column] = np.nan
            prepared[column] = pd.to_numeric(prepared[column], errors="coerce")

        for column in self.selection.categorical_columns:
            if column not in prepared.columns:
                prepared[column] = "UNKNOWN"

        return self._preprocessor.transform(
            prepared[self.selection.numerical_columns + self.selection.categorical_columns]
        )

    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        return self.fit(df).transform(df)

    @property
    def feature_names(self) -> list[str]:
        if self._preprocessor is None:
            return []
        try:
            return list(self._preprocessor.get_feature_names_out())
        except AttributeError:
            return []

    def metadata(self) -> dict[str, Any]:
        self.selection.feature_names = self.feature_names
        return {
            "input_columns": self.selection.input_columns,
            "ignored_columns": self.selection.ignored_columns,
            "numerical_columns_used": self.selection.numerical_columns,
            "categorical_columns_used": self.selection.categorical_columns,
            "datetime_columns": self.selection.datetime_columns,
            "derived_datetime_columns": self.selection.derived_datetime_columns,
            "project_feature_layers": self.selection.project_feature_layers,
            "feature_names": self.selection.feature_names,
        }

    def save(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, output_path)
        return output_path

    @classmethod
    def load(cls, path: str | Path) -> "TransactionFeatureEngineer":
        preprocessor = joblib.load(Path(path))
        if not isinstance(preprocessor, cls):
            raise TypeError(
                f"Expected {cls.__name__} in {path}, got {type(preprocessor).__name__}"
            )
        return preprocessor
