# Modèles de détection

MauriPay-Analytics combine trois détecteurs d’anomalies non supervisés avec des
règles métier. Ils recherchent des comportements inhabituels et ne prouvent
pas, à eux seuls, qu’une fraude a eu lieu.

## Isolation Forest

Isolation Forest construit des arbres de séparation aléatoires. Une
transaction rare est généralement isolée avec moins de divisions qu’une
transaction située dans une zone dense.

| Paramètre | Rôle | Valeur par défaut du pipeline |
|---|---|---:|
| `n_estimators` | Nombre d’arbres | `100` |
| `contamination` | Proportion estimée d’anomalies | `0.02` |
| `max_samples` | Nombre de lignes utilisées par arbre | `auto` |
| `random_state` | Reproductibilité | `42` |

Isolation Forest convient aux grands volumes et fournit un score pour chaque
transaction.

## Local Outlier Factor

LOF compare la densité locale d’une transaction à celle de ses voisines. Une
transaction située dans une zone beaucoup moins dense est considérée comme
atypique.

| Paramètre | Rôle | Valeur par défaut du pipeline |
|---|---|---:|
| `n_neighbors` | Nombre de voisins comparés | `20` |
| `contamination` | Proportion estimée d’anomalies | `0.02` |
| `metric` | Mesure de distance | `minkowski` |
| `novelty` | Autorise la prédiction sur de nouvelles données | `true` |

L’entraînement LOF est limité par défaut à 20 000 lignes dans le pipeline
afin de contrôler son coût en temps et en mémoire.

## Autoencoder

L’autoencoder est un réseau neuronal PyTorch entraîné à reconstruire les
transactions normales :

```text
Entrée → couches cachées → représentation compressée → reconstruction
```

Une forte erreur de reconstruction indique que la transaction s’éloigne des
structures apprises.

| Paramètre | Rôle | Valeur usuelle des modèles fournis |
|---|---|---:|
| `hidden_dims` | Dimensions des couches cachées | `[32, 16]` |
| `encoding_dim` | Taille de la représentation compressée | `8` |
| `learning_rate` | Vitesse d’apprentissage | `0.001` |
| `epochs` | Nombre de passages sur les données | `50` |
| `batch_size` | Taille des lots | `128` |
| `threshold_percentile` | Percentile initial des erreurs normales | `98` par défaut CLI |
| `device` | Matériel de calcul | CPU ou CUDA |

Le pipeline d’entraînement filtre les lignes marquées normales lorsque la
colonne de label est disponible. Son apprentissage est donc non supervisé sur
les features, avec une assistance des labels pour constituer le jeu normal et,
si activé, optimiser le seuil.

## Scores, seuils et labels

```text
anomaly_score → niveau de suspicion calculé par le détecteur
threshold     → frontière utilisée pour prendre une décision
anomaly_label → décision finale : 0 normale, 1 suspecte
```

Les scores bruts des trois modèles ne sont pas nécessairement sur la même
échelle. Un score de `0.8` produit par un modèle ne doit donc pas être
interprété comme identique à `0.8` produit par un autre.

Pour l’autoencoder, le score est fondé sur l’erreur de reconstruction. Pour les
modèles classiques, le score dérive de leur fonction de décision. Les règles
métier peuvent ensuite augmenter le score et faire passer le label à `1`.

## Ensemble

L’ensemble exige les prédictions des trois modèles et applique la règle :

```text
(Isolation Forest = 1 ET LOF = 1)
OU
(Autoencoder = 1 ET Isolation Forest = 0 ET LOF = 0)
```

Il conserve aussi :

- le label et le score de chaque modèle ;
- `ensemble_vote_count`, nombre de votes positifs ;
- `classical_consensus_label` ;
- `autoencoder_only_label` ;
- la moyenne des trois scores comme `anomaly_score` de l’ensemble.

## Règles métier

`business_rules.py` ajoute des motifs interprétables :

| Motif | Exemple de raison enregistrée |
|---|---|
| Montant élevé | `high_amount_type_limit` ou `high_amount_sender_profile` |
| Échec sans frais | `failed_zero_fee` |
| Forte fréquence | `high_frequency_burst` |
| Fractionnement | `structuring_pattern` |
| Panne d’opérateur | `operator_outage_cluster` |
| Localisation inhabituelle | `unusual_remote_location` |
| Profil géographique incohérent | `receiver_profile_location_mismatch` |

Les raisons sont concaténées dans `business_rule_reasons`. Une règle peut
ajouter une anomalie, mais elle ne retire jamais une anomalie détectée par le
modèle.

## Entraîner et prédire

Depuis `backend/`, avec le package accessible :

```bash
python -m mauripay.detection.train \
  --data ../data/generated/mauripay_s_10k.csv \
  --include-autoencoder
```

```bash
python -m mauripay.detection.predict \
  --model isolation_forest \
  --data ../data/generated/mauripay_s_10k.csv
```

Les artefacts sont sauvegardés dans `backend/models/` et les rapports dans
`backend/outputs/`.
