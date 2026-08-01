# Benchmarks

Les benchmarks comparent Isolation Forest, LOF et l’autoencoder sur les
datasets synthétiques. Les sources de référence sont
`benchmarks/results_full.md` et les fichiers JSON de `benchmarks/results/`.

## Environnement enregistré

| Propriété | Valeur |
|---|---|
| Système | Windows 10, version 10.0.19045 |
| Python | 3.12.3 |
| Seed | 42 |
| Préprocesseur | `TransactionFeatureEngineer` |

Les fichiers ne précisent pas le processeur, la RAM ou le GPU. Les mesures ne
doivent donc pas être généralisées à une autre machine sans nouveau benchmark.

Les tailles disque des datasets et la consommation maximale de mémoire ne sont
pas enregistrées dans les rapports JSON actuels.

## MauriPay-S — 10 000 lignes

Dataset : `data/generated/mauripay_s_10k.csv`.

| Mesure | Valeur |
|---|---:|
| Lignes | 10 000 |
| Transactions normales | 9 320 |
| Anomalies | 680 |
| Temps de chargement JSON enregistré | 0,128 s |
| Features autoencoder | 139 |
| `fit_transform` autoencoder | 25,299 s |
| `transform` autoencoder | 15,009 s |

Le rapport Markdown comparatif enregistre :

| Modèle | Précision | Rappel | F1 | ROC-AUC | Entraînement | Inférence | Alertes |
|---|---:|---:|---:|---:|---:|---:|---:|
| Isolation Forest | 0,6150 | 0,1809 | 0,2795 | 0,7913 | 0,5096 s | 0,3374 s | 200 |
| LOF | 0,2531 | 0,0603 | 0,0974 | 0,6839 | 3,5464 s | 1,8186 s | 162 |
| Autoencoder | 0,6954 | 0,7588 | 0,7257 | 0,9070 | 45,3932 s | 0,1540 s | 742 |

Le fichier JSON `full_10k_benchmark.json` actuellement présent ne contient que
le résultat autoencoder, alors que le rapport Markdown contient les trois
mesures. Il faut régénérer le benchmark pour obtenir un JSON comparatif complet
et cohérent.

Commande :

```bash
python benchmarks/run_benchmark.py \
  --benchmark full_10k \
  --data data/generated/mauripay_s_10k.csv \
  --output benchmarks/results/full_10k_benchmark.json \
  --threshold-percentile 98
```

## MauriPay-M — 100 000 lignes

Dataset : `data/generated/mauripay_m_100k.csv`.

| Mesure | Valeur |
|---|---:|
| Lignes | 100 000 |
| Transactions normales | 93 452 |
| Anomalies | 6 548 |
| Chargement | 0,917 s |
| Features classiques | 140 |
| `fit_transform` classique | 60,917 s |
| Features autoencoder | 139 |
| `fit_transform` autoencoder | 54,802 s |
| `transform` autoencoder | 31,948 s |

| Modèle | Précision | Rappel | F1 | ROC-AUC | Entraînement | Inférence | Alertes |
|---|---:|---:|---:|---:|---:|---:|---:|
| Isolation Forest | 0,9155 | 0,2796 | 0,4284 | 0,9108 | 1,909 s | 2,620 s | 2 000 |
| LOF | 0,1323 | 0,0350 | 0,0553 | 0,4777 | 117,392 s | 180,366 s | 1 731 |
| Autoencoder | 0,6145 | 0,8083 | 0,6982 | 0,9280 | 174,338 s | 0,378 s | 8 614 |

Commande :

```bash
python benchmarks/run_benchmark.py --benchmark full_100k
```

Ces temps de modèle excluent le chargement et le feature engineering, qui sont
mesurés séparément.

## MauriPay-L — 1 000 000 lignes

Le runner prévoit le scénario :

```bash
python benchmarks/run_benchmark.py --benchmark full_1m
```

Dataset par défaut : `data/generated/mauripay_l_1m.parquet`.

Aucun fichier `full_1m_benchmark.json` n’est actuellement présent. Il ne faut
donc pas publier de temps ou de métriques 1M sans exécuter ce benchmark. LOF et
l’autoencoder peuvent demander beaucoup de temps et de mémoire à cette échelle.

## Définition des métriques

| Métrique | Interprétation |
|---|---|
| Précision | Part des alertes qui correspondent réellement à une anomalie |
| Rappel | Part des anomalies réelles effectivement détectées |
| F1-score | Moyenne harmonique de la précision et du rappel |
| Accuracy | Part totale des prédictions correctes |
| ROC-AUC | Capacité du score à classer les anomalies au-dessus des normales |
| Matrice de confusion | Comptage des vrais/faux positifs et vrais/faux négatifs |

La matrice utilisée suit la forme :

```text
[[vrais négatifs, faux positifs],
 [faux négatifs, vrais positifs]]
```

L’accuracy peut sembler élevée sur un dataset très déséquilibré même si le
rappel des anomalies est faible. La précision, le rappel, le F1 et la matrice de
confusion doivent donc être examinés ensemble.

## Limitation d’évaluation

Les métadonnées des modèles fournis indiquent `test_size=0`. Dans ce mode, les
données utilisées pour l’entraînement servent également à l’évaluation. Les
métriques peuvent donc être optimistes et ne mesurent pas correctement la
généralisation à de nouvelles transactions.

Pour une validation plus solide, il faut utiliser un jeu d’évaluation
indépendant, par exemple :

```bash
python -m mauripay.detection.train \
  --data data/generated/mauripay_s_10k.csv \
  --test-size 0.2
```

Une séparation temporelle est encore plus pertinente pour éviter que des
transactions futures influencent l’apprentissage du comportement passé.
