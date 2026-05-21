from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

from mauripay.ingestion.schema import (
    Channel,
    Currency,
    Operator,
    TransactionType,
    Wilaya,
)


CATEGORICAL_VALUES: Mapping[str, Sequence[str]] = {
    "transaction_type": [value.value for value in TransactionType],
    "channel": [value.value for value in Channel],
    "operator": [value.value for value in Operator],
    "sender_wilaya": [value.value for value in Wilaya],
    "receiver_wilaya": [value.value for value in Wilaya],
    "currency": [value.value for value in Currency],
}

CATEGORICAL_COLUMNS = list(CATEGORICAL_VALUES)
ENCODED_FEATURE_COLUMNS = [
    f"{column}_{value}"
    for column, values in CATEGORICAL_VALUES.items()
    for value in values
]


def _validate_categories(
    dataframe: pd.DataFrame,
    category_values: Mapping[str, Sequence[str]],
) -> None:
    for column, allowed_values in category_values.items():
        unknown_values = sorted(
            set(dataframe[column].dropna()) - set(allowed_values)
        )

        if unknown_values:
            unknown = ", ".join(str(value) for value in unknown_values)
            raise ValueError(f"Valeur categorielle inconnue dans {column}: {unknown}")


def one_hot_encode_categories(
    dataframe: pd.DataFrame,
    *,
    columns: Sequence[str] | None = None,
    drop_original: bool = False,
) -> pd.DataFrame:
    """
    Add one-hot encoded columns for categorical transaction fields.
    """

    selected_columns = list(columns or CATEGORICAL_COLUMNS)
    category_values = {
        column: CATEGORICAL_VALUES[column]
        for column in selected_columns
    }
    missing_columns = set(selected_columns) - set(dataframe.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Colonnes manquantes pour l'encodage: {missing}")

    encoded = dataframe.copy()

    _validate_categories(encoded, category_values)

    for column, allowed_values in category_values.items():
        for value in allowed_values:
            encoded[f"{column}_{value}"] = (encoded[column] == value).astype(int)

    if drop_original:
        encoded = encoded.drop(columns=selected_columns)

    return encoded


__all__ = [
    "CATEGORICAL_COLUMNS",
    "CATEGORICAL_VALUES",
    "ENCODED_FEATURE_COLUMNS",
    "one_hot_encode_categories",
]
