# S5 - Ingestion et Feature Engineering

Cette note documente la couche 2 du projet MauriPay-Analytics :
ingestion, validation Pydantic, rapport d'erreurs et preparation des donnees
pour les modeles IA.

## Objectif S5

Transformer les datasets generes pendant le mois 1 en donnees propres,
validees et exploitables par les futurs detecteurs d'anomalies :
Isolation Forest, LOF et Autoencoder.

```text
fichier CSV/JSON/JSONL/Parquet
        |
        v
adaptateur d'ingestion
        |
        v
validation Pydantic
        |
        v
transactions valides + rapport d'erreurs
        |
        v
feature engineering
        |
        v
DataFrame ML numerique
```

## Fichiers principaux

```text
backend/src/mauripay/ingestion/common.py
backend/src/mauripay/ingestion/csv_adapter.py
backend/src/mauripay/ingestion/json_adapter.py
backend/src/mauripay/ingestion/parquet_adapter.py
backend/src/mauripay/ingestion/loader.py
backend/src/mauripay/ingestion/schema.py

backend/src/mauripay/features/temporal.py
backend/src/mauripay/features/geographic.py
backend/src/mauripay/features/encoding.py
backend/src/mauripay/features/scaling.py
backend/src/mauripay/features/engineering.py
```

## Ingestion simple

```python
from mauripay.ingestion import load_transactions

transactions = load_transactions("data/generated/mauripay_s_10k.csv")
```

`load_transactions` detecte automatiquement l'extension :

- `.csv`
- `.json`
- `.jsonl`
- `.parquet`

## Mode strict

Le mode par defaut est strict. La lecture s'arrete a la premiere transaction
invalide.

```python
transactions = load_transactions("bad_transactions.csv")
```

Si une ligne est invalide, une `ValueError` est levee avec la source, la ligne
et les erreurs Pydantic.

## Mode rapport

Le mode rapport conserve les lignes valides et collecte toutes les lignes
invalides.

```python
from mauripay.ingestion import load_transactions

result = load_transactions("bad_transactions.csv", report=True)

print(result.ok)
print(result.total_rows)
print(result.valid_rows)
print(result.invalid_rows)

for error in result.errors:
    print(error.source)
    print(error.row_number)
    print(error.errors)
    print(error.payload)
```

Champs du rapport :

- `transactions` : transactions valides ;
- `errors` : erreurs ligne par ligne ;
- `total_rows` : nombre total de lignes ;
- `valid_rows` : nombre de lignes valides ;
- `invalid_rows` : nombre de lignes invalides ;
- `ok` : `True` si aucune erreur.

## Feature engineering

Pipeline complet :

```python
from mauripay.ingestion import load_transactions
from mauripay.features import build_features, model_feature_columns

transactions = load_transactions("data/generated/mauripay_s_10k.csv")
df_ml = build_features(transactions)

X = df_ml[model_feature_columns(df_ml)]
y = df_ml["is_anomaly"]
```

`build_features` applique :

1. conversion en DataFrame ;
2. features temporelles ;
3. ratio entrant/sortant ;
4. features geographiques ;
5. one-hot encoding ;
6. normalisation min-max ;
7. z-score ;
8. selection des colonnes numeriques.

## Features produites

Exemples de colonnes temporelles :

- `tx_count_1h`
- `tx_count_24h`
- `tx_count_7d`
- `amount_sum_1h`
- `amount_mean_24h`
- `amount_std_7d`
- `hour`
- `day_of_week`
- `is_weekend`
- `is_ramadan`

Exemples de colonnes de flux :

- `incoming_amount_24h`
- `outgoing_amount_24h`
- `incoming_outgoing_ratio_24h`

Exemples de colonnes geographiques :

- `sender_wilaya_code`
- `receiver_wilaya_code`
- `is_cross_wilaya`
- `wilaya_distance_km`

Exemples de colonnes encodees :

- `channel_USSD`
- `channel_APP`
- `channel_AGENT`
- `operator_Bankily`
- `transaction_type_TRANSFER`
- `transaction_type_BILL_PAY`

Exemples de colonnes normalisees :

- `amount_scaled`
- `amount_zscore`
- `tx_count_1h_scaled`
- `incoming_outgoing_ratio_24h_zscore`

`is_anomaly` reste dans le DataFrame final pour l'evaluation. Pour un modele
non supervise, il ne doit pas etre utilise comme variable d'entree.

## Option Polars

Pour preparer les gros volumes, le pipeline accepte une materialisation via
Polars :

```python
df_ml = build_features(transactions, dataframe_engine="polars")
```

Le calcul des features reste actuellement execute avec pandas, car les fenetres
glissantes sont deja implementees et testees dans ce moteur.

## Benchmark Parquet 1M

Le benchmark gros volume est hors tests unitaires :

```powershell
$env:PYTHONPATH="backend/src"
python benchmarks/parquet_1m_benchmark.py --output data/generated/mauripay_l_1m.parquet --dataframe-engine polars
```

Test rapide :

```powershell
$env:PYTHONPATH="backend/src"
python benchmarks/parquet_1m_benchmark.py --rows 10000 --output data/generated/benchmark_10k.parquet --force --dataframe-engine pandas
```

## Tests

Depuis la racine du projet :

```powershell
$env:PYTHONPATH="backend/src"
python -m unittest discover -s tests
```

Les tests couvrent :

- chargement CSV valide ;
- rejet `amount <= 0` ;
- rejet devise invalide ;
- rejet `sender_id == receiver_id` ;
- chargement Parquet valide ;
- rapport d'erreurs ;
- features temporelles ;
- features geographiques ;
- encodage one-hot ;
- normalisation min-max et z-score ;
- pipeline complet `build_features`.
