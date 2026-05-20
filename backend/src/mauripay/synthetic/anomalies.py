# backend/src/mauripay/synthetic/anomalies.py

from __future__ import annotations

import random
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


MAX_AMOUNT = Decimal("10000000.00")


def money(value: Decimal) -> Decimal:
    """
    Arrondit un montant financier à deux décimales.
    """
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def mark_as_normal(transaction_data: dict[str, Any]) -> dict[str, Any]:
    """
    Marque une transaction comme normale.

    Utilisé en S3 et aussi comme valeur par défaut en S4.
    """
    transaction_data["is_anomaly"] = False
    transaction_data["anomaly_type"] = "NONE"
    return transaction_data


def inject_high_amount(transaction_data: dict[str, Any]) -> dict[str, Any]:
    """
    Injecte une anomalie HIGH_AMOUNT.

    Principe :
    - on prend un montant normal ;
    - on le multiplie par 10 à 30 ;
    - on limite le résultat à 10000000 MRU pour rester compatible avec schema.py ;
    - on marque la transaction comme anomalie.

    Exemple :
    amount = 12000 → 120000 ou plus
    """
    tx = deepcopy(transaction_data)

    amount = Decimal(str(tx["amount"]))
    multiplier = Decimal(str(random.choice([10, 15, 20, 25, 30])))

    anomalous_amount = money(amount * multiplier)

    if anomalous_amount > MAX_AMOUNT:
        anomalous_amount = MAX_AMOUNT

    tx["amount"] = anomalous_amount
    tx["fees"] = money(anomalous_amount * Decimal("0.01"))

    tx["is_anomaly"] = True
    tx["anomaly_type"] = "HIGH_AMOUNT"

    return tx


def inject_operator_outage(
    transaction_data: dict[str, Any],
    outage_operator: str | None = None,
) -> dict[str, Any]:
    """
    Injecte une anomalie OPERATOR_OUTAGE.

    Principe :
    - une transaction devient FAILED ;
    - les frais deviennent 0 ;
    - l'anomalie est liée à une panne opérateur.

    Si outage_operator est donné, on force l'opérateur à cette valeur.
    """
    tx = deepcopy(transaction_data)

    if outage_operator is not None:
        tx["operator"] = outage_operator

    tx["status"] = "FAILED"
    tx["fees"] = Decimal("0.00")

    tx["is_anomaly"] = True
    tx["anomaly_type"] = "OPERATOR_OUTAGE"

    return tx


def inject_unusual_location(
    transaction_data: dict[str, Any],
    unusual_wilayas: list[str] | None = None,
) -> dict[str, Any]:
    """
    Injecte une anomalie UNUSUAL_LOCATION.

    Principe :
    - on garde le sender ;
    - on change la wilaya du receiver vers une wilaya éloignée ou inhabituelle ;
    - on marque la transaction comme anomalie géographique.
    """
    tx = deepcopy(transaction_data)

    if unusual_wilayas is None:
        unusual_wilayas = [
            "Tiris Zemmour",
            "Inchiri",
            "Dakhlet Nouadhibou",
            "Guidimakha",
        ]

    sender_wilaya = tx["sender_wilaya"]

    possible_wilayas = [
        wilaya for wilaya in unusual_wilayas
        if wilaya != sender_wilaya
    ]

    if possible_wilayas:
        tx["receiver_wilaya"] = random.choice(possible_wilayas)

    tx["is_anomaly"] = True
    tx["anomaly_type"] = "UNUSUAL_LOCATION"

    return tx


