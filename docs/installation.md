# Installation

Ce guide explique comment préparer un environnement local pour le backend,
le frontend, les tests et la documentation de MauriPay-Analytics.

## Prérequis

- Python 3.10 ou supérieur ;
- Node.js 18 ou supérieur ;
- npm ;
- Git.

Vérifiez les versions installées :

```bash
python --version
node --version
npm --version
git --version
```

## Cloner le dépôt

```bash
git clone https://github.com/mauripay-analytics-teams/mauripay-analytics.git
cd mauripay-analytics
```

Toutes les commandes suivantes, sauf indication contraire, sont exécutées
depuis la racine `mauripay-analytics/`.

## Créer un environnement Python

L’utilisation d’un environnement virtuel permet d’isoler les dépendances du
projet de celles installées globalement sur la machine.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Si PowerShell refuse l’activation à cause de sa politique d’exécution, vous
pouvez l’autoriser uniquement pour le processus courant :

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Linux ou macOS

```bash
python -m venv .venv
source .venv/bin/activate
```

Une fois l’environnement activé, le préfixe `(.venv)` apparaît généralement
dans le terminal.

## Installer le backend

Mettez `pip` à jour, puis installez le package backend en mode éditable :

```bash
python -m pip install --upgrade pip
python -m pip install -e backend
```

L’option `-e` permet de prendre en compte les modifications du code Python sans
réinstaller le package après chaque changement.

### Dépendances de test et de documentation

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -r docs/requirements.txt
```

Vérifiez l’installation de Sphinx :

```bash
python -m sphinx --version
```

L’utilisation de `python -m sphinx` est recommandée sous Windows lorsque
`sphinx-build` n’est pas présent dans la variable `PATH`.

## Installer le frontend

```bash
cd frontend
npm install
cd ..
```

La commande lit `frontend/package.json` et installe les dépendances dans
`frontend/node_modules/`.

Sous Windows PowerShell, si l’exécution de `npm.ps1` est bloquée, utilisez :

```powershell
cd frontend
npm.cmd install
cd ..
```

## Variables d’environnement

Les principales variables de configuration sont :

| Variable | Utilisation | Valeur locale habituelle |
|---|---|---|
| `VITE_API_BASE_URL` | Adresse du backend utilisée par React | `http://127.0.0.1:8000` |
| `MAURIPAY_CORS_ORIGINS` | Origines autorisées à appeler FastAPI | `http://127.0.0.1:5173,http://localhost:5173` |
| `MAURIPAY_API_ALLOWED_ROOTS` | Répertoires supplémentaires accessibles par les endpoints utilisant un chemin de dataset | Vide par défaut |

Par défaut, le backend autorise déjà ses propres répertoires ainsi que le
dossier `data/` situé à la racine du projet. Il n’est donc généralement pas
nécessaire de définir `MAURIPAY_API_ALLOWED_ROOTS` pour une utilisation locale.

### Exemple Windows PowerShell

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
$env:MAURIPAY_CORS_ORIGINS="http://127.0.0.1:5173,http://localhost:5173"
```

Pour autoriser un répertoire de datasets supplémentaire :

```powershell
$env:MAURIPAY_API_ALLOWED_ROOTS="D:\datasets"
```

Plusieurs chemins doivent être séparés par un point-virgule sous Windows :

```powershell
$env:MAURIPAY_API_ALLOWED_ROOTS="D:\datasets;E:\archives"
```

### Exemple Linux ou macOS

```bash
export VITE_API_BASE_URL="http://127.0.0.1:8000"
export MAURIPAY_CORS_ORIGINS="http://127.0.0.1:5173,http://localhost:5173"
export MAURIPAY_API_ALLOWED_ROOTS="/home/user/datasets:/mnt/archives"
```

Sous Linux et macOS, plusieurs chemins autorisés sont séparés par `:`.

`VITE_API_BASE_URL` doit être définie avant de lancer ou de compiler le
frontend. Les variables commençant par `MAURIPAY_` doivent être définies dans
le terminal qui démarre le backend.

## Vérification de l’installation

Depuis la racine, vérifiez que le package backend peut être importé :

```bash
python -c "import mauripay; print('Backend MauriPay installé')"
```

Vérifiez ensuite les outils frontend :

```bash
cd frontend
npm run build
cd ..
```

La procédure de démarrage du backend et du frontend est présentée dans le
{doc}`quickstart`.
