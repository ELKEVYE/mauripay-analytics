# Générateur synthétique

Le générateur crée des transactions Mobile Money fictives conformes au
{doc}`data_schema`. Il simule le contexte mauritanien, des comportements
normaux et plusieurs familles d’anomalies.

## Générer un dataset

Depuis le dossier `backend/`, sous Windows PowerShell :

```powershell
cd backend
$env:PYTHONPATH="src"

python -m mauripay.synthetic.generator `
  --rows 10000 `
  --seed 42 `
  --output ../data/generated/mauripay_s_10k.csv
```

Sous Linux ou macOS :

```bash
cd backend
PYTHONPATH=src python -m mauripay.synthetic.generator \
  --rows 10000 \
  --seed 42 \
  --output ../data/generated/mauripay_s_10k.csv
```

Si le backend est installé avec `pip install -e backend`, la définition de
`PYTHONPATH` n’est normalement pas nécessaire.

Le format de sortie est déterminé par l’extension. Les extensions prises en
charge par le générateur sont `.csv`, `.json` et `.parquet`.

## Paramètres

| Paramètre | Valeur par défaut | Description |
|---|---:|---|
| `--rows` | `10000` | Nombre total de transactions à produire |
| `--accounts` | `5000` | Nombre de comptes fictifs |
| `--output` | `data/generated/mauripay_s.csv` | Chemin du fichier de sortie |
| `--start-date` | `2026-01-01` | Début de la période, format `YYYY-MM-DD` |
| `--end-date` | `2026-03-31` | Fin de la période, format `YYYY-MM-DD` |
| `--seed` | `42` | Graine pseudo-aléatoire pour la reproductibilité |
| `--anomaly-rate` | `0.02` | Probabilité d’injecter une anomalie simple |
| `--tontine-rate` | `0.001` | Probabilité de générer une séquence normale de tontine |
| `--structuring-rate` | `0.003` | Probabilité de générer une séquence de fractionnement |
| `--high-frequency-rate` | `0.002` | Probabilité de générer une séquence à forte fréquence |

Une valeur comme `0.02` correspond à une probabilité de 2 %. Le taux final de
lignes anormales peut être supérieur, car un seul événement de structuration
ou de forte fréquence génère plusieurs transactions.

La même commande avec une seed et des paramètres identiques produit des
résultats reproductibles avec la même version du code et des dépendances.

## Patterns normaux

### Ramadan

Le générateur marque les transactions situées pendant la période configurée du
Ramadan et adapte les horaires et l’activité. Une activité nocturne plus élevée
peut donc être normale dans ce contexte.

### Salaires

Les périodes de salaire augmentent les entrées, retraits et transferts. Ce
pattern évite de représenter le volume de transactions comme uniforme pendant
tout le mois.

### Paiements de factures

Les opérations `BILL_PAY` sont associées à un fournisseur comme SOMELEC, SNDE
ou un opérateur téléphonique. Les montants suivent une plage adaptée aux
factures.

### Diaspora

Certaines opérations `CASH_IN` possèdent un `origin_country` tel que `FR`, `ES`
ou `US`. Elles représentent des fonds provenant de l’étranger.

### Tontines

Les tontines « El Lewha » créent des transferts réguliers entre les membres
d’un groupe. Elles peuvent ressembler à une séquence suspecte, mais elles sont
étiquetées comme comportement normal afin de tester les faux positifs.

### Canaux

Les transactions utilisent `USSD`, `APP` ou `AGENT`. USSD est majoritaire et
sa proportion est encore plus importante dans les wilayas rurales.

### Géographie

La distribution favorise Nouakchott et Nouadhibou tout en conservant des
transactions dans les autres wilayas. Les wilayas de l’expéditeur et du
destinataire sont enregistrées séparément.

## Anomalies injectées

### `HIGH_AMOUNT`

Le montant dépasse fortement les valeurs normales du type de transaction.

Exemple :

```text
Montant habituel de l’expéditeur : 3 000 MRU
Nouvelle transaction             : 150 000 MRU
```

### `HIGH_FREQUENCY`

Un même compte effectue une succession rapide d’opérations.

Exemple :

```text
10:00 → transfert
10:01 → transfert
10:03 → transfert
10:05 → transfert
```

Cette séquence peut représenter un compte automatisé ou une tentative de vider
rapidement un portefeuille.

### `STRUCTURING`

Une somme importante est divisée en plusieurs transferts rapprochés et de
montants similaires.

Exemple :

```text
29 500 MRU + 30 000 MRU + 28 500 MRU + 31 000 MRU
```

Ce pattern concerne les opérations `TRANSFER` et simule un contournement de
seuils de contrôle.

### `OPERATOR_OUTAGE`

Plusieurs transactions d’un même opérateur échouent dans une période courte,
généralement avec des frais nuls.

Exemple :

```text
10:00 → Bankily, FAILED, frais 0
10:12 → Bankily, FAILED, frais 0
10:25 → Bankily, FAILED, frais 0
```

Il s’agit principalement d’une anomalie opérationnelle et non d’une fraude
client certaine.

### `UNUSUAL_LOCATION`

Une transaction apparaît dans une wilaya inhabituelle ou éloignée par rapport
au comportement attendu du compte.

Exemple :

```text
Habitude : transactions à Nouakchott
Nouvelle opération : retrait élevé dans une wilaya éloignée
```

Cette situation peut indiquer un compte compromis, mais elle peut aussi
correspondre à un déplacement légitime.

## Valider le résultat

Depuis `backend/` :

```powershell
$env:PYTHONPATH="src"
python -m mauripay.synthetic.validate ../data/generated/mauripay_s_10k.csv
```

Le validateur contrôle les colonnes attendues et applique le schéma Pydantic à
chaque ligne.
