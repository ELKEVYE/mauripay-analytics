# backend/src/mauripay/synthetic/validate.py

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import ValidationError

from mauripay.ingestion.schema import Transaction


# ─────────────────────────────────────────────
# CONSTANTES DE VALIDATION
# ─────────────────────────────────────────────

NOUAKCHOTT_WILAYAS = [
    "Nouakchott-Ouest",
    "Nouakchott-Nord",
    "Nouakchott-Sud",
]

RAMADAN_2026_START = "2026-02-17"
RAMADAN_2026_END = "2026-03-18"

REQUIRED_COLUMNS = [
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


# ─────────────────────────────────────────────
# LECTURE DU DATASET
# ─────────────────────────────────────────────

def load_dataset(input_path: str | Path) -> pd.DataFrame:
    """
    Charge un dataset MauriPay depuis CSV, JSON ou Parquet.

    Formats supportés :
    - .csv
    - .json
    - .parquet
    """

    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path)

    if suffix == ".json":
        return pd.read_json(path)

    if suffix == ".parquet":
        return pd.read_parquet(path)

    raise ValueError(
        "Format non supporté. Utilise un fichier .csv, .json ou .parquet"
    )


# ─────────────────────────────────────────────
# CONTRÔLE DU SCHÉMA
# ─────────────────────────────────────────────

def validate_columns(df: pd.DataFrame) -> dict[str, Any]:
    """
    Vérifie que toutes les colonnes attendues sont présentes.
    """

    existing_columns = list(df.columns)

    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in existing_columns
    ]

    extra_columns = [
        column for column in existing_columns
        if column not in REQUIRED_COLUMNS
    ]

    return {
        "missing_columns": missing_columns,
        "extra_columns": extra_columns,
        "is_valid": len(missing_columns) == 0,
    }


def normalize_value_for_pydantic(value: Any) -> Any:
    """
    Convertit les valeurs vides lues depuis CSV/Parquet en None.

    Pandas transforme souvent les champs optionnels vides en NaN. Le schema
    Pydantic attend None pour bill_provider et origin_country quand ils ne
    sont pas applicables.
    """

    if pd.isna(value):
        return None

    if isinstance(value, str) and value.strip() == "":
        return None

    return value


def row_to_transaction_payload(row: pd.Series) -> dict[str, Any]:
    """
    Prépare une ligne pandas pour Transaction(**payload).
    """

    return {
        column: normalize_value_for_pydantic(row[column])
        for column in REQUIRED_COLUMNS
        if column in row.index
    }


def validate_pydantic_rows(
    df: pd.DataFrame,
    max_errors: int = 5,
) -> dict[str, Any]:
    """
    Revalide chaque ligne avec le schéma Pydantic Transaction.

    Cette étape complète validate_columns(): elle contrôle aussi les enums,
    les montants, les timestamps UTC et les règles métier.
    """

    errors: list[dict[str, Any]] = []
    valid_count = 0
    columns = [column for column in REQUIRED_COLUMNS if column in df.columns]

    for index, values in zip(df.index, df[columns].itertuples(index=False, name=None)):
        payload = {
            column: normalize_value_for_pydantic(value)
            for column, value in zip(columns, values)
        }

        try:
            Transaction.model_validate(payload)
            valid_count += 1
        except ValidationError as exc:
            if len(errors) < max_errors:
                errors.append(
                    {
                        "row": int(index) + 1,
                        "errors": exc.errors(),
                    }
                )

    return {
        "valid_count": valid_count,
        "invalid_count": len(df) - valid_count,
        "sample_errors": errors,
        "is_valid": len(df) == valid_count,
    }


# ─────────────────────────────────────────────
# STATISTIQUES PRINCIPALES
# ─────────────────────────────────────────────

def percent_series(series: pd.Series) -> pd.Series:
    """
    Convertit un comptage en pourcentage.
    """

    total = len(series)

    if total == 0:
        return pd.Series(dtype=float)

    return round(series.value_counts(dropna=False) / total * 100, 2)


def count_series(series: pd.Series) -> pd.Series:
    """
    Retourne le nombre d'occurrences par valeur.
    """

    return series.value_counts(dropna=False)


def compute_channel_stats(df: pd.DataFrame) -> pd.Series:
    """
    Calcule la répartition des canaux :
    USSD / APP / AGENT.
    """

    return percent_series(df["channel"])


def compute_currency_stats(df: pd.DataFrame) -> pd.Series:
    """
    Calcule la repartition des devises.
    """

    return percent_series(df["currency"])


def compute_wilaya_stats(df: pd.DataFrame) -> pd.Series:
    """
    Calcule la répartition par wilaya source.
    """

    return percent_series(df["sender_wilaya"])


