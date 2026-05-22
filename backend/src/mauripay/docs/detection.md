# MauriPay Detection Integration

This module connects the Month 1 synthetic transaction pipeline with two anomaly
detection baselines:

- Isolation Forest
- Local Outlier Factor with `novelty=True`

The implementation lives in `backend/src/mauripay/detection/`.

Current detector slots:

- `iforest.py`: implemented Isolation Forest baseline.
- `lof.py`: implemented LOF baseline with `novelty=True`.
- `autoencoder.py`: reserved class for the third model, using the same detector
  interface so it can be added without changing the training workflow shape.

## Real Dataset Columns

The detector does not rely on a fixed CDC-era column list. During training,
`TransactionFeatureEngineer` inspects the actual input dataframe and:

- ignores identifiers such as `transaction_id`, `sender_id`, `receiver_id`, and
  any `*_id` field;
- ignores label/target columns such as `is_anomaly`, `anomaly_type`,
  `anomaly_label`, `label`, `target`, `fraud`, and `is_fraud`;
- detects timestamp/date columns and derives `hour`, `day_of_week`,
  `day_of_month`, `month`, and `is_weekend`;
- reuses the project `mauripay.features` layer when possible to add temporal,
  flow-ratio, and geographic context before identifier columns are removed;
- scales numerical features;
- one-hot encodes categorical features with unknown-category support.

For the current Month 1 generator, the useful raw columns are generally:

- numerical: `amount`, `fees`, `is_ramadan`, plus timestamp-derived fields;
- categorical: `currency`, `transaction_type`, `channel`, `operator`,
  `sender_wilaya`, `receiver_wilaya`, `status`, `bill_provider`,
  `origin_country`;
- labels for evaluation only: `is_anomaly`, `anomaly_type`.

## Train

From `mauripay-analytics/backend`:

```powershell
$env:PYTHONPATH="src"
python -m mauripay.detection.train --data data/generated/mauripay_s_10k.csv
```

Optional parameters:

```powershell
python -m mauripay.detection.train `
  --data data/generated/mauripay_s_10k.csv `
  --contamination 0.02 `
  --n-estimators 100 `
  --n-neighbors 20
```

Training saves:

- `backend/models/isolation_forest.joblib`
- `backend/models/lof.joblib`
- `backend/models/preprocessor.joblib`
- `backend/models/metadata.json`

If a label column exists, evaluation JSON files are saved in `backend/outputs/`.

## Predict

```powershell
$env:PYTHONPATH="src"
python -m mauripay.detection.predict --model isolation_forest --data data/generated/mauripay_s_10k.csv
python -m mauripay.detection.predict --model lof --data data/generated/mauripay_s_10k.csv
```

Prediction outputs contain the original rows plus:

- `anomaly_label`
- `anomaly_score`
- `algorithm`

Default output files are saved under `backend/outputs/`.

## API And Dashboard Later

There is no FastAPI app in the Month 1 project yet. The detection module is
prepared for future API/dashboard work through stable saved artifacts and CSV
outputs. A future API can call `train_models()` and `predict_anomalies()` from
the CLI modules, and the dashboard can read the prediction CSV with transaction
fields plus anomaly results.
