# backend/src/mauripay/synthetic/config.py

from __future__ import annotations

from decimal import Decimal
from datetime import date, datetime, timezone

# ─────────────────────────────────────────────
# PARAMÈTRES GÉNÉRAUX
# ─────────────────────────────────────────────

DEFAULT_RANDOM_SEED = 42

DEFAULT_NUM_ACCOUNTS = 5_000

DEFAULT_START_DATE = "2026-01-01"
DEFAULT_END_DATE = datetime.now(timezone.utc).date().isoformat()

MAX_AMOUNT = Decimal("10000000.00")

# Compatible avec schema.py : pattern ACC_\d{5}
ACCOUNT_ID_FORMAT = "ACC_{:05d}"


# ─────────────────────────────────────────────
# DEVISE M1
# ─────────────────────────────────────────────


CURRENCIES = ["MRU", "XOF", "USD"]

CURRENCY_WEIGHTS = {
    "MRU": 0.92,
    "XOF": 0.05,
    "USD": 0.03,
}


# ─────────────────────────────────────────────
# OPÉRATEURS
# IMPORTANT : cette liste doit correspondre à ton Enum Operator dans schema.py
# ─────────────────────────────────────────────

OPERATORS = [
    "Bankily",
    "Masrvi",
    "Sedad",
    "Click",
    "bimbank Mobile",
    "Bamis Digital",
    "GazaPay",
    "BaridCash",
    "BCIpay",
    "Attijari Mobile",
    "Amanty",
    "Moov Money",
    "Rassidy رصيدي",
]

OPERATOR_WEIGHTS = {
    "Bankily": 0.24,
    "Masrvi": 0.15,
    "Sedad": 0.12,
    "Click": 0.08,
    "bimbank Mobile": 0.07,
    "Bamis Digital": 0.05,
    "GazaPay": 0.04,
    "BaridCash": 0.03,
    "BCIpay": 0.03,
    "Attijari Mobile": 0.06,
    "Amanty": 0.05,
    "Moov Money": 0.05,
    "Rassidy رصيدي": 0.03,
}


# ─────────────────────────────────────────────
# TYPES DE TRANSACTIONS
# ─────────────────────────────────────────────

TRANSACTION_TYPES = [
    "TRANSFER",
    "BILL_PAY",
    "MERCHANT",
    "CASH_IN",
    "CASH_OUT",
    "AIRTIME",
]

TRANSACTION_TYPE_WEIGHTS = {
    "TRANSFER": 0.35,
    "BILL_PAY": 0.12,
    "MERCHANT": 0.18,
    "CASH_IN": 0.12,
    "CASH_OUT": 0.13,
    "AIRTIME": 0.10,
}


# ─────────────────────────────────────────────
# CANAUX
# Objectif : USSD ≈ 70 %, APP ≈ 25 %, AGENT ≈ 5 %
# ─────────────────────────────────────────────

CHANNELS = ["USSD", "APP", "AGENT"]

CHANNEL_WEIGHTS = {
    "USSD": 0.70,
    "APP": 0.25,
    "AGENT": 0.05,
}

RURAL_CHANNEL_WEIGHTS = {
    "USSD": 0.85,
    "APP": 0.10,
    "AGENT": 0.05,
}


# ─────────────────────────────────────────────
# WILAYAS
# Compatible avec l'Enum Wilaya de schema.py
# ─────────────────────────────────────────────

WILAYAS = [
    "Nouakchott-Ouest",
    "Nouakchott-Nord",
    "Nouakchott-Sud",
    "Hodh El Chargui",
    "Hodh El Gharbi",
    "Assaba",
    "Gorgol",
    "Brakna",
    "Trarza",
    "Adrar",
    "Dakhlet Nouadhibou",
    "Tagant",
    "Guidimakha",
    "Tiris Zemmour",
    "Inchiri",
]

NOUAKCHOTT_WILAYAS = [
    "Nouakchott-Ouest",
    "Nouakchott-Nord",
    "Nouakchott-Sud",
]

RURAL_WILAYAS = [
    "Adrar",
    "Tagant",
    "Tiris Zemmour",
    "Inchiri",
    "Hodh El Chargui",
    "Hodh El Gharbi",
    "Guidimakha",
]

# Objectif : Nouakchott ≈ 60 %, Nouadhibou ≈ 15 %, autres ≈ 25 %
GEOGRAPHIC_WEIGHTS = {
    "Nouakchott-Ouest": 0.20,
    "Nouakchott-Nord": 0.20,
    "Nouakchott-Sud": 0.20,
    "Dakhlet Nouadhibou": 0.15,
    "Trarza": 0.05,
    "Brakna": 0.04,
    "Gorgol": 0.03,
    "Hodh El Chargui": 0.03,
    "Assaba": 0.03,
    "Guidimakha": 0.02,
    "Hodh El Gharbi": 0.015,
    "Adrar": 0.015,
    "Tagant": 0.01,
    "Tiris Zemmour": 0.01,
    "Inchiri": 0.01,
}


# ─────────────────────────────────────────────
# RAMADAN 2026
# À vérifier avec calendrier islamique officiel
# ─────────────────────────────────────────────

RAMADAN_2026_START = date(2026, 2, 17)
RAMADAN_2026_END = date(2026, 3, 18)


# ─────────────────────────────────────────────
# FOURCHETTES DE MONTANTS PAR TYPE
# ─────────────────────────────────────────────

AMOUNT_RANGES = {
    "TRANSFER": (Decimal("100.00"), Decimal("80000.00")),
    "BILL_PAY": (Decimal("400.00"), Decimal("8000.00")),
    "MERCHANT": (Decimal("100.00"), Decimal("25000.00")),
    "CASH_IN": (Decimal("500.00"), Decimal("85000.00")),
    "CASH_OUT": (Decimal("500.00"), Decimal("90000.00")),
    "AIRTIME": (Decimal("50.00"), Decimal("2000.00")),
}


# ─────────────────────────────────────────────
# FACTURES
# ─────────────────────────────────────────────

BILL_PROVIDERS = ["SOMELEC", "SNDE", "MAURITEL", "CHINGUITEL", "MATTEL"]

BILL_PROVIDER_WEIGHTS = {
    "SOMELEC": 0.42,
    "SNDE": 0.28,
    "MAURITEL": 0.14,
    "CHINGUITEL": 0.08,
    "MATTEL": 0.08,
}


# ─────────────────────────────────────────────
# DIASPORA
# ─────────────────────────────────────────────

DIASPORA_COUNTRIES = ["FR", "ES", "US"]

DIASPORA_COUNTRY_WEIGHTS = {
    "FR": 0.50,
    "ES": 0.25,
    "US": 0.25,
}

DIASPORA_CASH_IN_RATE = 0.20


# ─────────────────────────────────────────────
# ANOMALIES
# S3 : anomalies désactivées
# S4 : injection contrôlée
# ─────────────────────────────────────────────

DEFAULT_ANOMALY_RATE = 0.02

# Tontines El Lewha : comportement culturel normal, pas une anomalie.
DEFAULT_TONTINE_RATE = 0.001
