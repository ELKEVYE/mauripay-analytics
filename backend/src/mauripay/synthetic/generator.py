# backend/src/mauripay/synthetic/generator.py

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from mauripay.ingestion.schema import Transaction
from mauripay.synthetic.anomalies import (
    create_high_frequency_sequence,
    create_structuring_sequence,
    maybe_inject_anomaly,
)
from mauripay.synthetic.config import (
    ACCOUNT_ID_FORMAT,
    DEFAULT_ANOMALY_RATE,
    DEFAULT_END_DATE,
    DEFAULT_NUM_ACCOUNTS,
    DEFAULT_RANDOM_SEED,
    DEFAULT_START_DATE,
    DEFAULT_TONTINE_RATE,
    CURRENCIES,
    CURRENCY_WEIGHTS,
)
from mauripay.synthetic.exporters import export_transactions
from mauripay.synthetic.patterns import (
    choose_amount,
    choose_bill_provider,
    choose_channel,
    choose_diaspora_origin,
    choose_operator,
    choose_patterned_timestamp,
    choose_transaction_type,
    choose_wilaya,
    compute_fees,
    is_ramadan_period,
    should_be_diaspora_cash_in,
)
# ─────────────────────────────────────────────
# MODÈLE INTERNE D'UN COMPTE
# ─────────────────────────────────────────────

@dataclass(frozen=True)
class Account:
    """
    Compte utilisateur fictif.

    Ce modèle n'est pas exporté dans le dataset final.
    Il sert seulement au générateur pour créer des transactions réalistes.
    """

    account_id: str
    wilaya: str
    operator: str
    preferred_channel: str
    activity_level: str


# ─────────────────────────────────────────────
# OUTILS TEMPORELS
# ─────────────────────────────────────────────

def choose_currency() -> str:
    return random.choices(
        CURRENCIES,
        weights=[CURRENCY_WEIGHTS[currency] for currency in CURRENCIES],
        k=1,
    )[0]


def parse_utc_datetime(date_text: str, end_of_day: bool = False) -> datetime:
    """
    Convertit une date YYYY-MM-DD en datetime UTC.

    Exemple :
    "2026-01-01" devient 2026-01-01T00:00:00+00:00

    Si end_of_day=True :
    "2026-12-31" devient 2026-12-31T23:59:59+00:00
    """

    base = datetime.fromisoformat(date_text)

    if end_of_day:
        base = base.replace(hour=23, minute=59, second=59, microsecond=0)
    else:
        base = base.replace(hour=0, minute=0, second=0, microsecond=0)

    return base.replace(tzinfo=timezone.utc)


# ─────────────────────────────────────────────
# CRÉATION DES COMPTES
# ─────────────────────────────────────────────

def create_accounts(num_accounts: int = DEFAULT_NUM_ACCOUNTS) -> list[Account]:
    """
    Crée des comptes fictifs compatibles avec schema.py.

    Le format conservé est :
    ACC_00001
    ACC_00002
    ACC_00003

    Ce format respecte :
    pattern=r"^ACC_\\d{5}$"
    """

    if num_accounts <= 1:
        raise ValueError("num_accounts doit être supérieur à 1")

    if num_accounts > 99_999:
        raise ValueError(
            "Avec le format ACC_\\d{5}, num_accounts ne peut pas dépasser 99 999"
        )

    accounts: list[Account] = []

    for index in range(1, num_accounts + 1):
        wilaya = choose_wilaya()
        operator = choose_operator()
        preferred_channel = choose_channel(wilaya)

        activity_level = random.choices(
            ["LOW", "MEDIUM", "HIGH"],
            weights=[0.60, 0.30, 0.10],
            k=1,
        )[0]

        account = Account(
            account_id=ACCOUNT_ID_FORMAT.format(index),
            wilaya=wilaya,
            operator=operator,
            preferred_channel=preferred_channel,
            activity_level=activity_level,
        )

        accounts.append(account)

    return accounts


def choose_two_accounts(accounts: list[Account]) -> tuple[Account, Account]:
    """
    Choisit deux comptes différents.

    On utilise random.sample pour garantir :
    sender_id != receiver_id
    """

    sender, receiver = random.sample(accounts, k=2)
    return sender, receiver


# ─────────────────────────────────────────────
# CONSTRUCTION D'UNE TRANSACTION DE BASE
# ─────────────────────────────────────────────

