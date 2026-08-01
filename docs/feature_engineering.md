# Feature engineering

Le feature engineering transforme les transactions lisibles par un humain en
une matrice numérique exploitable par Isolation Forest, LOF et l’autoencoder.

## Organisation des fichiers

| Fichier | Rôle |
|---|---|
| `features/temporal.py` | Temps, fréquence, fenêtres glissantes et historique |
| `features/geographic.py` | Codes des wilayas et distances |
| `features/risk_signals.py` | Signaux de risque métier |
| `features/encoding.py` | Encodage manuel des catégories |
| `features/scaling.py` | Normalisation Min-Max et Z-score |
| `features/engineering.py` | Assemblage générique du pipeline |
| `detection/features.py` | Préprocesseur sauvegardé utilisé par l’entraînement et la prédiction |

Le pipeline des modèles utilise principalement la classe
`TransactionFeatureEngineer` de `detection/features.py`. Elle réutilise les
couches temporelles, géographiques et de risque, puis applique un
`ColumnTransformer` scikit-learn.

## Features temporelles

| Feature | Signification |
|---|---|
| `hour` | Heure de la transaction, de 0 à 23 |
| `is_night` | `1` entre 00:00 et 04:59 |
| `tx_gap_seconds` | Secondes depuis la transaction précédente du même expéditeur |
| `tx_count_5min` | Nombre de transactions de l’expéditeur sur cinq minutes |
| `tx_count_1h` | Nombre de transactions sur une heure |

Le projet calcule aussi des statistiques sur 5 minutes, 10 minutes, 1 heure,
24 heures et 7 jours : nombre, somme, moyenne et écart-type des montants.

## Features financières

| Feature | Signification |
|---|---|
| `amount` | Montant original |
| `amount_log` | `log(1 + amount)`, qui réduit l’effet des très grands montants |
| `amount_mean_7d` | Moyenne des montants de l’expéditeur sur sept jours |
| `amount_zscore_sender_7d` | Écart du montant par rapport à l’historique de l’expéditeur |

D’autres ratios comparent le montant actuel aux moyennes et volumes sur
24 heures ou sept jours.

## Features géographiques

| Feature | Signification |
|---|---|
| `is_cross_wilaya` | Expéditeur et destinataire dans des wilayas différentes |
| `wilaya_distance_km` | Distance approximative entre les centres administratifs |
| `sender_receiver_is_new_wilaya` | Wilaya jamais observée auparavant pour cet expéditeur |

Les coordonnées sont des centres approximatifs destinés aux features ML ;
elles ne constituent pas un système GPS ou de routage.

## Features comportementales

Le projet mesure notamment :

- si le bénéficiaire est nouveau ;
- si le bénéficiaire est rare dans l’historique ;
- le nombre de bénéficiaires récents ;
- les montants entrants et sortants sur 24 heures ;
- le rapport entre flux entrant et sortant ;
- la fréquence des changements de wilaya ;
- l’activité récente du destinataire.

## Signaux métier

| Feature | Signification |
|---|---|
| `failed_zero_fee_signal` | Transaction `FAILED` avec frais nuls |
| `structuring_signal` | Transferts multiples aux montants proches |
| `high_frequency_signal` | Au moins 10 transactions en 1 h ou 4 en 5 min |

Ces signaux sont fournis aux modèles comme caractéristiques. Ils sont
distincts des règles finales de `business_rules.py`, qui peuvent directement
ajouter une alerte après la prédiction.

## Encodage one-hot

Les modèles ne peuvent pas utiliser directement des valeurs comme `USSD` ou
`APP`. Le one-hot encoding crée une colonne binaire par catégorie :

```text
channel_USSD  channel_APP  channel_AGENT
      1            0              0
```

`TransactionFeatureEngineer` utilise `OneHotEncoder` et sait ignorer une
catégorie inconnue au moment de la prédiction.

## Standardisation et Min-Max

La standardisation transforme une valeur avec :

```text
z = (valeur - moyenne) / écart-type
```

Elle est appliquée par `StandardScaler` dans le préprocesseur des modèles. Elle
est particulièrement importante pour LOF et l’autoencoder.

Le module `features/scaling.py` propose aussi une normalisation Min-Max :

```text
x_normalisé = (x - minimum) / (maximum - minimum)
```

Elle place normalement les valeurs entre 0 et 1. Le builder générique de
`features/engineering.py` peut produire les deux variantes, mais le pipeline de
détection sauvegardé repose sur son propre `ColumnTransformer`.

## `fit`, `transform` et `fit_transform`

- `fit(données)` apprend les colonnes, catégories, moyennes et écarts-types ;
- `transform(données)` applique les transformations déjà apprises ;
- `fit_transform(données)` exécute les deux opérations sur les données
  d’entraînement.

Pendant la prédiction, il faut obligatoirement utiliser `transform` avec le
préprocesseur sauvegardé, afin de conserver les mêmes colonnes et la même
échelle qu’à l’entraînement.

Les préprocesseurs sont enregistrés dans :

```text
backend/models/preprocessor.joblib
backend/models/autoencoder_preprocessor.joblib
```

## Exclusion des labels

Les colonnes de cible et de vérité terrain sont exclues des entrées des
modèles, notamment :

```text
is_anomaly
anomaly_type
anomaly_label
label
target
fraud
is_fraud
```

Cette exclusion empêche une fuite de cible : le modèle ne doit pas recevoir la
réponse qu’il cherche à détecter. Les labels peuvent toutefois servir à
l’évaluation, à la sélection des lignes normales de l’autoencoder et à
l’optimisation d’un seuil.
