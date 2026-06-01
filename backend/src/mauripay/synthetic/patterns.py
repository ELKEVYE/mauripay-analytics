# backend/src/mauripay/synthetic/patterns.py

from __future__ import annotations

import random
from bisect import bisect_left
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from typing import Any

from mauripay.synthetic.config import (
    AMOUNT_RANGES,
    BILL_PROVIDER_WEIGHTS,
    CHANNEL_WEIGHTS,
    DIASPORA_COUNTRY_WEIGHTS,
    DIASPORA_CASH_IN_RATE,
    GEOGRAPHIC_WEIGHTS,
    OPERATOR_WEIGHTS,
    RAMADAN_2026_END,
    RAMADAN_2026_START,
    RURAL_CHANNEL_WEIGHTS,
    RURAL_WILAYAS,
    TRANSACTION_TYPE_WEIGHTS,
)


def weighted_choice(weights: dict[str, float]) -> str:
    """
    Choisit une valeur selon une distribution de probabilités.
    """
    values = list(weights.keys())
    probabilities = list(weights.values())
    return random.choices(values, weights=probabilities, k=1)[0]


def money(value: Decimal) -> Decimal:
    """
    Arrondit un montant financier à deux décimales.
    """
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def random_decimal_between(min_value: Decimal, max_value: Decimal) -> Decimal:
    """
    Génère un Decimal aléatoire entre deux bornes.
    """
    random_float = random.uniform(float(min_value), float(max_value))
    return money(Decimal(str(random_float)))


# ─────────────────────────────────────────────
# PATTERN 1 — RAMADAN
# ─────────────────────────────────────────────

def is_ramadan_period(timestamp: datetime) -> bool:
    """
    Retourne True si le timestamp est pendant Ramadan 2026.
    """
    current_date = timestamp.date()
    return RAMADAN_2026_START <= current_date <= RAMADAN_2026_END


def ramadan_multiplier(timestamp: datetime) -> float:
    """
    Multiplicateur de volume pendant Ramadan.

    S3 : utilisé surtout pour marquer la logique.
    S4 : pourra être utilisé pour augmenter réellement le nombre de transactions.
    """
    if is_ramadan_period(timestamp):
        return 2.5

    return 1.0


def choose_hour_for_timestamp(base_timestamp: datetime) -> datetime:
    """
    Ajuste l'heure d'une transaction.

    Pendant Ramadan :
    - 60 % des transactions sont entre 19h et 23h.

    Hors Ramadan :
    - distribution plus large entre 7h et 22h.
    """
    if is_ramadan_period(base_timestamp) and random.random() < 0.60:
        hour = random.randint(19, 23)
    else:
        hour = random.randint(7, 22)

    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    return base_timestamp.replace(hour=hour, minute=minute, second=second, microsecond=0)


# ─────────────────────────────────────────────
# PATTERN 2 — CYCLES SALARIAUX
# ─────────────────────────────────────────────

def salary_day_multiplier(timestamp: datetime) -> float:
    """
    Les jours 1 à 5 du mois ont plus d'activité.
    """
    if timestamp.day in [1, 2, 3, 4, 5]:
        return 1.8

    return 1.0


@lru_cache(maxsize=32)
def build_patterned_date_distribution(
    start: datetime,
    end: datetime,
) -> tuple[tuple[Any, ...], tuple[float, ...], float]:
    """
    Precalcule les jours et poids cumules pour une plage de generation.

    Le cache evite de reconstruire la meme distribution pour chaque ligne.
    C'est important pour les gros datasets, par exemple 1 000 000 lignes.
    """
    current_date = start.date()
    end_date = end.date()

    candidate_dates = []
    cumulative_weights = []
    total_weight = 0.0

    while current_date <= end_date:
        probe = datetime(
            current_date.year,
            current_date.month,
            current_date.day,
            tzinfo=start.tzinfo,
        )

        weight = ramadan_multiplier(probe) * salary_day_multiplier(probe)
        total_weight += weight

        candidate_dates.append(current_date)
        cumulative_weights.append(total_weight)

        current_date = current_date + timedelta(days=1)

    return tuple(candidate_dates), tuple(cumulative_weights), total_weight


