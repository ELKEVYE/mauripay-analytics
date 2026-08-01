# API

L’API FastAPI est disponible par défaut sur <http://127.0.0.1:8000>. Les
contrats Pydantic sont définis dans `mauripay/api/schemas.py`.

Documentation interactive :

- Swagger UI : <http://127.0.0.1:8000/docs> ;
- schéma OpenAPI : <http://127.0.0.1:8000/openapi.json>.

## Endpoints de santé

| Méthode | URL | Module contrôlé |
|---|---|---|
| GET | `/ingest/health` | Ingestion |
| GET | `/stats/health` | Statistiques |
| GET | `/timeseries/health` | Séries temporelles |
| GET | `/geo/health` | Géographie |

Exemple :

```bash
curl http://127.0.0.1:8000/ingest/health
```

Réponse :

```json
{"status": "ready", "module": "ingest"}
```

## `POST /ingest`

Charge un fichier CSV, JSON, JSONL ou Parquet et valide toutes ses lignes.

Le corps est de type `multipart/form-data` avec un champ `file` :

```bash
curl -X POST http://127.0.0.1:8000/ingest \
  -F "file=@transactions.csv"
```

Réponse :

```json
{
  "rows": 10000,
  "valid_rows": 10000,
  "invalid_rows": 0,
  "dataset_path": "data/uploads/transactions_a1b2c3d4.csv",
  "errors_file": null
}
```

Erreurs principales : `400` pour un format non pris en charge ou une erreur de
lecture, `422` si le champ `file` manque.

## `POST /ingest/generate`

Génère et sauvegarde un dataset synthétique.

```bash
curl -X POST http://127.0.0.1:8000/ingest/generate \
  -H "Content-Type: application/json" \
  -d '{"rows":10000,"output_path":"data/generated/api_generated_10k.csv","seed":42}'
```

Champs principaux : `rows` (1 à 1 000 000), `output_path`, `accounts`,
`start_date`, `end_date`, `seed`, `anomaly_rate`, `tontine_rate`,
`structuring_rate` et `high_frequency_rate`.

La réponse contient `status`, `rows`, `output_path` et des statistiques. Une
valeur invalide produit `422`; une erreur de génération produit `400`.

## `GET /detect/models`

Liste les algorithmes, indique quels artefacts sont disponibles et retourne les
métadonnées d’entraînement.

```bash
curl http://127.0.0.1:8000/detect/models
```

La réponse contient `available_algorithms`, `models` et `metadata`.

## `POST /detect/predict`

Exécute un algorithme sur un dataset.

```bash
curl -X POST http://127.0.0.1:8000/detect/predict \
  -H "Content-Type: application/json" \
  -d '{"algorithm":"isolation_forest","data_path":"data/generated/mauripay_s_10k.csv"}'
```

Algorithmes autorisés : `isolation_forest`, `lof`, `autoencoder` et
`ensemble`. `output_path` et `model_dir` sont facultatifs.

La réponse fournit notamment le nombre de lignes, le nombre d’anomalies, le
chemin du CSV produit, une évaluation si un label est disponible et un aperçu
des alertes.

`POST /detect` est un alias de compatibilité qui accepte le même corps et
renvoie la même structure.

Erreurs principales : `404` si le dataset ou le modèle est absent, `403` pour
un chemin hors des répertoires autorisés, `400` pour une erreur de prédiction,
`422` pour un corps invalide.

## `POST /detect/predict-all`

Exécute Isolation Forest, LOF, l’autoencoder puis l’ensemble.

```bash
curl -X POST http://127.0.0.1:8000/detect/predict-all \
  -H "Content-Type: application/json" \
  -d '{"data_path":"data/generated/mauripay_s_10k.csv"}'
```

Sous `cmd.exe`, l’échappement peut s’écrire :

```bat
curl -X POST http://127.0.0.1:8000/detect/predict-all -H "Content-Type: application/json" -d "{\"data_path\":\"data/generated/mauripay_s_10k.csv\"}"
```

Réponse simplifiée :

```json
{
  "status": "predicted",
  "data_path": "data/generated/mauripay_s_10k.csv",
  "results": [
    {
      "algorithm": "isolation_forest",
      "total_transactions": 10000,
      "anomalies_detected": 200,
      "output_path": "outputs/mauripay_s_10k_isolation_forest.csv",
      "preview": []
    }
  ]
}
```

L’endpoint exige les trois modèles et les préprocesseurs correspondants. Un
artefact absent produit `404`.

## `POST /detect/train`

Entraîne Isolation Forest et LOF, avec l’autoencoder en option.

```bash
curl -X POST http://127.0.0.1:8000/detect/train \
  -H "Content-Type: application/json" \
  -d '{"data_path":"data/generated/mauripay_s_10k.csv","test_size":0.2,"include_autoencoder":true}'
```

Les paramètres couvrent la contamination, le nombre d’arbres, les voisins LOF,
la séparation d’évaluation, la limite de lignes LOF et les hyperparamètres de
l’autoencoder. La réponse contient les algorithmes entraînés et toutes les
métadonnées. Un dataset absent produit `404`; une erreur d’entraînement
produit `400`.

## `GET /stats`

Paramètre obligatoire : `dataset_path`.

```bash
curl "http://127.0.0.1:8000/stats?dataset_path=data%2Fgenerated%2Fmauripay_s_10k.csv"
```

La réponse contient : `total_transactions`, `total_amount`, `average_amount`,
`anomalies_count`, `failure_rate`, `by_type` et `by_channel`.

La colonne `amount` est obligatoire. Un fichier absent produit `404` et une
colonne obligatoire absente produit `400`.

## `GET /timeseries`

```bash
curl "http://127.0.0.1:8000/timeseries?dataset_path=data%2Fgenerated%2Fmauripay_s_10k.csv"
```

La réponse contient les transactions et montants par jour, les montants et
anomalies par heure, les anomalies par semaine, la heatmap horaire, ainsi que
les volumes par opérateur et par wilaya. Les colonnes `timestamp` et `amount`
sont obligatoires.

## `GET /geo`

```bash
curl "http://127.0.0.1:8000/geo?dataset_path=data%2Fgenerated%2Fmauripay_s_10k.csv"
```

La réponse contient, pour chaque wilaya, le nombre de transactions, le montant
total, le nombre d’anomalies et le taux d’échec. En l’absence de colonnes de
wilaya, la liste `wilayas` est vide.

## Accès aux fichiers

Pour limiter la lecture et l’écriture arbitraires, l’API autorise par défaut le
dossier `backend/` et le dossier racine `data/`. Des chemins supplémentaires
peuvent être déclarés avec `MAURIPAY_API_ALLOWED_ROOTS`. Un chemin hors de ces
racines produit une réponse HTTP `403`.
