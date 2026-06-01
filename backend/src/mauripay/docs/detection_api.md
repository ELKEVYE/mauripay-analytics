# Detection API

This API exposes the current anomaly detection backend for Isolation Forest and LOF.
It does not include Autoencoder yet. Autoencoder can be added later by extending the
model registry and keeping the same endpoint shape.

## Run the API

From `backend/`:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
uvicorn mauripay.api.app:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Endpoints

### GET /detect/models

Returns available algorithms, trained model status, and metadata.

Current algorithms:

```text
isolation_forest
lof
```

### POST /detect/train

Trains Isolation Forest and LOF from a dataset path.

Example body:

```json
{
  "data_path": "data/generated/new_10k.csv",
  "contamination": 0.068,
  "n_estimators": 100,
  "n_neighbors": 50,
  "metric": "manhattan",
  "test_size": 0.0
}
```

Outputs are saved in:

```text
backend/models/
backend/outputs/
```

### POST /detect/predict

Runs one trained detector on a dataset.

Example body:

```json
{
  "algorithm": "isolation_forest",
  "data_path": "data/generated/new_10k.csv",
  "output_path": "outputs/api_predictions_isolation_forest.csv"
}
```

Response includes row count, anomaly count, output path, and a small preview.

## Future Autoencoder Integration

When Autoencoder is ready, add it in:

```text
backend/src/mauripay/detection/model_registry.py
```

Then update the API algorithm type in:

```text
backend/src/mauripay/api/routes/detect.py
```

The API shape can stay the same:

```text
POST /detect/train
POST /detect/predict
GET /detect/models
```
