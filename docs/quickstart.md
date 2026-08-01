# Démarrage rapide

Ce guide suppose que les dépendances décrites dans le
{doc}`installation` sont déjà installées. Ouvrez deux terminaux à la racine
du dépôt.

## Terminal 1 : démarrer le backend

Activez d’abord votre environnement virtuel si nécessaire.

Après l’installation éditable du package avec `pip install -e backend` :

```bash
uvicorn mauripay.api.main:app --reload
```

Sous Windows, si la commande `uvicorn` n’est pas disponible dans le `PATH` :

```powershell
python -m uvicorn mauripay.api.main:app --reload
```

Le backend est alors accessible aux adresses suivantes :

| Service | Adresse |
|---|---|
| API | <http://127.0.0.1:8000> |
| Swagger UI | <http://127.0.0.1:8000/docs> |
| Schéma OpenAPI | <http://127.0.0.1:8000/openapi.json> |

Swagger permet d’examiner et de tester les endpoints directement depuis le
navigateur.

### Alternative sans installation éditable

Sous Windows PowerShell :

```powershell
cd backend
$env:PYTHONPATH="src"
python -m uvicorn mauripay.api.main:app --reload
```

Sous Linux ou macOS :

```bash
cd backend
PYTHONPATH=src python -m uvicorn mauripay.api.main:app --reload
```

Revenez à la racine avant d’exécuter les autres commandes :

```bash
cd ..
```

## Terminal 2 : démarrer le frontend

Vérifiez que `VITE_API_BASE_URL` pointe vers le backend, puis lancez Vite :

```bash
cd frontend
npm run dev
```

Sous Windows PowerShell, utilisez `npm.cmd run dev` si `npm.ps1` est bloqué :

```powershell
cd frontend
npm.cmd run dev
```

Le dashboard est disponible à l’adresse :

<http://localhost:5173>

## Premier scénario utilisateur

1. Ouvrez <http://localhost:5173> dans un navigateur.
2. Vérifiez que l’interface indique que l’API est accessible.
3. Sur le dashboard, sélectionnez un dataset CSV, JSON, JSONL ou Parquet
   respectant le {doc}`data_schema`.
4. Lancez l’analyse. Le fichier est chargé et validé par l’API.
5. Attendez l’exécution d’Isolation Forest, LOF, de l’autoencoder et de
   l’ensemble. La durée dépend de la taille du dataset.
6. Consultez les cartes du dashboard : transactions, montant total, consensus
   des modèles et taux d’échec.
7. Ouvrez les vues temporelles, opérationnelles et géographiques.
8. Ouvrez « Transactions suspectes » pour examiner les alertes, utiliser les
   filtres et afficher le détail d’une transaction.

Les modèles préentraînés doivent être présents dans `backend/models/`. Si un
modèle manque, l’endpoint de prédiction renvoie une erreur indiquant le fichier
absent.

## Arrêter l’application

Dans chacun des deux terminaux, utilisez :

```text
Ctrl+C
```