def choose_patterned_timestamp(start: datetime, end: datetime) -> datetime:
    """
    Choisit un timestamp en ponderant les jours avec les patterns temporels.

    Ramadan augmente le poids du jour a x2.5. Les jours 1 a 5 augmentent
    le poids a x1.8. Si les deux patterns se croisent, les poids se
    multiplient.
    """
    if start >= end:
        raise ValueError("start doit etre avant end")

    candidate_dates, cumulative_weights, total_weight = (
        build_patterned_date_distribution(start, end)
    )
    random_weight = random.random() * total_weight
    date_index = bisect_left(cumulative_weights, random_weight)
    chosen_date = candidate_dates[date_index]

    day_start = datetime(
        chosen_date.year,
        chosen_date.month,
        chosen_date.day,
        tzinfo=start.tzinfo,
    )
    day_end = day_start + timedelta(days=1) - timedelta(seconds=1)

    lower_bound = max(day_start, start)
    upper_bound = min(day_end, end)

    random_seconds = random.randint(
        0,
        int((upper_bound - lower_bound).total_seconds()),
    )
    base_timestamp = lower_bound + timedelta(seconds=random_seconds)
    patterned_timestamp = choose_hour_for_timestamp(base_timestamp)

    if patterned_timestamp < lower_bound:
        return lower_bound

    if patterned_timestamp > upper_bound:
        return upper_bound

    return patterned_timestamp


def adjust_transaction_type_for_salary_day(transaction_type: str, timestamp: datetime) -> str:
    """
    En début de mois, on favorise CASH_OUT, BILL_PAY et TRANSFER.
    """
    if timestamp.day not in [1, 2, 3, 4, 5]:
        return transaction_type

    salary_weights = {
        "CASH_OUT": 0.40,
        "BILL_PAY": 0.30,
        "TRANSFER": 0.20,
        "MERCHANT": 0.05,
        "AIRTIME": 0.03,
        "CASH_IN": 0.02,
    }

    return weighted_choice(salary_weights)


# ─────────────────────────────────────────────
# PATTERN 3 — FACTURES SOMELEC / SNDE
# ─────────────────────────────────────────────

def choose_bill_provider() -> str:
    """
    Choisit un fournisseur de facture.
    """
    return weighted_choice(BILL_PROVIDER_WEIGHTS)


def choose_bill_amount(provider: str) -> Decimal:
    """
    Montants réalistes par type de fournisseur.
    """
    if provider == "SOMELEC":
        return random_decimal_between(Decimal("800.00"), Decimal("8000.00"))

    if provider == "SNDE":
        return random_decimal_between(Decimal("400.00"), Decimal("2000.00"))

    if provider in {"MAURITEL", "CHINGUITEL"}:
        return random_decimal_between(Decimal("200.00"), Decimal("3000.00"))

    return random_decimal_between(Decimal("400.00"), Decimal("8000.00"))


# ─────────────────────────────────────────────
# PATTERN 4 — TRANSFERTS DIASPORA
# ─────────────────────────────────────────────

def should_be_diaspora_cash_in(transaction_type: str, timestamp: datetime) -> bool:
    """
    Une partie des CASH_IN vient de la diaspora.

    Les vendredis, samedis et dimanches ont plus de probabilité.
    """
    if transaction_type != "CASH_IN":
        return False

    probability = DIASPORA_CASH_IN_RATE

    # weekday : lundi=0, vendredi=4, samedi=5, dimanche=6
    if timestamp.weekday() in [4, 5, 6]:
        probability *= 1.4

    return random.random() < min(probability, 1.0)