def build_base_transaction_data(
    accounts: list[Account],
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    """
    Construit une transaction normale avant injection d'anomalie.

    Cette fonction ne décide pas encore si la transaction est normale
    ou anormale. Elle construit seulement les champs de base :
    timestamp, sender, receiver, amount, type, channel, operator, etc.
    """

    timestamp = choose_patterned_timestamp(start, end)

    sender, receiver = choose_two_accounts(accounts)

    transaction_type = choose_transaction_type(timestamp)

    bill_provider = None
    if transaction_type == "BILL_PAY":
        bill_provider = choose_bill_provider()

    diaspora = should_be_diaspora_cash_in(transaction_type, timestamp)
    origin_country = choose_diaspora_origin() if diaspora else None

    amount = choose_amount(
        transaction_type=transaction_type,
        bill_provider=bill_provider,
        diaspora=diaspora,
    )

    fees = compute_fees(amount, transaction_type)

    # Le canal est souvent lié à la wilaya de l'expéditeur.
    # 70 % du temps, on garde le canal préféré du compte.
    # 30 % du temps, on choisit un autre canal selon la wilaya.
    if random.random() < 0.70:
        channel = sender.preferred_channel
    else:
        channel = choose_channel(sender.wilaya)

    transaction_data: dict[str, Any] = {
        "timestamp": timestamp,
        "sender_id": sender.account_id,
        "receiver_id": receiver.account_id,
        "amount": amount,
        "currency": choose_currency(),
        "transaction_type": transaction_type,
        "channel": channel,
        "operator": sender.operator,
        "sender_wilaya": sender.wilaya,
        "receiver_wilaya": receiver.wilaya,
        "status": "SUCCESS",
        "fees": fees,
        "is_ramadan": is_ramadan_period(timestamp),
        "bill_provider": bill_provider,
        "origin_country": origin_country,
    }

    return transaction_data


def build_transaction_data(
    accounts: list[Account],
    start: datetime,
    end: datetime,
    anomaly_rate: float = DEFAULT_ANOMALY_RATE,
) -> dict[str, Any]:
    """
    Construit une transaction puis injecte parfois une anomalie simple.

    Les anomalies simples sont :
    - HIGH_AMOUNT
    - OPERATOR_OUTAGE
    - UNUSUAL_LOCATION

    Les anomalies en séquence comme STRUCTURING et HIGH_FREQUENCY
    sont gérées dans generate_transactions().
    """

    transaction_data = build_base_transaction_data(
        accounts=accounts,
        start=start,
        end=end,
    )

    transaction_data = maybe_inject_anomaly(
        transaction_data,
        anomaly_rate=anomaly_rate,
    )

    return transaction_data


def validate_transaction(transaction_data: dict[str, Any]) -> Transaction:
    """
    Valide une transaction avec Pydantic.

    Si la transaction ne respecte pas schema.py,
    Pydantic lève une erreur.
    """

    return Transaction(**transaction_data)


def generate_transaction(
    accounts: list[Account],
    start: datetime,
    end: datetime,
    anomaly_rate: float = DEFAULT_ANOMALY_RATE,
) -> Transaction:
    """
    Génère une seule transaction.

    Étapes :
    1. construire une transaction de base ;
    2. injecter parfois une anomalie simple ;
    3. valider avec Pydantic.
    """

    transaction_data = build_transaction_data(
        accounts=accounts,
        start=start,
        end=end,
        anomaly_rate=anomaly_rate,
    )

    return validate_transaction(transaction_data)


# ─────────────────────────────────────────────
# GÉNÉRATION DES SÉQUENCES D'ANOMALIES
# ─────────────────────────────────────────────

def generate_structuring_transactions(
    accounts: list[Account],
    start: datetime,
    end: datetime,
) -> list[Transaction]:
    """
    Génère une séquence STRUCTURING.

    STRUCTURING signifie :
    - même sender ;
    - plusieurs transactions rapprochées ;
    - montants similaires ;
    - courte période.

    Exemple :
    au lieu d'une transaction de 300000 MRU,
    le générateur crée 5 ou 6 transactions de 50000 MRU.
    """

    base_data = build_base_transaction_data(
        accounts=accounts,
        start=start,
        end=end,
    )

    sequence_data = create_structuring_sequence(base_data, max_timestamp=end)

    return [
        validate_transaction(transaction_data)
        for transaction_data in sequence_data
    ]


def generate_high_frequency_transactions(
    accounts: list[Account],
    start: datetime,
    end: datetime,
) -> list[Transaction]:
    """
    Génère une séquence HIGH_FREQUENCY.

    HIGH_FREQUENCY signifie :
    - même sender ;
    - beaucoup de transactions ;
    - très courte période ;
    - montants petits ou moyens.

    Ce type d'anomalie peut représenter :
    - un bot ;
    - un compte piraté ;
    - une activité automatisée.
    """

    base_data = build_base_transaction_data(
        accounts=accounts,
        start=start,
        end=end,
    )

    sequence_data = create_high_frequency_sequence(base_data, max_timestamp=end)

    return [
        validate_transaction(transaction_data)
        for transaction_data in sequence_data
    ]


# ─────────────────────────────────────────────
# GENERATION DES TONTINES NORMALES
# ─────────────────────────────────────────────

def generate_tontine_transactions(
    accounts: list[Account],
    start: datetime,
    end: datetime,
) -> list[Transaction]:
    """
    Genere une sequence de tontine El Lewha comme comportement normal.

    Signature dans les donnees :
    - 10 a 30 comptes emetteurs ;
    - meme beneficiaire ;
    - meme montant ;
    - fenetre temporelle courte de deux heures ;
    - is_anomaly=False et anomaly_type=NONE.
    """

    if len(accounts) < 3:
        raise ValueError("Il faut au moins 3 comptes pour une tontine")

    beneficiary = random.choice(accounts)
    possible_senders = [
        account for account in accounts
        if account.account_id != beneficiary.account_id
    ]

    group_size = min(
        len(possible_senders),
        random.randint(10, 30),
    )
    senders = random.sample(possible_senders, k=group_size)

    amount = random.choice(
        [
            Decimal("500.00"),
            Decimal("1000.00"),
            Decimal("2000.00"),
            Decimal("5000.00"),
        ]
    )

    latest_start = end - timedelta(hours=2)
    if latest_start > start:
        base_timestamp = choose_patterned_timestamp(start, latest_start)
    else:
        base_timestamp = choose_patterned_timestamp(start, end)

    offsets = sorted(random.randint(0, 120) for _ in senders)

    sequence: list[Transaction] = []
    for sender, offset_minutes in zip(senders, offsets):
        timestamp = min(
            base_timestamp + timedelta(minutes=offset_minutes),
            end,
        )

        transaction_data: dict[str, Any] = {
            "timestamp": timestamp,
            "sender_id": sender.account_id,
            "receiver_id": beneficiary.account_id,
            "amount": amount,
            "currency": choose_currency(),
            "transaction_type": "TRANSFER",
            "channel": sender.preferred_channel,
            "operator": sender.operator,
            "sender_wilaya": sender.wilaya,
            "receiver_wilaya": beneficiary.wilaya,
            "status": "SUCCESS",
            "fees": compute_fees(amount, "TRANSFER"),
            "is_ramadan": is_ramadan_period(timestamp),
            "bill_provider": None,
            "origin_country": None,
            "is_anomaly": False,
            "anomaly_type": "NONE",
        }

        sequence.append(validate_transaction(transaction_data))

    return sequence


# GENERATION PRINCIPALE

def generate_transactions(
    rows: int,
    num_accounts: int = DEFAULT_NUM_ACCOUNTS,
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    seed: int | None = DEFAULT_RANDOM_SEED,
    anomaly_rate: float = DEFAULT_ANOMALY_RATE,
    tontine_rate: float = DEFAULT_TONTINE_RATE,
    structuring_rate: float = 0.003,
    high_frequency_rate: float = 0.002,
) -> list[Transaction]:
    """
    Génère un dataset complet.

    Paramètres :
    - rows : nombre total de transactions souhaité
    - anomaly_rate : taux d'anomalies simples
    - tontine_rate : probabilite de creer une sequence normale de tontine
    - structuring_rate : probabilité de créer une séquence STRUCTURING
    - high_frequency_rate : probabilité de créer une séquence HIGH_FREQUENCY

    Important :
    STRUCTURING et HIGH_FREQUENCY créent plusieurs transactions.
    Donc la boucle continue jusqu'à atteindre rows,
    puis on coupe la liste à rows exactement.
    """

    if rows <= 0:
        raise ValueError("rows doit être supérieur à 0")

    if not 0 <= anomaly_rate <= 1:
        raise ValueError("anomaly_rate doit être entre 0 et 1")

    if not 0 <= tontine_rate <= 1:
        raise ValueError("tontine_rate doit être entre 0 et 1")

    if not 0 <= structuring_rate <= 1:
        raise ValueError("structuring_rate doit être entre 0 et 1")

    if not 0 <= high_frequency_rate <= 1:
        raise ValueError("high_frequency_rate doit être entre 0 et 1")

    if tontine_rate + structuring_rate + high_frequency_rate > 1:
        raise ValueError(
            "La somme tontine_rate + structuring_rate + "
            "high_frequency_rate doit être <= 1"
        )

    if seed is not None:
        random.seed(seed)

    start = parse_utc_datetime(start_date, end_of_day=False)
    end = parse_utc_datetime(end_date, end_of_day=True)
    now = datetime.now(timezone.utc)

    if end > now:
        end = now

    if start >= end:
        raise ValueError("start_date doit être avant end_date")

    accounts = create_accounts(num_accounts=num_accounts)

    transactions: list[Transaction] = []

    while len(transactions) < rows:
        random_value = random.random()

        # Cas 1 : sequence normale de tontine.
        # Ce comportement culturel n'est pas marque comme anomalie.
        if random_value < tontine_rate:
            sequence = generate_tontine_transactions(
                accounts=accounts,
                start=start,
                end=end,
            )
            transactions.extend(sequence)

        # Cas 2 : sequence STRUCTURING.
        elif random_value < tontine_rate + structuring_rate:
            sequence = generate_structuring_transactions(
                accounts=accounts,
                start=start,
                end=end,
            )
            transactions.extend(sequence)

        # Cas 3 : sequence HIGH_FREQUENCY.
        # Cette anomalie ajoute aussi plusieurs transactions.
        elif random_value < (
            tontine_rate + structuring_rate + high_frequency_rate
        ):
            sequence = generate_high_frequency_transactions(
                accounts=accounts,
                start=start,
                end=end,
            )
            transactions.extend(sequence)

        # Cas 4 : transaction normale ou anomalie simple.
        else:
            transaction = generate_transaction(
                accounts=accounts,
                start=start,
                end=end,
                anomaly_rate=anomaly_rate,
            )
            transactions.append(transaction)

    # On garantit exactement le nombre demandé.
    return transactions[:rows]


# ─────────────────────────────────────────────
# STATISTIQUES DE VALIDATION
# ─────────────────────────────────────────────

def compute_basic_stats(transactions: list[Transaction]) -> dict[str, Any]:
    """
    Calcule des statistiques simples pour vérifier le dataset.

    Statistiques affichées :
    - répartition des canaux ;
    - répartition des types de transaction ;
    - part de Nouakchott ;
    - part de Nouadhibou ;
    - pourcentage d'anomalies ;
    - nombre par type d'anomalie.
    """

    total = len(transactions)

    if total == 0:
        return {}

    channel_counts: dict[str, int] = {}
    currency_counts: dict[str, int] = {}
    wilaya_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    anomaly_type_counts: dict[str, int] = {}

    anomaly_count = 0
    nouakchott_count = 0
    nouadhibou_count = 0

    for tx in transactions:
        data = tx.model_dump(mode="json")

        channel = data["channel"]
        currency = data["currency"]
        sender_wilaya = data["sender_wilaya"]
        tx_type = data["transaction_type"]
        is_anomaly = data["is_anomaly"]
        anomaly_type = data["anomaly_type"]

        channel_counts[channel] = channel_counts.get(channel, 0) + 1
        currency_counts[currency] = currency_counts.get(currency, 0) + 1
        wilaya_counts[sender_wilaya] = wilaya_counts.get(sender_wilaya, 0) + 1
        type_counts[tx_type] = type_counts.get(tx_type, 0) + 1

        if is_anomaly:
            anomaly_count += 1

        anomaly_type_counts[anomaly_type] = (
            anomaly_type_counts.get(anomaly_type, 0) + 1
        )

        if sender_wilaya.startswith("Nouakchott"):
            nouakchott_count += 1

        if sender_wilaya == "Dakhlet Nouadhibou":
            nouadhibou_count += 1

    return {
        "rows": total,
        "channels_percent": {
            key: round(value / total * 100, 2)
            for key, value in sorted(channel_counts.items())
        },
        "currencies_percent": {
            key: round(value / total * 100, 2)
            for key, value in sorted(currency_counts.items())
        },
        "transaction_types_percent": {
            key: round(value / total * 100, 2)
            for key, value in sorted(type_counts.items())
        },
        "nouakchott_percent": round(nouakchott_count / total * 100, 2),
        "nouadhibou_percent": round(nouadhibou_count / total * 100, 2),
        "top_sender_wilayas_percent": {
            key: round(value / total * 100, 2)
            for key, value in sorted(
                wilaya_counts.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:8]
        },
        "anomaly_percent": round(anomaly_count / total * 100, 2),
        "anomaly_types_count": dict(sorted(anomaly_type_counts.items())),
    }


def print_stats(stats: dict[str, Any]) -> None:
    """
    Affiche les statistiques principales dans le terminal.
    """

    print("\nStatistiques de validation")
    print("--------------------------")
    print(f"Nombre de transactions : {stats.get('rows')}")

    print("\nCanaux :")
    for key, value in stats.get("channels_percent", {}).items():
        print(f"  - {key}: {value}%")

    print("\nDevises :")
    for key, value in stats.get("currencies_percent", {}).items():
        print(f"  - {key}: {value}%")

    print("\nGéographie :")
    print(f"  - Nouakchott total: {stats.get('nouakchott_percent')}%")
    print(f"  - Dakhlet Nouadhibou: {stats.get('nouadhibou_percent')}%")

    print("\nTypes de transactions :")
    for key, value in stats.get("transaction_types_percent", {}).items():
        print(f"  - {key}: {value}%")

    print("\nAnomalies :")
    print(f"  - Pourcentage anomalies: {stats.get('anomaly_percent')}%")
    for key, value in stats.get("anomaly_types_count", {}).items():
        print(f"  - {key}: {value}")


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def build_arg_parser() -> argparse.ArgumentParser:
    """
    Crée le parser CLI.

    Cela permet de lancer le générateur avec :
    python -m mauripay.synthetic.generator --rows 10000 --output ...
    """

    parser = argparse.ArgumentParser(
        description="Générateur synthétique MauriPay"
    )

    parser.add_argument(
        "--rows",
        type=int,
        default=10_000,
        help="Nombre de transactions à générer",
    )

    parser.add_argument(
        "--accounts",
        type=int,
        default=DEFAULT_NUM_ACCOUNTS,
        help="Nombre de comptes fictifs à créer",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="data/generated/mauripay_s.csv",
        help="Chemin de sortie .csv, .json ou .parquet",
    )

    parser.add_argument(
        "--start-date",
        type=str,
        default=DEFAULT_START_DATE,
        help="Date de début au format YYYY-MM-DD",
    )

    parser.add_argument(
        "--end-date",
        type=str,
        default=DEFAULT_END_DATE,
        help="Date de fin au format YYYY-MM-DD",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_RANDOM_SEED,
        help="Seed aléatoire pour reproductibilité",
    )

    parser.add_argument(
        "--anomaly-rate",
        type=float,
        default=DEFAULT_ANOMALY_RATE,
        help="Taux d'anomalies simples, ex: 0.02 = 2%",
    )

    parser.add_argument(
        "--tontine-rate",
        type=float,
        default=DEFAULT_TONTINE_RATE,
        help="Probabilite de generer une sequence normale de tontine",
    )

    parser.add_argument(
        "--structuring-rate",
        type=float,
        default=0.003,
        help="Probabilité de générer une séquence STRUCTURING",
    )

    parser.add_argument(
        "--high-frequency-rate",
        type=float,
        default=0.002,
        help="Probabilité de générer une séquence HIGH_FREQUENCY",
    )

    return parser


def main() -> None:
    """
    Point d'entrée principal du générateur.
    """

    parser = build_arg_parser()
    args = parser.parse_args()

    transactions = generate_transactions(
        rows=args.rows,
        num_accounts=args.accounts,
        start_date=args.start_date,
        end_date=args.end_date,
        seed=args.seed,
        anomaly_rate=args.anomaly_rate,
        tontine_rate=args.tontine_rate,
        structuring_rate=args.structuring_rate,
        high_frequency_rate=args.high_frequency_rate,
    )

    output_path = export_transactions(transactions, args.output)

    print(f"\nOK Dataset genere : {Path(output_path)}")

    stats = compute_basic_stats(transactions)
    print_stats(stats)


if __name__ == "__main__":
    main()
