# -*- coding: utf-8 -*-
# backend/src/mauripay/ingestion/schema.py

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid

from pydantic import BaseModel, Field, field_validator, model_validator


class Currency(str, Enum):
    MRU = "MRU"
    XOF = "XOF"
    USD = "USD"


class TransactionType(str, Enum):
    TRANSFER = "TRANSFER"
    BILL_PAY = "BILL_PAY"
    MERCHANT = "MERCHANT"
    CASH_IN = "CASH_IN"
    CASH_OUT = "CASH_OUT"
    AIRTIME = "AIRTIME"


class Channel(str, Enum):
    USSD = "USSD"
    APP = "APP"
    AGENT = "AGENT"


class Operator(str, Enum):
    BANKILY = "Bankily"
    MASRVI = "Masrvi"
    SEDAD = "Sedad"
    CLICK = "Click"
    BIMBANK = "bimbank Mobile"
    BAMIS_DIGITAL = "Bamis Digital"
    GAZAPAY = "GazaPay"
    BARIDCASH = "BaridCash"
    BCIPAY = "BCIpay"
    ATTIJARI_MOBILE = "Attijari Mobile"
    AMANTY = "Amanty"
    MOOV_MONEY = "Moov Money"
    RASSIDY = "Rassidy رصيدي"


class Wilaya(str, Enum):
    NOUAKCHOTT_OUEST = "Nouakchott-Ouest"
    NOUAKCHOTT_NORD = "Nouakchott-Nord"
    NOUAKCHOTT_SUD = "Nouakchott-Sud"
    HODH_EL_CHARGUI = "Hodh El Chargui"
    HODH_EL_GHARBI = "Hodh El Gharbi"
    ASSABA = "Assaba"
    GORGOL = "Gorgol"
    BRAKNA = "Brakna"
    TRARZA = "Trarza"
    ADRAR = "Adrar"
    DAKHLET_NOUADHIBOU = "Dakhlet Nouadhibou"
    TAGANT = "Tagant"
    GUIDIMAKHA = "Guidimakha"
    TIRIS_ZEMMOUR = "Tiris Zemmour"
    INCHIRI = "Inchiri"


class TransactionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"


class AnomalyType(str, Enum):
    NONE = "NONE"
    HIGH_AMOUNT = "HIGH_AMOUNT"
    STRUCTURING = "STRUCTURING"
    OPERATOR_OUTAGE = "OPERATOR_OUTAGE"
    HIGH_FREQUENCY = "HIGH_FREQUENCY"
    UNUSUAL_LOCATION = "UNUSUAL_LOCATION"


class BillProvider(str, Enum):
    SOMELEC = "SOMELEC"
    SNDE = "SNDE"
    MAURITEL = "MAURITEL"
    CHINGUITEL = "CHINGUITEL"
    MATTEL = "MATTEL"

class Transaction(BaseModel):
    """
    Schéma standardisé d'une transaction Mobile Money MauriPay.
    Inspiré du format PaySim et adapté au contexte mauritanien.
    """

    transaction_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="UUID v4 unique de la transaction",
    )

    timestamp: datetime = Field(
        description="Horodatage ISO 8601 avec timezone UTC+0",
    )

    sender_id: str = Field(
        pattern=r"^ACC_\d{5}$",
        description="Identifiant anonymisé du compte émetteur",
    )

    receiver_id: str = Field(
        pattern=r"^ACC_\d{5}$",
        description="Identifiant anonymisé du compte récepteur",
    )

    amount: Decimal = Field(
        gt=0,
        le=Decimal("10000000.00"),
        decimal_places=2,
        description="Montant de la transaction",
    )

    currency: Currency = Currency.MRU

    fees: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        decimal_places=2,
        description="Frais de transaction",
    )

    transaction_type: TransactionType
    channel: Channel
    operator: Operator
    status: TransactionStatus = TransactionStatus.SUCCESS

    sender_wilaya: Wilaya
    receiver_wilaya: Wilaya

    is_ramadan: bool = False

    bill_provider: Optional[BillProvider] = None

    origin_country: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=2,
        pattern=r"^[A-Z]{2}$",
        description="Code pays ISO 3166-1 alpha-2, ex: FR, ES, US",
    )

    is_anomaly: bool = False
    anomaly_type: AnomalyType = AnomalyType.NONE

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_have_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp doit contenir une timezone")

        if value.utcoffset() != timezone.utc.utcoffset(value):
            raise ValueError("timestamp doit être en UTC+0")

        # if value > datetime.now(timezone.utc):
        #     raise ValueError("timestamp ne peut pas être dans le futur")

        return value

    @model_validator(mode="after")
    def validate_business_rules(self):
        if self.sender_id == self.receiver_id:
            raise ValueError(
                "sender_id et receiver_id ne peuvent pas être identiques"
            )

        if self.fees > self.amount:
            raise ValueError(
                "fees ne peut pas être supérieur à amount"
            )

        if self.transaction_type == TransactionType.BILL_PAY:
            if self.bill_provider is None:
                raise ValueError(
                    "bill_provider est obligatoire pour BILL_PAY"
                )
        else:
            if self.bill_provider is not None:
                raise ValueError(
                    "bill_provider doit être None sauf pour BILL_PAY"
                )

        if self.transaction_type != TransactionType.CASH_IN:
            if self.origin_country is not None:
                raise ValueError(
                    "origin_country doit être None sauf pour CASH_IN diaspora"
                )

        if self.is_anomaly and self.anomaly_type == AnomalyType.NONE:
            raise ValueError(
                "Si is_anomaly=True, anomaly_type doit être différent de NONE"
            )

        if not self.is_anomaly and self.anomaly_type != AnomalyType.NONE:
            raise ValueError(
                "Si is_anomaly=False, anomaly_type doit être NONE"
            )

        return self

    model_config = {
        "use_enum_values": True,
        "json_encoders": {Decimal: str},
    }
