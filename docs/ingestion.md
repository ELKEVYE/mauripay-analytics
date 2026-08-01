# Ingestion

Le module d’ingestion lit les fichiers de transactions, normalise les valeurs
vides et valide chaque ligne avec le schéma Pydantic `Transaction`.

## Formats acceptés

| Format | Extension | Structure attendue |
|---|---|---|
| CSV | `.csv` | Une ligne d’en-tête puis une transaction par ligne |
| JSON | `.json` | Liste d’objets ou objet contenant une liste `transactions` |
| JSON Lines | `.jsonl` | Un objet JSON par ligne non vide |
| Parquet | `.parquet` | Table Parquet contenant les colonnes du schéma |

L’extension du fichier permet au chargeur de choisir automatiquement
l’adaptateur.

## Adaptateurs

Les fichiers se trouvent dans `backend/src/mauripay/ingestion/`.

| Fichier | Rôle |
|---|---|
| `csv_adapter.py` | Lecture CSV en UTF-8 avec `csv.DictReader` |
| `json_adapter.py` | Lecture JSON et JSONL |
| `parquet_adapter.py` | Lecture Parquet par lots avec PyArrow, avec repli sur Pandas |
| `loader.py` | Sélection de l’adaptateur selon l’extension |
| `common.py` | Normalisation, validation commune et objets de résultat |
| `schema.py` | Modèle Pydantic `Transaction` et règles métier |

## Charger un fichier en Python

Depuis la racine du projet, après l’installation du backend :

```python
from mauripay.ingestion.loader import load_transactions

result = load_transactions(
    "data/generated/mauripay_s_10k.csv",
    report=True,
)

print(result.total_rows)
print(result.valid_rows)
print(result.invalid_rows)
```

Avec `report=True`, la fonction renvoie un `IngestionResult` contenant :

- `transactions` : objets Pydantic valides ;
- `errors` : erreurs associées aux lignes invalides ;
- `total_rows` : nombre total de lignes examinées ;
- `valid_rows` : nombre de transactions valides ;
- `invalid_rows` : nombre de transactions invalides ;
- `ok` : `true` lorsqu’aucune erreur n’a été rencontrée.

Sans rapport :

```python
transactions = load_transactions("transactions.csv")
```

La fonction renvoie directement la liste des transactions. Si une ligne est
invalide, elle lève une erreur à partir de la première erreur rencontrée.

## Validation ligne par ligne

Pour chaque enregistrement, le pipeline :

1. transforme les valeurs vides, `nan` et `null` en `None` lorsque cela est
   pertinent ;
2. appelle `Transaction.model_validate(payload)` ;
3. ajoute la transaction à la liste valide si la validation réussit ;
4. conserve le numéro de ligne, les erreurs Pydantic et le contenu original si
   la validation échoue.

Une ligne invalide n’empêche donc pas la validation des lignes suivantes quand
`report=True`.

## Rapport d’erreurs de l’API

L’endpoint `POST /ingest` sauvegarde le fichier dans `data/uploads/`, avec un
suffixe aléatoire pour éviter les collisions. Il renvoie par exemple :

```json
{
  "rows": 10000,
  "valid_rows": 9998,
  "invalid_rows": 2,
  "dataset_path": "data/uploads/transactions_a1b2c3d4.csv",
  "errors_file": "outputs/transactions_a1b2c3d4_ingestion_errors.json"
}
```

Le rapport JSON contient, pour chaque erreur :

- le fichier source ;
- le numéro de ligne ;
- les messages Pydantic ;
- les données de la ligne.

Le fichier chargé est conservé même si certaines lignes sont invalides. Le
dashboard refuse toutefois de lancer la prédiction lorsqu’il reçoit un nombre
de lignes invalides supérieur à zéro.

## Formats non acceptés

L’API refuse notamment `.xlsx`, `.txt`, `.xml` et toute extension inconnue avec
une réponse HTTP `400`. En Python, `load_transactions()` lève une `ValueError`
pour une extension non prise en charge et une `FileNotFoundError` si le fichier
n’existe pas.
