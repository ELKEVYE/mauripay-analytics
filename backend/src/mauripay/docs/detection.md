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

## FastAPI Integration

The project now includes a FastAPI backend that exposes the detection workflow
through API routes. From `mauripay-analytics/backend`, run:

```powershell
$env:PYTHONPATH="src"
uvicorn mauripay.api.main:app --reload
```

Useful detection endpoints:

- `GET /detect/models`: list trained model artifacts and metadata.
- `POST /detect/train`: train Isolation Forest, LOF, and optionally the
  Autoencoder.
- `POST /detect/predict`: run predictions with `isolation_forest`, `lof`,
  `autoencoder`, or `ensemble`.

The dashboard remains a future layer. It can consume the prediction CSV files
or call the FastAPI endpoints directly.

## Improvement Workflow

The detection layer now supports stronger behavior features, holdout evaluation,
per-anomaly-type metrics, and automatic tuning.

Stronger features include:

- `tx_count_5min`
- `tx_count_10min`
- `sender_unique_receivers_1h`
- `same_sender_receiver_count_1h`
- `similar_amount_count_1h`
- `amount_vs_sender_avg_7d`

Train with a real holdout split:

```powershell
python -m mauripay.detection.train --data data/generated/test_10k.csv --contamination 0.068 --test-size 0.3
```

Tune IF/LOF settings automatically:

```powershell
python -m mauripay.detection.tune --data data/generated/test_10k.csv --test-size 0.3
```

Tuning saves:

- `backend/outputs/tuning_results.csv`
- `backend/outputs/tuning_summary.json`

Evaluation JSON files now include global metrics and, when `anomaly_type` exists,
metrics grouped by anomaly family.