def compute_geographic_summary(df: pd.DataFrame) -> dict[str, float]:
    """
    Calcule les pourcentages agrégés :
    - Nouakchott total
    - Dakhlet Nouadhibou
    - autres wilayas
    """

    total = len(df)

    if total == 0:
        return {
            "nouakchott_percent": 0.0,
            "nouadhibou_percent": 0.0,
            "other_wilayas_percent": 0.0,
        }

    nouakchott_count = df["sender_wilaya"].isin(NOUAKCHOTT_WILAYAS).sum()
    nouadhibou_count = (df["sender_wilaya"] == "Dakhlet Nouadhibou").sum()

    nouakchott_percent = round(nouakchott_count / total * 100, 2)
    nouadhibou_percent = round(nouadhibou_count / total * 100, 2)
    other_percent = round(100 - nouakchott_percent - nouadhibou_percent, 2)

    return {
        "nouakchott_percent": nouakchott_percent,
        "nouadhibou_percent": nouadhibou_percent,
        "other_wilayas_percent": other_percent,
    }


def compute_transaction_type_stats(df: pd.DataFrame) -> pd.Series:
    """
    Calcule le nombre de transactions par type.
    """

    return count_series(df["transaction_type"])


def compute_tontine_stats(df: pd.DataFrame) -> dict[str, Any]:
    """
    Detecte les groupes qui ressemblent a une tontine normale.

    Une tontine n'a pas de colonne dediee en M1. On la repere donc par
    signature :
    - TRANSFER normal ;
    - anomaly_type = NONE ;
    - meme receiver_id ;
    - meme amount ;
    - au moins 10 senders differents dans une fenetre de 2 heures.
    """

    if df.empty:
        return {"candidate_group_count": 0, "candidate_transaction_count": 0}

    working_df = df.copy()
    working_df["timestamp"] = pd.to_datetime(
        working_df["timestamp"],
        utc=True,
        errors="coerce",
    )

    normal_mask = (
        (working_df["transaction_type"] == "TRANSFER")
        & (working_df["anomaly_type"] == "NONE")
        & (working_df["is_anomaly"].astype(str).str.lower().isin(["false", "0"]))
    )

    working_df = (
        working_df.loc[normal_mask, ["receiver_id", "amount", "timestamp", "sender_id"]]
        .dropna(subset=["timestamp"])
        .sort_values(["receiver_id", "amount", "timestamp"])
    )

    candidate_group_count = 0
    candidate_transaction_count = 0

    for _, group in working_df.groupby(["receiver_id", "amount"], sort=False, dropna=False):
        if len(group) < 10:
            continue

        timestamps = group["timestamp"].tolist()
        sender_ids = group["sender_id"].tolist()
        sender_counts: dict[str, int] = defaultdict(int)
        start_index = 0
        end_index = 0
        group_size = len(group)

        while start_index < group_size:
            window_end = timestamps[start_index] + pd.Timedelta(hours=2)

            while end_index < group_size and timestamps[end_index] <= window_end:
                sender_counts[sender_ids[end_index]] += 1
                end_index += 1

            if len(sender_counts) >= 10:
                candidate_group_count += 1
                candidate_transaction_count += end_index - start_index
                start_index = end_index
                sender_counts.clear()
            else:
                sender_id = sender_ids[start_index]
                sender_counts[sender_id] -= 1
                if sender_counts[sender_id] == 0:
                    del sender_counts[sender_id]
                start_index += 1

    return {
        "candidate_group_count": candidate_group_count,
        "candidate_transaction_count": candidate_transaction_count,
    }


def compute_anomaly_stats(df: pd.DataFrame) -> dict[str, Any]:
    """
    Calcule :
    - le nombre total d'anomalies ;
    - le pourcentage d'anomalies ;
    - le nombre par anomaly_type.
    """

    total = len(df)

    if total == 0:
        return {
            "anomaly_count": 0,
            "anomaly_percent": 0.0,
            "anomaly_type_counts": pd.Series(dtype=int),
        }

    # is_anomaly peut être bool ou texte selon CSV/JSON.
    is_anomaly = df["is_anomaly"].astype(str).str.lower().isin(["true", "1"])

    anomaly_count = int(is_anomaly.sum())
    anomaly_percent = round(anomaly_count / total * 100, 2)

    anomaly_type_counts = count_series(df["anomaly_type"])

    return {
        "anomaly_count": anomaly_count,
        "anomaly_percent": anomaly_percent,
        "anomaly_type_counts": anomaly_type_counts,
    }


def compute_daily_volume(df: pd.DataFrame) -> pd.Series:
    """
    Calcule le nombre de transactions par jour.
    """

    timestamps = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    daily_volume = timestamps.dt.date.value_counts().sort_index()

    return daily_volume


