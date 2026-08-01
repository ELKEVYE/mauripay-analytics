# MauriPay-Analytics

MauriPay-Analytics est une plateforme d’analyse de transactions
Mobile Money adaptée au contexte mauritanien et ouest-africain.

Elle permet :

- de générer des transactions synthétiques ;
- d’ingérer des fichiers CSV, JSON, JSONL et Parquet ;
- de valider les transactions avec Pydantic ;
- de calculer des caractéristiques métier ;
- de détecter les anomalies avec trois modèles ;
- de consulter les résultats dans une API et un dashboard.

```{toctree}
:maxdepth: 2
:caption: Documentation

installation
quickstart
architecture
data_schema
synthetic_generator
ingestion
feature_engineering
detection_models
api
dashboard
benchmarks
```
