# Dashboard

Le dashboard React permet de charger un dataset, d’exécuter les modèles et
d’explorer les transactions et anomalies. Il est disponible par défaut sur
<http://localhost:5173>.

## Prérequis

Avant d’ouvrir l’interface :

1. démarrez FastAPI sur `http://127.0.0.1:8000` ;
2. vérifiez que les modèles sont présents dans `backend/models/` ;
3. démarrez Vite depuis `frontend/` avec `npm run dev` ;
4. ouvrez <http://localhost:5173>.

Consultez le {doc}`quickstart` pour les commandes complètes.

## Parcours utilisateur

1. Vérifiez l’indicateur de connexion à l’API dans l’en-tête.
2. Sur le dashboard, choisissez un fichier CSV, JSON, JSONL ou Parquet.
3. Lancez l’analyse.
4. L’API conserve le fichier et valide toutes les transactions.
5. Si toutes les lignes sont valides, les trois modèles et l’ensemble sont
   exécutés.
6. Le frontend charge ensuite les statistiques, les séries temporelles, les
   agrégations géographiques et l’état des modèles.
7. Utilisez la barre latérale pour naviguer entre les analyses.
8. Dans la liste des transactions suspectes, utilisez les filtres, la
   pagination et le panneau de détail.

## Dashboard principal

Le dashboard affiche quatre indicateurs :

- nombre total de transactions ;
- montant total en MRU ;
- nombre d’alertes du consensus des trois modèles ;
- taux de transactions échouées.

Il permet aussi de choisir le dataset à analyser.

## Analyse temporelle des transactions

Cette vue affiche notamment :

- le nombre de transactions par jour ;
- les montants agrégés par jour ;
- l’évolution des volumes dans le temps.

## Analyse des opérations

Cette vue présente :

- la répartition par type de transaction ;
- la répartition par canal ;
- les volumes par opérateur ;
- l’activité selon l’heure et le jour.

## Analyse géographique

Cette vue utilise la carte et les agrégations par wilaya pour afficher :

- les wilayas les plus actives ;
- le nombre de transactions ;
- les montants ;
- les taux d’échec.

Les statistiques combinent les wilayas de l’expéditeur et du destinataire.

## Anomalies temporelles

Cette vue présente la distribution des alertes :

- par heure ;
- par semaine ;
- selon les types d’anomalies visibles dans les aperçus de prédiction.

## Anomalies géographiques

Cette vue classe les wilayas selon le nombre d’alertes et permet d’identifier
les zones qui concentrent les transactions suspectes.

## Transactions suspectes

La table regroupe les aperçus produits par les modèles. Selon les colonnes
disponibles, elle affiche notamment :

- identifiant et date ;
- montant et type ;
- canal et opérateur ;
- wilayas ;
- algorithme ;
- score et label ;
- raisons des règles métier.

Les filtres permettent de réduire la liste, et la pagination facilite la
consultation des grands ensembles. Un clic sur une ligne ouvre son détail.

## Captures d’écran

Les captures destinées à la documentation doivent être placées dans :

```text
docs/_static/dashboard/
```

Par exemple, après l’ajout de `dashboard.png`, insérez-la avec MyST :

```markdown
![Dashboard MauriPay](_static/dashboard/dashboard.png)
```

Aucune image inexistante n’est actuellement référencée, afin de conserver un
build Sphinx sans avertissement.

## Erreurs courantes

### API inaccessible

Message typique : l’API FastAPI est inaccessible. Vérifiez que le backend est
démarré, que `VITE_API_BASE_URL` est correcte et que CORS autorise le frontend.

### Fichier invalide

Le dashboard affiche le nombre de lignes invalides et le chemin du rapport
d’erreurs. Corrigez les lignes selon le {doc}`data_schema`, puis rechargez le
fichier.

### Format non supporté

Utilisez une extension `.csv`, `.json`, `.jsonl` ou `.parquet`.

### Modèles absents

`/detect/predict-all` exige les artefacts Isolation Forest, LOF et autoencoder,
ainsi que leurs préprocesseurs. Restaurez les fichiers ou entraînez les modèles.

### Dataset introuvable

Vérifiez le chemin renvoyé par l’ingestion et les racines autorisées par
`MAURIPAY_API_ALLOWED_ROOTS`.