def compute_ramadan_stats(df: pd.DataFrame) -> dict[str, Any]:
    """
    Vérifie le volume pendant Ramadan 2026.

    On compare :
    - volume moyen journalier pendant Ramadan ;
    - volume moyen journalier hors Ramadan.
    """

    working_df = df.copy()
    working_df["timestamp"] = pd.to_datetime(
        working_df["timestamp"],
        utc=True,
        errors="coerce",
    )

    working_df = working_df.dropna(subset=["timestamp"])

    if working_df.empty:
        return {
            "ramadan_transactions": 0,
            "non_ramadan_transactions": 0,
            "ramadan_daily_avg": 0.0,
            "non_ramadan_daily_avg": 0.0,
            "ramadan_multiplier": 0.0,
        }

    start = pd.Timestamp(RAMADAN_2026_START, tz="UTC")
    end = pd.Timestamp(RAMADAN_2026_END, tz="UTC") + pd.Timedelta(days=1)

    ramadan_mask = (
        (working_df["timestamp"] >= start)
        & (working_df["timestamp"] < end)
    )

    ramadan_df = working_df[ramadan_mask]
    non_ramadan_df = working_df[~ramadan_mask]

    ramadan_days = max(
        1,
        ramadan_df["timestamp"].dt.date.nunique(),
    )

    non_ramadan_days = max(
        1,
        non_ramadan_df["timestamp"].dt.date.nunique(),
    )

    ramadan_daily_avg = round(len(ramadan_df) / ramadan_days, 2)
    non_ramadan_daily_avg = round(len(non_ramadan_df) / non_ramadan_days, 2)

    if non_ramadan_daily_avg == 0:
        multiplier = 0.0
    else:
        multiplier = round(ramadan_daily_avg / non_ramadan_daily_avg, 2)

    return {
        "ramadan_transactions": len(ramadan_df),
        "non_ramadan_transactions": len(non_ramadan_df),
        "ramadan_daily_avg": ramadan_daily_avg,
        "non_ramadan_daily_avg": non_ramadan_daily_avg,
        "ramadan_multiplier": multiplier,
    }


def compute_salary_day_stats(df: pd.DataFrame) -> dict[str, Any]:
    """
    Vérifie le pic des jours 1 à 5 du mois.

    On compare :
    - volume moyen journalier les jours 1-5 ;
    - volume moyen journalier les autres jours.
    """

    working_df = df.copy()
    working_df["timestamp"] = pd.to_datetime(
        working_df["timestamp"],
        utc=True,
        errors="coerce",
    )

    working_df = working_df.dropna(subset=["timestamp"])

    if working_df.empty:
        return {
            "salary_period_transactions": 0,
            "other_days_transactions": 0,
            "salary_daily_avg": 0.0,
            "other_daily_avg": 0.0,
            "salary_multiplier": 0.0,
        }

    salary_mask = working_df["timestamp"].dt.day.isin([1, 2, 3, 4, 5])

    salary_df = working_df[salary_mask]
    other_df = working_df[~salary_mask]

    salary_days = max(1, salary_df["timestamp"].dt.date.nunique())
    other_days = max(1, other_df["timestamp"].dt.date.nunique())

    salary_daily_avg = round(len(salary_df) / salary_days, 2)
    other_daily_avg = round(len(other_df) / other_days, 2)

    if other_daily_avg == 0:
        multiplier = 0.0
    else:
        multiplier = round(salary_daily_avg / other_daily_avg, 2)

    return {
        "salary_period_transactions": len(salary_df),
        "other_days_transactions": len(other_df),
        "salary_daily_avg": salary_daily_avg,
        "other_daily_avg": other_daily_avg,
        "salary_multiplier": multiplier,
    }


# ─────────────────────────────────────────────
# AFFICHAGE DU RAPPORT
# ─────────────────────────────────────────────

def print_series(title: str, series: pd.Series, max_rows: int | None = None) -> None:
    """
    Affiche proprement une série pandas.
    """

    print(f"\n{title}")
    print("-" * len(title))

    if series.empty:
        print("Aucune donnée")
        return

    if max_rows is not None:
        series = series.head(max_rows)

    for index, value in series.items():
        print(f"- {index}: {value}")


