# MauriPay-Analytics

MauriPay-Analytics est une plateforme open-source d'analyse de transactions
Mobile Money adaptee au contexte mauritanien et ouest-africain.

Le projet fournit actuellement :

- un schema de donnees Pydantic pour les transactions Mobile Money ;
- des exemples d'ingestion en CSV et JSON ;
- un generateur de donnees synthetiques realistes ;
- des patterns mauritaniens : Ramadan, salaires, factures, diaspora, tontines,
  geographie et canaux USSD/APP/AGENT ;
- des anomalies injectees pour tester les futurs algorithmes de detection ;
- des exports CSV, JSON et Parquet ;
- une base technique pour les futurs modules ML : Isolation Forest, LOF et
  Autoencoder.

## Structure utile

```text
backend/src/mauripay/ingestion/schema.py
backend/src/mauripay/ingestion/samples/sample.csv
backend/src/mauripay/ingestion/samples/sample.json
backend/src/mauripay/docs/patterns.md
backend/src/mauripay/docs/schema_decisions.md
backend/src/mauripay/synthetic/config.py
backend/src/mauripay/synthetic/patterns.py
backend/src/mauripay/synthetic/generator.py
backend/src/mauripay/synthetic/anomalies.py
backend/src/mauripay/synthetic/exporters.py
backend/src/mauripay/synthetic/validate.py
```

Les fichiers generes sont produits dans `data/generated/` depuis le dossier
`backend/`. Ce dossier peut etre regenere a tout moment avec les commandes
ci-dessous.

## Generation des datasets

Depuis `backend/` :

```powershell
$env:PYTHONPATH="src"

python -m mauripay.synthetic.generator --rows 10000 --output data/generated/mauripay_s_10k.csv
python -m mauripay.synthetic.generator --rows 100000 --output data/generated/mauripay_m_100k.csv
python -m mauripay.synthetic.generator --rows 1000000 --output data/generated/mauripay_l_1m.parquet
```

Parametres importants :

- `--anomaly-rate 0.02` : environ 2 % d'anomalies simples.
- `--structuring-rate 0.003` : probabilite de creer une sequence STRUCTURING.
- `--high-frequency-rate 0.002` : probabilite de creer une sequence HIGH_FREQUENCY.
- `--seed 42` : generation reproductible.

## Validation

```powershell
$env:PYTHONPATH="src"

python -m compileall mauripay
python -m mauripay.synthetic.validate data/generated/mauripay_s_10k.csv
python -m mauripay.synthetic.validate data/generated/mauripay_m_100k.csv
python -m mauripay.synthetic.validate data/generated/mauripay_l_1m.parquet
```

Le validateur controle maintenant deux niveaux :

- les colonnes attendues ;
- chaque ligne avec `Transaction(**payload)` depuis `schema.py`.

La validation Pydantic verifie donc aussi les enums, les montants, les
timestamps UTC, `bill_provider`, `origin_country`, `fees`, `sender_id !=
receiver_id` et la coherence `is_anomaly` / `anomaly_type`.

## Resultats attendus

Avec les parametres par defaut et `seed=42`, les statistiques doivent rester
proches de :

| Dataset | USSD | APP | AGENT | Nouakchott | Nouadhibou | Anomalies |
|---|---:|---:|---:|---:|---:|---:|
| MauriPay-S 10k | 72.11 % | 22.98 % | 4.91 % | 59.75 % | 15.00 % | 7.98 % |
| MauriPay-M 100k | 71.78 % | 23.03 % | 5.19 % | 58.92 % | 15.31 % | 7.36 % |
| MauriPay-L 1M | 71.63 % | 23.19 % | 5.19 % | 58.68 % | 15.28 % | 7.28 % |

Le taux total d'anomalies autour de 7 a 8 % est normal. `--anomaly-rate 0.02`
ne concerne que les anomalies simples : HIGH_AMOUNT, OPERATOR_OUTAGE et
UNUSUAL_LOCATION. Les anomalies STRUCTURING et HIGH_FREQUENCY sont des
sequences : un seul evenement peut creer plusieurs transactions anormales, ce
qui augmente le taux final mesure ligne par ligne.

## Etat S1-S4

- S1 : revue conceptuelle PaySim, Mobile Money, Isolation Forest, LOF et
  Autoencoder posee comme base scientifique.
- S2 : schema Pydantic, decisions de schema, patterns et samples CSV/JSON.
- S3 : generateur normal, comptes fictifs, geographie, canaux et exports.
- S4 : anomalies, validation Pydantic, generation S/M/L et documentation.

Apres regeneration et validation des fichiers S/M/L, le projet peut passer a
S5 : preparation ML, features, baseline Isolation Forest / LOF / Autoencoder et
evaluation.
