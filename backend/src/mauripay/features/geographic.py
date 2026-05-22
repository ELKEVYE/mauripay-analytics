from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

import pandas as pd

from mauripay.ingestion.schema import Wilaya


EARTH_RADIUS_KM = 6371.0

WILAYA_VALUES = [wilaya.value for wilaya in Wilaya]
WILAYA_CODES = {
    wilaya: code
    for code, wilaya in enumerate(WILAYA_VALUES)
}

# Approximate administrative centroids used for ML features, not routing.
WILAYA_COORDINATES = {
    "Nouakchott-Ouest": (18.08, -15.98),
    "Nouakchott-Nord": (18.12, -15.92),
    "Nouakchott-Sud": (17.98, -15.94),
    "Hodh El Chargui": (18.23, -7.02),
    "Hodh El Gharbi": (16.62, -9.42),
    "Assaba": (16.15, -11.40),
    "Gorgol": (16.05, -13.07),
    "Brakna": (17.02, -13.92),
    "Trarza": (17.87, -14.98),
    "Adrar": (20.52, -13.05),
    "Dakhlet Nouadhibou": (20.93, -17.03),
    "Tagant": (18.65, -11.42),
    "Guidimakha": (15.25, -12.25),
    "Tiris Zemmour": (22.68, -12.71),
    "Inchiri": (19.75, -15.90),
}

WILAYA_DISTANCE_OVERRIDES_KM = {
    frozenset(("Nouakchott-Ouest", "Dakhlet Nouadhibou")): 470.0,
    frozenset(("Nouakchott-Nord", "Dakhlet Nouadhibou")): 470.0,
    frozenset(("Nouakchott-Sud", "Dakhlet Nouadhibou")): 470.0,
}

GEOGRAPHIC_FEATURE_COLUMNS = [
    "sender_wilaya_code",
    "receiver_wilaya_code",
    "is_cross_wilaya",
    "wilaya_distance_km",
]


def _haversine_distance_km(
    first_coordinates: tuple[float, float],
    second_coordinates: tuple[float, float],
) -> float:
    first_latitude, first_longitude = first_coordinates
    second_latitude, second_longitude = second_coordinates

    latitude_delta = radians(second_latitude - first_latitude)
    longitude_delta = radians(second_longitude - first_longitude)

    first_latitude = radians(first_latitude)
    second_latitude = radians(second_latitude)

    a = (
        sin(latitude_delta / 2) ** 2
        + cos(first_latitude)
        * cos(second_latitude)
        * sin(longitude_delta / 2) ** 2
    )
    c = 2 * asin(sqrt(a))

    return EARTH_RADIUS_KM * c


def _validate_wilayas(series: pd.Series, column_name: str) -> None:
    unknown_wilayas = sorted(set(series.dropna()) - set(WILAYA_CODES))

    if unknown_wilayas:
        unknown = ", ".join(str(wilaya) for wilaya in unknown_wilayas)
        raise ValueError(f"Wilaya inconnue dans {column_name}: {unknown}")


def _wilaya_distance_km(sender_wilaya: str, receiver_wilaya: str) -> float:
    if sender_wilaya == receiver_wilaya:
        return 0.0

    override_key = frozenset((sender_wilaya, receiver_wilaya))

    if override_key in WILAYA_DISTANCE_OVERRIDES_KM:
        return WILAYA_DISTANCE_OVERRIDES_KM[override_key]

    return round(
        _haversine_distance_km(
            WILAYA_COORDINATES[sender_wilaya],
            WILAYA_COORDINATES[receiver_wilaya],
        ),
        2,
    )


def add_geographic_features(
    dataframe: pd.DataFrame,
    *,
    sender_wilaya_col: str = "sender_wilaya",
    receiver_wilaya_col: str = "receiver_wilaya",
) -> pd.DataFrame:
    """
    Add geographic ML features based on sender and receiver wilayas.
    """

    required_columns = {sender_wilaya_col, receiver_wilaya_col}
    missing_columns = required_columns - set(dataframe.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Colonnes manquantes pour les features geographiques: {missing}")

    features = dataframe.copy()

    _validate_wilayas(features[sender_wilaya_col], sender_wilaya_col)
    _validate_wilayas(features[receiver_wilaya_col], receiver_wilaya_col)

    features["sender_wilaya_code"] = features[sender_wilaya_col].map(WILAYA_CODES)
    features["receiver_wilaya_code"] = features[receiver_wilaya_col].map(WILAYA_CODES)
    features["is_cross_wilaya"] = (
        features[sender_wilaya_col] != features[receiver_wilaya_col]
    ).astype(int)
    features["wilaya_distance_km"] = [
        _wilaya_distance_km(sender_wilaya, receiver_wilaya)
        for sender_wilaya, receiver_wilaya in zip(
            features[sender_wilaya_col],
            features[receiver_wilaya_col],
        )
    ]

    return features


__all__ = [
    "GEOGRAPHIC_FEATURE_COLUMNS",
    "WILAYA_CODES",
    "WILAYA_COORDINATES",
    "WILAYA_DISTANCE_OVERRIDES_KM",
    "add_geographic_features",
]