def print_validation_report(df: pd.DataFrame, input_path: str | Path) -> None:
    """
    Affiche le rapport complet de validation.
    """

    print("\nRapport de validation MauriPay")
    print("==============================")
    print(f"Fichier : {input_path}")
    print(f"Nombre total de transactions : {len(df)}")

    # Validation des colonnes
    column_report = validate_columns(df)

    print("\nSchéma")
    print("------")
    if column_report["is_valid"]:
        print("OK Toutes les colonnes obligatoires sont presentes")
    else:
        print("ERREUR Colonnes manquantes :")
        for column in column_report["missing_columns"]:
            print(f"  - {column}")

    if column_report["extra_columns"]:
        print("Colonnes supplémentaires :")
        for column in column_report["extra_columns"]:
            print(f"  - {column}")

    pydantic_report = validate_pydantic_rows(df)

    if pydantic_report["is_valid"]:
        print("OK Toutes les lignes respectent schema.py")
    else:
        print(
            "ERREUR Lignes invalides selon schema.py : "
            f"{pydantic_report['invalid_count']}"
        )
        for item in pydantic_report["sample_errors"]:
            print(f"  - ligne {item['row']}: {item['errors']}")

    # Canaux
    channel_stats = compute_channel_stats(df)
    print_series("Répartition des canaux (%)", channel_stats)

    # Devises
    currency_stats = compute_currency_stats(df)
    print_series("Repartition des devises (%)", currency_stats)

    # Géographie
    geo_summary = compute_geographic_summary(df)

    print("\nRésumé géographique")
    print("-------------------")
    print(f"- Nouakchott total: {geo_summary['nouakchott_percent']}%")
    print(f"- Dakhlet Nouadhibou: {geo_summary['nouadhibou_percent']}%")
    print(f"- Autres wilayas: {geo_summary['other_wilayas_percent']}%")

    wilaya_stats = compute_wilaya_stats(df)
    print_series("Top wilayas source (%)", wilaya_stats, max_rows=10)

    # Types de transaction
    tx_type_stats = compute_transaction_type_stats(df)
    print_series("Nombre par transaction_type", tx_type_stats)

    # Tontines normales probables
    tontine_stats = compute_tontine_stats(df)

    print("\nTontines normales probables")
    print("---------------------------")
    print(f"- Groupes detectes: {tontine_stats['candidate_group_count']}")
    print(f"- Transactions concernees: {tontine_stats['candidate_transaction_count']}")

    # Anomalies
    anomaly_stats = compute_anomaly_stats(df)

    print("\nAnomalies")
    print("---------")
    print(f"- Nombre anomalies: {anomaly_stats['anomaly_count']}")
    print(f"- Pourcentage anomalies: {anomaly_stats['anomaly_percent']}%")

    print_series(
        "Nombre par anomaly_type",
        anomaly_stats["anomaly_type_counts"],
    )

    # Volume journalier
    daily_volume = compute_daily_volume(df)

    print("\nVolume journalier")
    print("-----------------")
    if daily_volume.empty:
        print("Aucune date valide")
    else:
        print(f"- Nombre de jours couverts: {len(daily_volume)}")
        print(f"- Volume journalier moyen: {round(daily_volume.mean(), 2)}")
        print(f"- Volume journalier min: {int(daily_volume.min())}")
        print(f"- Volume journalier max: {int(daily_volume.max())}")

    # Ramadan
    ramadan_stats = compute_ramadan_stats(df)

    print("\nPic Ramadan")
    print("-----------")
    print(f"- Transactions Ramadan: {ramadan_stats['ramadan_transactions']}")
    print(f"- Transactions hors Ramadan: {ramadan_stats['non_ramadan_transactions']}")
    print(f"- Moyenne/jour Ramadan: {ramadan_stats['ramadan_daily_avg']}")
    print(f"- Moyenne/jour hors Ramadan: {ramadan_stats['non_ramadan_daily_avg']}")
    print(f"- Multiplicateur Ramadan: x{ramadan_stats['ramadan_multiplier']}")

    # Salaire
    salary_stats = compute_salary_day_stats(df)

    print("\nPic salarial jours 1 à 5")
    print("------------------------")
    print(f"- Transactions jours 1-5: {salary_stats['salary_period_transactions']}")
    print(f"- Transactions autres jours: {salary_stats['other_days_transactions']}")
    print(f"- Moyenne/jour jours 1-5: {salary_stats['salary_daily_avg']}")
    print(f"- Moyenne/jour autres jours: {salary_stats['other_daily_avg']}")
    print(f"- Multiplicateur salarial: x{salary_stats['salary_multiplier']}")


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def build_arg_parser() -> argparse.ArgumentParser:
    """
    Crée le parser CLI du script de validation.
    """

    parser = argparse.ArgumentParser(
        description="Validation statistique d'un dataset MauriPay"
    )

    parser.add_argument(
        "input",
        type=str,
        help="Chemin du dataset à valider : .csv, .json ou .parquet",
    )

    return parser


def main() -> None:
    """
    Point d'entrée principal.
    """

    parser = build_arg_parser()
    args = parser.parse_args()

    dataframe = load_dataset(args.input)
    print_validation_report(dataframe, args.input)


if __name__ == "__main__":
    main()
