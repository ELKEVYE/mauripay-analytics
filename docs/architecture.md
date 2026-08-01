# Architecture

MauriPay-Analytics est organisé en cinq couches. Chaque couche a une
responsabilité précise et communique avec la couche suivante.

```text
┌──────────────────────────────┐
│ 5. Interfaces                │
│ React, CLI, Swagger          │
├──────────────────────────────┤
│ 4. API                       │
│ FastAPI                      │
├──────────────────────────────┤
│ 3. Détection                 │
│ IF, LOF, Autoencoder, règles │
├──────────────────────────────┤
│ 2. Ingestion et features     │
│ Pydantic, Pandas, sklearn    │
├──────────────────────────────┤
│ 1. Données                   │
│ CSV, JSON, JSONL, Parquet    │
└──────────────────────────────┘
```

## 1. Couche données

Cette couche contient les données d’entrée et les artefacts produits :

| Emplacement | Contenu |
|---|---|
| `data/generated/` | Datasets synthétiques générés |
| `data/uploads/` | Fichiers chargés par l’API |
| `backend/models/` | Modèles et préprocesseurs entraînés |
| `backend/outputs/` | Prédictions, évaluations et rapports d’erreurs |

Les formats de transaction acceptés sont CSV, JSON, JSONL et Parquet. Les
modèles et préprocesseurs sont principalement enregistrés avec Joblib.

## 2. Couche ingestion et features

Le dossier `backend/src/mauripay/ingestion/` contient :

- le schéma Pydantic `Transaction` ;
- les adaptateurs CSV, JSON, JSONL et Parquet ;
- le chargeur qui sélectionne l’adaptateur à partir de l’extension ;
- les résultats et erreurs de validation.

Le dossier `backend/src/mauripay/features/` calcule les caractéristiques :

- temporelles et comportementales ;
- financières ;
- géographiques ;
- signaux de risque métier ;
- encodage des catégories ;
- normalisation numérique.

`backend/src/mauripay/detection/features.py` fournit le préprocesseur
`TransactionFeatureEngineer`, compatible avec l’entraînement et la prédiction.

## 3. Couche détection

Le dossier `backend/src/mauripay/detection/` contient :

- Isolation Forest (`iforest.py`) ;
- Local Outlier Factor (`lof.py`) ;
- l’autoencoder PyTorch (`autoencoder.py`) ;
- les commandes d’entraînement et de prédiction ;
- l’évaluation des modèles ;
- l’ensemble des trois détecteurs ;
- les règles métier.

Les modèles produisent un score d’anomalie et une étiquette `0` ou `1`. Les
règles métier peuvent ajouter une alerte, mais ne suppriment pas une alerte
déjà produite par un modèle.

## 4. Couche API

Le dossier `backend/src/mauripay/api/` expose les fonctionnalités avec
FastAPI :

- ingestion et génération ;
- entraînement et prédiction ;
- statistiques ;
- séries temporelles ;
- agrégations géographiques.

Les routes sont séparées dans `mauripay/api/routes/`. FastAPI génère également
le schéma OpenAPI et l’interface Swagger.

## 5. Couche interfaces

Les utilisateurs peuvent accéder au système de plusieurs manières :

| Interface | Emplacement ou adresse |
|---|---|
| CLI Python | `backend/src/mauripay/cli.py` |
| Dashboard React | `frontend/` |
| Swagger UI | `http://127.0.0.1:8000/docs` |
| API HTTP | `http://127.0.0.1:8000` |

Le frontend appelle l’API avec la fonction native `fetch`. Il affiche les
indicateurs, les graphiques, la carte et les transactions suspectes.

## Flux complet d’une analyse

```text
Fichier CSV, JSON, JSONL ou Parquet
                  ↓
        Validation Pydantic
                  ↓
         Feature engineering
                  ↓
   Isolation Forest + LOF + Autoencoder
                  ↓
       Règles métier et ensemble
                  ↓
       Fichiers de résultats CSV
                  ↓
 Stats + séries temporelles + géographie
                  ↓
               Dashboard
```

Dans le parcours du dashboard, le fichier est d’abord envoyé à `/ingest`.
L’endpoint `/detect/predict-all` exécute ensuite les modèles. Le frontend
utilise enfin `/stats`, `/timeseries` et `/geo` sur le fichier de prédiction
choisi pour construire les vues analytiques.
