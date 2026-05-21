# Benchmarks

Benchmarks reproductibles hors tests unitaires.

## Parquet 1M

Depuis la racine du projet :

```powershell
$env:PYTHONPATH="backend/src"
python benchmarks/parquet_1m_benchmark.py
```

Par defaut, le script genere `data/generated/mauripay_l_1m.parquet` s'il
n'existe pas, lit le fichier avec l'adaptateur Parquet, puis construit le
DataFrame ML avec `build_features`.

Pour un test rapide :

```powershell
$env:PYTHONPATH="backend/src"
python benchmarks/parquet_1m_benchmark.py --rows 10000 --output data/generated/benchmark_10k.parquet
```
