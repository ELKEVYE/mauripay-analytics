# MauriPay Detection Integration

This module connects the synthetic transaction pipeline with three anomaly
detection baselines:

- Isolation Forest
- Local Outlier Factor with `novelty=True`
- PyTorch Autoencoder

The implementation lives in `backend/src/mauripay/detection/`.

Current detector slots:

- `iforest.py`: implemented Isolation Forest baseline.
- `lof.py`: implemented LOF baseline with `novelty=True`.
- `autoencoder.py`: implemented encoder-decoder detector using reconstruction
  error as anomaly score.

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

To train the complete detector set from the main pipeline, add:

```powershell
python -m mauripay.detection.train `
  --data data/generated/mauripay_s_10k.csv `
  --include-autoencoder
```

This trains IF/LOF first, then trains the autoencoder on rows labelled as normal.
The option requires a label column such as `is_anomaly`.

Training saves:

- `backend/models/isolation_forest.joblib`
- `backend/models/lof.joblib`
- `backend/models/preprocessor.joblib`
- `backend/models/metadata.json`

If `--include-autoencoder` is enabled, it also saves:

- `backend/models/autoencoder.joblib`
- `backend/models/autoencoder_preprocessor.joblib`
- `backend/models/metadata_autoencoder.json`

If a label column exists, evaluation JSON files are saved in `backend/outputs/`.

## Train Autoencoder

The autoencoder can also be trained separately on rows labelled as normal, when
you want to tune it without retraining IF/LOF:

```powershell
$env:PYTHONPATH="src"
python -m mauripay.detection.train_autoencoder --data data/generated/mauripay_s_10k.csv
```

The main CLI exposes the same workflow:

```powershell
mauripay train-autoencoder --data data/generated/mauripay_s_10k.csv
```

Training saves:

- `backend/models/autoencoder.joblib`
- `backend/models/autoencoder_preprocessor.joblib`
- `backend/models/metadata_autoencoder.json`
- `backend/outputs/evaluation_autoencoder.json`
- `backend/outputs/autoencoder_error_analysis.json`

## Predict

```powershell
$env:PYTHONPATH="src"
python -m mauripay.detection.predict --model isolation_forest --data data/generated/mauripay_s_10k.csv
python -m mauripay.detection.predict --model lof --data data/generated/mauripay_s_10k.csv
python -m mauripay.detection.predict --model autoencoder --data data/generated/mauripay_s_10k.csv
```

Prediction outputs contain the original rows plus:

- `anomaly_label`
- `anomaly_score`
- `algorithm`

Autoencoder outputs also contain business-rule columns:

- `autoencoder_label`
- `business_rule_label`
- `business_rule_reasons`

Default output files are saved under `backend/outputs/`.

## Official Autoencoder Commands

Use these commands from `mauripay-analytics/backend` with:

```powershell
$env:PYTHONPATH="src"
```

Recommended full-pipeline workflow:

```powershell
python -m mauripay.detection.train `
  --data data/generated/mauripay_s_10k.csv `
  --include-autoencoder

python -m mauripay.detection.predict `
  --model autoencoder `
  --data data/generated/mauripay_s_10k.csv
```

Autoencoder-only tuning workflow:

```powershell
python -m mauripay.detection.train_autoencoder `
  --data data/generated/mauripay_s_10k.csv `
  --epochs 50 `
  --batch-size 128 `
  --threshold-percentile 98

python -m mauripay.detection.predict_autoencoder `
  --data data/generated/mauripay_s_10k.csv
```

Package CLI equivalents:

```powershell
mauripay train --data data/generated/mauripay_s_10k.csv --include-autoencoder
mauripay train-autoencoder --data data/generated/mauripay_s_10k.csv
mauripay predict --model autoencoder --data data/generated/mauripay_s_10k.csv
```

The official prediction entry point is `mauripay.detection.predict --model
autoencoder` or `mauripay predict --model autoencoder`. The
`predict_autoencoder` module remains available for autoencoder-specific options
such as `--threshold-percentile`.

## API And Dashboard Later

There is no FastAPI app in the Month 1 project yet. The detection module is
prepared for future API/dashboard work through stable saved artifacts and CSV
outputs. A future API can call `train_models()` and `predict_anomalies()` from
the CLI modules, and the dashboard can read the prediction CSV with transaction
fields plus anomaly results.
