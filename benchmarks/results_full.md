# Benchmark S7 - Comparaison des detecteurs

Date : 2026-05-24 04:28:10 +02:00
Machine : Windows-10-10.0.19045-SP0
Python : 3.12.3
Dataset : MauriPay-S 10K
Fichier : `data/generated/mauripay_s_10k.csv`
Lignes : 10000
Normales : 9320
Anomalies : 680
Seed : 42
Features utilisees : TransactionFeatureEngineer

Commande executee :

```bash
python benchmarks/run_benchmark.py --benchmark full_10k --data data/generated/mauripay_s_10k.csv --output benchmarks/results/full_10k_benchmark.json --threshold-percentile 98
```

Les valeurs ci-dessous viennent de l'execution reelle stockee dans
`benchmarks/results/full_10k_benchmark.json`.

| Dataset | Algorithme | Precision | Recall | F1-score | ROC-AUC | Train(s) | Infer(s) | Anomalies detectees |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| MauriPay-S 10K | Isolation Forest | 0.6150 | 0.1809 | 0.2795 | 0.7913 | 0.5096 | 0.3374 | 200 |
| MauriPay-S 10K | LOF | 0.2531 | 0.0603 | 0.0974 | 0.6839 | 3.5464 | 1.8186 | 162 |
| MauriPay-S 10K | Autoencoder | 0.7096 | 0.7618 | 0.7348 | 0.9078 | 23.5140 | 0.2134 | 730 |

## Notes

- Isolation Forest et LOF utilisent les features ajustees sur tout le dataset.
- Autoencoder utilise des features ajustees sur les lignes normales uniquement.
- Le seuil Autoencoder stocke dans ce run correspond au percentile 98 des
  erreurs de reconstruction.
- Les temps `Train(s)` et `Infer(s)` mesurent uniquement le fit/inference des modeles, pas le chargement CSV ni le feature engineering.

## MauriPay-M 100K

Scenario ajoute dans le runner. Commande officielle :

```bash
python benchmarks/run_benchmark.py --benchmark full_100k
```

Sortie par defaut :

```text
benchmarks/results/full_100k_benchmark.json
```

Ce scenario compare les memes 3 detecteurs que le 10K, dans le meme format
JSON :

- Isolation Forest
- LOF
- Autoencoder

Le fichier `backend/outputs/evaluation_autoencoder.json` contient deja une
evaluation Autoencoder sur `data/generated/mauripay_m_100k.csv`, mais le
benchmark comparatif 100K doit etre regenere avec la commande ci-dessus pour
obtenir les trois modeles dans un seul rapport.

## MauriPay-L 1M

Scenario ajoute dans le runner. Commande officielle :

```bash
python benchmarks/run_benchmark.py --benchmark full_1m
```

Sortie par defaut :

```text
benchmarks/results/full_1m_benchmark.json
```

Le dataset par defaut est `data/generated/mauripay_l_1m.parquet`. Ce benchmark
est potentiellement long, surtout pour LOF et Autoencoder ; il doit donc etre
execute sur une machine avec assez de RAM et, idealement, GPU pour PyTorch.