def choose_diaspora_origin() -> str:
    """
    Choisit le pays d'origine d'un transfert diaspora.
    """
    return weighted_choice(DIASPORA_COUNTRY_WEIGHTS)


def choose_diaspora_amount() -> Decimal:
    """
    Montant plus élevé que les petits transferts domestiques.
    """
    return random_decimal_between(Decimal("5000.00"), Decimal("80000.00"))


# ─────────────────────────────────────────────
# PATTERN 5 — TONTINES EL LEWHA
# ─────────────────────────────────────────────

def generate_tontine_group(accounts: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Prépare un groupe de tontine.

    S3 : fonction de préparation.
    S4 : peut être utilisée pour injecter des séquences de transactions groupées.
    """
    if len(accounts) < 30:
        group_size = min(len(accounts), random.randint(10, 30))
    else:
        group_size = random.randint(10, 30)

    members = random.sample(accounts, k=group_size)
    beneficiary = random.choice(members)

    amount = random.choice([
        Decimal("500.00"),
        Decimal("1000.00"),
        Decimal("2000.00"),
        Decimal("5000.00"),
    ])

    frequency = random.choice(["WEEKLY", "MONTHLY"])

    return {
        "members": members,
        "beneficiary": beneficiary,
        "amount": amount,
        "frequency": frequency,
        "window_hours": 2,
    }


# ─────────────────────────────────────────────
# PATTERN 6 — GÉOGRAPHIE
# ─────────────────────────────────────────────

def choose_wilaya() -> str:
    """
    Choisit une wilaya selon les poids géographiques.
    """
    return weighted_choice(GEOGRAPHIC_WEIGHTS)


# ─────────────────────────────────────────────
# PATTERN 7 — CANAUX
# ─────────────────────────────────────────────

def choose_channel(wilaya: str | None = None) -> str:
    """
    Choisit un canal.

    Dans les wilayas rurales, USSD est plus fréquent.
    """
    if wilaya in RURAL_WILAYAS:
        return weighted_choice(RURAL_CHANNEL_WEIGHTS)

    return weighted_choice(CHANNEL_WEIGHTS)


# ─────────────────────────────────────────────
# AUTRES CHOIX MÉTIER
# ─────────────────────────────────────────────

def choose_operator() -> str:
    """
    Choisit un opérateur Mobile Money.
    """
    return weighted_choice(OPERATOR_WEIGHTS)


def choose_transaction_type(timestamp: datetime) -> str:
    """
    Choisit le type de transaction avec ajustement en période salariale.
    """
    transaction_type = weighted_choice(TRANSACTION_TYPE_WEIGHTS)
    transaction_type = adjust_transaction_type_for_salary_day(transaction_type, timestamp)
    return transaction_type


def choose_amount(transaction_type: str, bill_provider: str | None = None, diaspora: bool = False) -> Decimal:
    """
    Choisit le montant selon le type de transaction.
    """
    if transaction_type == "BILL_PAY" and bill_provider is not None:
        return choose_bill_amount(bill_provider)

    if transaction_type == "CASH_IN" and diaspora:
        return choose_diaspora_amount()

    min_amount, max_amount = AMOUNT_RANGES[transaction_type]
    return random_decimal_between(min_amount, max_amount)


def compute_fees(amount: Decimal, transaction_type: str) -> Decimal:
    """
    Calcule les frais de transaction.

    Règle simple S3 :
    - AIRTIME et BILL_PAY : souvent 0
    - autres : entre 0.5 % et 2 %
    """
    if transaction_type in {"AIRTIME", "BILL_PAY"}:
        return Decimal("0.00")

    rate = Decimal(str(random.uniform(0.005, 0.02)))
    return money(amount * rate)


def random_timestamp_between(start: datetime, end: datetime) -> datetime:
    """
    Génère un timestamp aléatoire entre deux dates.
    """
    return choose_patterned_timestamp(start, end)
