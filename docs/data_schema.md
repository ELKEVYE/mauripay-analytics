# Schéma des données

Le schéma canonique est la classe Pydantic `Transaction`, définie dans
`backend/src/mauripay/ingestion/schema.py`. Elle valide chaque transaction
avant son utilisation par le générateur, l’ingestion ou les modèles.

## Champs

| Champ | Type | Présence à l’entrée | Description |
|---|---|---|---|
| `transaction_id` | chaîne | Facultative, UUID généré par défaut | Identifiant unique de la transaction |
| `timestamp` | datetime UTC | Obligatoire | Date et heure ISO 8601 avec fuseau UTC |
| `sender_id` | chaîne | Obligatoire | Identifiant anonymisé de l’expéditeur |
| `receiver_id` | chaîne | Obligatoire | Identifiant anonymisé du destinataire |
| `amount` | Decimal | Obligatoire | Montant strictement positif, limité à 10 000 000 |
| `currency` | enum | Facultative, `MRU` par défaut | Devise de la transaction |
| `fees` | Decimal | Facultative, `0.00` par défaut | Frais positifs ou nuls |
| `transaction_type` | enum | Obligatoire | Nature de l’opération |
| `channel` | enum | Obligatoire | Moyen utilisé pour l’opération |
| `operator` | enum | Obligatoire | Opérateur ou service Mobile Money |
| `status` | enum | Facultative, `SUCCESS` par défaut | État de la transaction |
| `sender_wilaya` | enum | Obligatoire | Wilaya associée à l’expéditeur |
| `receiver_wilaya` | enum | Obligatoire | Wilaya associée au destinataire |
| `is_ramadan` | booléen | Facultative, `false` par défaut | Indique le contexte du Ramadan |
| `bill_provider` | enum ou `null` | Conditionnelle | Fournisseur obligatoire pour `BILL_PAY` |
| `origin_country` | chaîne ou `null` | Facultative pour `CASH_IN` | Pays d’origine, code ISO alpha-2 |
| `is_anomaly` | booléen | Facultative, `false` par défaut | Vérité terrain synthétique |
| `anomaly_type` | enum | Facultative, `NONE` par défaut | Type d’anomalie injecté |

Le cahier des charges emploie parfois le terme général `wilaya`. Le schéma
réel distingue :

```text
sender_wilaya
receiver_wilaya
```

## Identifiants des comptes

`sender_id` et `receiver_id` doivent respecter le format :

```text
ACC_ suivi exactement de cinq chiffres
```

Exemples valides :

```text
ACC_00001
ACC_12345
```

## Devises

| Valeur | Description |
|---|---|
| `MRU` | Ouguiya mauritanienne |
| `XOF` | Franc CFA d’Afrique de l’Ouest |
| `USD` | Dollar américain |

## Types de transactions

| Valeur | Description |
|---|---|
| `TRANSFER` | Transfert entre deux comptes |
| `CASH_IN` | Entrée ou dépôt d’argent |
| `CASH_OUT` | Retrait d’argent |
| `BILL_PAY` | Paiement d’une facture |
| `AIRTIME` | Achat de crédit téléphonique |
| `MERCHANT` | Paiement auprès d’un commerçant |

## Canaux

| Valeur | Description |
|---|---|
| `USSD` | Menu téléphonique fonctionnant sans application |
| `APP` | Application mobile |
| `AGENT` | Point de service ou agent Mobile Money |

## Statuts

Le code accepte trois statuts :

| Valeur | Description |
|---|---|
| `SUCCESS` | Transaction réussie |
| `FAILED` | Transaction échouée |
| `PENDING` | Transaction en attente |

## Fournisseurs de factures

Les valeurs acceptées pour `bill_provider` sont :

```text
SOMELEC
SNDE
MAURITEL
CHINGUITEL
MATTEL
```

## Types d’anomalies

| Valeur | Description |
|---|---|
| `NONE` | Aucune anomalie connue |
| `HIGH_AMOUNT` | Montant anormalement élevé |
| `HIGH_FREQUENCY` | Nombre important d’opérations rapprochées |
| `STRUCTURING` | Fractionnement d’un montant en plusieurs transferts |
| `OPERATOR_OUTAGE` | Groupe d’échecs associé à un opérateur |
| `UNUSUAL_LOCATION` | Localisation inhabituelle |

## Règles de validation

Pydantic applique notamment les règles suivantes :

- `amount` doit être supérieur à zéro et inférieur ou égal à
  `10 000 000.00` ;
- `amount` et `fees` acceptent au maximum deux décimales ;
- `fees` doit être positif ou nul et ne peut pas dépasser `amount` ;
- `sender_id` et `receiver_id` doivent être différents ;
- `timestamp` doit contenir un fuseau horaire et être en UTC+0 ;
- `bill_provider` est obligatoire pour `BILL_PAY` et interdit pour les autres
  types ;
- `origin_country`, lorsqu’il est renseigné, doit être un code de deux lettres
  majuscules et n’est autorisé que pour `CASH_IN` ;
- si `is_anomaly=true`, `anomaly_type` doit être différent de `NONE` ;
- si `is_anomaly=false`, `anomaly_type` doit être égal à `NONE`.

## Exemple JSON valide

```json
{
  "transaction_id": "TX_20260729_000001",
  "timestamp": "2026-07-29T10:30:00Z",
  "sender_id": "ACC_00001",
  "receiver_id": "ACC_00042",
  "amount": "3500.00",
  "currency": "MRU",
  "fees": "35.00",
  "transaction_type": "BILL_PAY",
  "channel": "APP",
  "operator": "Bankily",
  "status": "SUCCESS",
  "sender_wilaya": "Nouakchott-Ouest",
  "receiver_wilaya": "Nouakchott-Ouest",
  "is_ramadan": false,
  "bill_provider": "SOMELEC",
  "origin_country": null,
  "is_anomaly": false,
  "anomaly_type": "NONE"
}
```

Les nombres monétaires peuvent être fournis sous forme de chaînes afin de
préserver précisément leurs décimales.