def create_structuring_sequence(
    base_transaction_data: dict[str, Any],
    count: int | None = None,
    max_timestamp: datetime | None = None,
) -> list[dict[str, Any]]:
    """
    Crée une séquence STRUCTURING.

    Principe :
    - même sender ;
    - même receiver ou receivers proches ;
    - plusieurs transactions rapprochées ;
    - montants similaires ;
    - courte période de temps.

    Exemple :
    au lieu d'une seule transaction de 200000 MRU,
    le générateur crée 5 transactions de 40000 MRU.
    """
    base_tx = deepcopy(base_transaction_data)

    if count is None:
        count = random.randint(4, 8)

    timestamp = base_tx["timestamp"]

    total_amount = Decimal(str(base_tx["amount"]))

    # On force un total assez élevé pour que le structuring ait du sens.
    if total_amount < Decimal("100000.00"):
        total_amount = Decimal(str(random.randint(100000, 300000)))

    split_amount = money(total_amount / Decimal(count))

    sequence: list[dict[str, Any]] = []

    for index in range(count):
        tx = deepcopy(base_tx)

        # Transactions espacées de quelques minutes.
        tx["timestamp"] = timestamp + timedelta(minutes=random.randint(2, 15) * index)
        if max_timestamp is not None and tx["timestamp"] > max_timestamp:
            tx["timestamp"] = max_timestamp

        # Montants similaires mais pas toujours identiques.
        variation = Decimal(str(random.uniform(0.95, 1.05)))
        tx["amount"] = money(split_amount * variation)

        tx["fees"] = money(tx["amount"] * Decimal("0.01"))

        tx["transaction_type"] = "TRANSFER"
        tx["status"] = "SUCCESS"
        tx["bill_provider"] = None
        tx["origin_country"] = None

        tx["is_anomaly"] = True
        tx["anomaly_type"] = "STRUCTURING"

        sequence.append(tx)

    return sequence


def create_high_frequency_sequence(
    base_transaction_data: dict[str, Any],
    count: int | None = None,
    max_timestamp: datetime | None = None,
) -> list[dict[str, Any]]:
    """
    Crée une séquence HIGH_FREQUENCY.

    Principe :
    - même sender ;
    - beaucoup de transactions ;
    - très courte période ;
    - montants petits ou moyens.
    """
    base_tx = deepcopy(base_transaction_data)

    if count is None:
        count = random.randint(10, 30)

    timestamp = base_tx["timestamp"]

    sequence: list[dict[str, Any]] = []

    for index in range(count):
        tx = deepcopy(base_tx)

        tx["timestamp"] = timestamp + timedelta(seconds=random.randint(20, 120) * index)
        if max_timestamp is not None and tx["timestamp"] > max_timestamp:
            tx["timestamp"] = max_timestamp
        tx["amount"] = money(Decimal(str(random.uniform(100, 5000))))
        tx["fees"] = money(tx["amount"] * Decimal("0.01"))

        tx["transaction_type"] = random.choice(["TRANSFER", "AIRTIME", "MERCHANT"])
        tx["status"] = "SUCCESS"
        tx["bill_provider"] = None
        tx["origin_country"] = None

        tx["is_anomaly"] = True
        tx["anomaly_type"] = "HIGH_FREQUENCY"

        sequence.append(tx)

    return sequence


def inject_single_anomaly(
    transaction_data: dict[str, Any],
    anomaly_type: str | None = None,
) -> dict[str, Any]:
    """
    Injecte une anomalie simple sur une seule transaction.

    Anomalies simples :
    - HIGH_AMOUNT
    - OPERATOR_OUTAGE
    - UNUSUAL_LOCATION

    Les anomalies STRUCTURING et HIGH_FREQUENCY sont des séquences,
    donc elles sont générées par des fonctions séparées.
    """
    if anomaly_type is None:
        anomaly_type = random.choices(
            ["HIGH_AMOUNT", "OPERATOR_OUTAGE", "UNUSUAL_LOCATION"],
            weights=[0.50, 0.30, 0.20],
            k=1,
        )[0]

    if anomaly_type == "HIGH_AMOUNT":
        return inject_high_amount(transaction_data)

    if anomaly_type == "OPERATOR_OUTAGE":
        return inject_operator_outage(transaction_data)

    if anomaly_type == "UNUSUAL_LOCATION":
        return inject_unusual_location(transaction_data)

    raise ValueError(
        f"Anomaly type non supporté pour une transaction simple : {anomaly_type}"
    )


def maybe_inject_anomaly(
    transaction_data: dict[str, Any],
    anomaly_rate: float = 0.02,
) -> dict[str, Any]:
    """
    Injecte parfois une anomalie simple.

    Exemple :
    anomaly_rate = 0.02 signifie environ 2 % d'anomalies.

    Cette fonction ne génère pas les séquences STRUCTURING ou HIGH_FREQUENCY.
    Elle sert seulement pour les anomalies simples.
    """
    if anomaly_rate < 0 or anomaly_rate > 1:
        raise ValueError("anomaly_rate doit être entre 0 et 1")

    if random.random() < anomaly_rate:
        return inject_single_anomaly(transaction_data)

    return mark_as_normal(transaction_data)
