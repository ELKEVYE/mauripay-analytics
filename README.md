---
title: MauriPay-Analytics
emoji: 💳
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# MauriPay-Analytics

## Présentation

MauriPay-Analytics est une plateforme open source d’analyse de transactions
Mobile Money adaptée au contexte mauritanien et ouest-africain. Elle permet de
générer et d’ingérer des transactions, de calculer des indicateurs métier et de
détecter les comportements inhabituels avec plusieurs modèles.

Le projet comprend un backend FastAPI, un pipeline de détection Python et un
dashboard React.

## Fonctionnalités

- schéma de transaction et validation avec Pydantic v2 ;
- ingestion CSV, JSON, JSONL et Parquet ;
- génération de transactions synthétiques reproductibles ;
- patterns mauritaniens : Ramadan, salaires, diaspora, factures et tontines ;
- feature engineering temporel, financier, comportemental et géographique ;
- Isolation Forest, Local Outlier Factor et autoencoder PyTorch ;
- ensemble des trois modèles et règles métier interprétables ;
- API de statistiques, séries temporelles et agrégations géographiques ;
- dashboard React avec graphiques, carte et liste des transactions suspectes ;
- benchmarks sur plusieurs tailles de datasets.

## Architecture

MauriPay-Analytics est organisé en cinq couches :

```text
Données
   ↓
Ingestion et feature engineering
   ↓
Détection d’anomalies
   ↓
API FastAPI
   ↓
CLI, Swagger et dashboard React
```

Les principaux dossiers sont :

```text
backend/      API, ingestion, génération et détection
frontend/     dashboard React et TypeScript
data/         datasets générés et fichiers chargés
tests/        tests Python
benchmarks/   scripts et résultats de performance
docs/         documentation Sphinx et MyST
```

## Installation rapide

Prérequis : Python 3.10 ou supérieur, Node.js 18 ou supérieur, npm et Git.

```bash
git clone https://github.com/mauripay-analytics-teams/mauripay-analytics.git
cd mauripay-analytics
python -m pip install -e backend
cd frontend
npm install
cd ..
```

Pour installer les outils de test et de documentation :

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -r docs/requirements.txt
```

## Démarrage

Dans un premier terminal, depuis la racine :

```bash
uvicorn mauripay.api.main:app --reload
```

Sous Windows, si `uvicorn` n’est pas dans le `PATH` :

```powershell
python -m uvicorn mauripay.api.main:app --reload
```

L’API et Swagger sont disponibles sur :

- API : <http://127.0.0.1:8000> ;
- Swagger : <http://127.0.0.1:8000/docs>.

Dans un deuxième terminal :

```bash
cd frontend
npm run dev
```

Le dashboard est disponible sur <http://localhost:5173>.

## Documentation

La documentation technique complète se trouve dans [`docs/`](docs/index.md).

Construction locale :

```bash
python -m sphinx -W --keep-going -b html docs docs/_build/html
```

Ouvrez ensuite `docs/_build/html/index.html` dans un navigateur.

La documentation Read the Docs sera ajoutée ici dès que le projet aura été
importé et que sa première construction en ligne aura réussi.

## Tests

Tests backend :

```bash
cd backend
python -m pytest -q
```

Tests et build du frontend :

```bash
cd frontend
npm test
npm run build
```

Build strict de la documentation :

```bash
python -m sphinx -W --keep-going -b html docs docs/_build/html
```

## Licence

Le package backend déclare la licence MIT dans `backend/pyproject.toml`.
