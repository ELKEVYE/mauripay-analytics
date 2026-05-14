# Décisions de schéma — MauriPay-Analytics

## Objectif du document

Ce document justifie les choix du schéma de données MauriPay. Il explique pourquoi chaque champ existe, son type Python, ses contraintes, sa justification métier et son lien avec le projet.

Le schéma est implémenté dans :

```text
backend/src/mauripay/ingestion/schema.py
```

Il sert à valider les transactions Mobile Money synthétiques avant leur utilisation dans l’ingestion, le feature engineering, les algorithmes de détection d’anomalies, l’API et le dashboard.

---

## Vue d’ensemble du schéma

Le schéma contient 18 champs :

- 12 champs principaux issus du CDC ;
- 6 champs enrichis recommandés pour rendre le dataset plus réaliste et plus utile pour le ML.

### Champs principaux

```text
transaction_id
timestamp
sender_id
receiver_id
amount
currency
transaction_type
channel
operator
sender_wilaya
receiver_wilaya
is_anomaly
```

### Champs enrichis

```text
status
anomaly_type
fees
is_ramadan
bill_provider
origin_country
```

---

## Tableau synthétique des décisions

| Champ | Type Python | Contrainte principale | Justification |
|---|---|---|---|
| `transaction_id` | `str` | UUID v4, unique | Identifier chaque transaction sans collision |
| `timestamp` | `datetime` | timezone obligatoire UTC+0 | Éviter les ambiguïtés temporelles |
| `sender_id` | `str` | format `ACC_XXXXX` | Anonymiser le compte émetteur |
| `receiver_id` | `str` | format `ACC_XXXXX` | Anonymiser le compte récepteur |
| `amount` | `Decimal` | `> 0`, `<= 500000.00`, 2 décimales | Représenter correctement les montants financiers |
| `currency` | `Enum` | `MRU`, `XOF`, `USD` | Représenter la devise locale et les liens régionaux/diaspora |
| `transaction_type` | `Enum` | valeurs contrôlées | Décrire le type métier de transaction |
| `channel` | `Enum` | `USSD`, `APP`, `AGENT` | Capturer les canaux Mobile Money locaux |
| `operator` | `Enum` | services autorisés | Identifier le wallet provider / service financier |
| `sender_wilaya` | `Enum` | wilaya valide | Géolocaliser l’origine de la transaction |
| `receiver_wilaya` | `Enum` | wilaya valide | Géolocaliser la destination de la transaction |
| `is_anomaly` | `bool` | cohérent avec `anomaly_type` | Étiquette binaire pour ML |
| `status` | `Enum` | `SUCCESS`, `FAILED`, `PENDING` | Simuler succès, échec ou attente |
| `anomaly_type` | `Enum` | `NONE` si non anomalie | Expliquer le type d’anomalie |
| `fees` | `Decimal` | `>= 0`, `<= amount` | Simuler les frais de transaction |
| `is_ramadan` | `bool` | calculé depuis `timestamp` | Capturer la saisonnalité Ramadan |
| `bill_provider` | `Optional[Enum]` | obligatoire seulement pour `BILL_PAY` | Identifier le fournisseur payé |
| `origin_country` | `Optional[str]` | ISO alpha-2, seulement pour `CASH_IN` diaspora | Représenter les transferts depuis la diaspora |

---

# Décisions champ par champ

## 1. `transaction_id`

### Type Python

```python
str
```

### Contrainte

- UUID v4 ;
- généré automatiquement si absent ;
- doit être unique dans un dataset.

### Exemple

```text
550e8400-e29b-41d4-a716-446655440000
```

### Justification

`transaction_id` identifie chaque transaction de manière unique. Le choix d’un UUID v4 est plus robuste qu’un entier séquentiel, surtout dans un système distribué où plusieurs services peuvent générer des transactions en parallèle.

### Décision technique

Dans `schema.py`, l’identifiant est généré automatiquement avec :

```python
str(uuid.uuid4())
```

---

## 2. `timestamp`

### Type Python

```python
datetime
```

### Contrainte

- format ISO 8601 ;
- timezone obligatoire ;
- timezone attendue : UTC+0.

### Exemple

```text
2026-03-15T21:30:00+00:00
```

### Justification

Le champ `timestamp` est indispensable pour analyser les comportements temporels : Ramadan, cycles salariaux, pics horaires, week-ends, transactions nocturnes et séries temporelles.

La timezone est obligatoire pour éviter les ambiguïtés entre fuseaux horaires.

### Validation

Le schéma refuse les dates sans timezone et les dates qui ne sont pas en UTC+0.

---

## 3. `sender_id`

### Type Python

```python
str
```

### Contrainte

Format obligatoire :

```text
ACC_XXXXX
```

où `XXXXX` correspond à exactement 5 chiffres.

### Exemple

```text
ACC_00042
```

### Justification

Ce champ identifie le compte émetteur sans stocker d’information personnelle. On évite les noms réels et les numéros de téléphone.

### Validation

Regex utilisée :

```python
^ACC_\d{5}$
```

---

## 4. `receiver_id`

### Type Python

```python
str
```

### Contrainte

Même format que `sender_id` :

```text
ACC_XXXXX
```

### Exemple

```text
ACC_01987
```

### Justification

Ce champ identifie le compte récepteur de manière anonymisée.

### Règle métier

`sender_id` et `receiver_id` ne doivent pas être identiques.

---

## 5. `amount`

### Type Python

```python
Decimal
```

### Contraintes

- supérieur à `0` ;
- inférieur ou égal à `500000.00` ;
- maximum 2 décimales.

### Exemple

```text
2500.00
```

### Justification

Les montants financiers ne doivent pas être stockés en `float`, car `float` peut introduire des erreurs d’arrondi. Le type `Decimal` est plus adapté aux montants financiers.

La limite `500000.00` MRU représente le plafond défini pour la simulation MauriPay. Si une source réglementaire officielle BCM est utilisée plus tard, cette limite devra être citée précisément dans le mémoire.

---

## 6. `currency`

### Type Python

```python
Currency
```

### Valeurs autorisées

```text
MRU
XOF
USD
```

### Justification

- `MRU` : devise principale de la Mauritanie ;
- `XOF` : devise utilisée dans plusieurs pays UEMOA ;
- `USD` : devise utile pour certains scénarios de transferts internationaux/diaspora.

### Décision

La valeur par défaut est :

```text
MRU
```

Pour M1, le générateur synthétique produit uniquement des montants en `MRU`.
`XOF` et `USD` restent acceptés par le schéma pour les scénarios régionaux ou
diaspora prévus plus tard. Une future génération multi-devise devra aussi
définir des règles de conversion ou des fourchettes de montants par devise.

---

## 7. `transaction_type`

### Type Python

```python
TransactionType
```

### Valeurs autorisées

```text
TRANSFER
BILL_PAY
MERCHANT
CASH_IN
CASH_OUT
AIRTIME
```

### Justification

Ce champ décrit la nature métier de la transaction. Il s’inspire des types PaySim, mais il est adapté au contexte mauritanien.

| Valeur | Signification |
|---|---|
| `TRANSFER` | transfert d’argent entre deux comptes |
| `BILL_PAY` | paiement de facture |
| `MERCHANT` | paiement chez un commerçant |
| `CASH_IN` | dépôt d’argent |
| `CASH_OUT` | retrait d’argent |
| `AIRTIME` | achat de crédit téléphonique |

---

## 8. `channel`

### Type Python

```python
Channel
```

### Valeurs autorisées

```text
USSD
APP
AGENT
```

### Justification

Le canal est essentiel dans le contexte Mobile Money ouest-africain.

| Canal | Signification |
|---|---|
| `USSD` | téléphone basique sans internet |
| `APP` | application smartphone |
| `AGENT` | point de vente physique |

L’USSD est particulièrement important dans les zones rurales ou à faible connectivité.

---

## 9. `operator`

### Type Python

```python
Operator
```

### Signification

Dans ce projet, `operator` désigne le service financier ou wallet provider utilisé pour la transaction, pas forcément l’opérateur télécom.

### Valeurs recommandées

La liste minimale du CDC contient :

```text
Bankily
Masrvi
Sedad
```

Pour un schéma plus réaliste, la liste peut être enrichie avec :

```text
Click
bimbank Mobile
Bamis Digital
GazaPay
BaridCash
BCIpay
```

### Justification

Ce champ permet d’analyser les transactions par service financier, de simuler des pannes opérateur et de produire des indicateurs métier par provider.

---

## 10. `sender_wilaya`

### Type Python

```python
Wilaya
```

### Contrainte

Doit appartenir à la liste des wilayas retenue dans le schéma.

### Exemple

```text
Nouakchott-Ouest
```

### Justification

Ce champ indique la localisation de l’émetteur. Il est utilisé pour les analyses géographiques et la détection d’anomalies géographiques.

---

## 11. `receiver_wilaya`

### Type Python

```python
Wilaya
```

### Contrainte

Doit appartenir à la liste des wilayas retenue dans le schéma.

### Exemple

```text
Trarza
```

### Justification

Ce champ indique la localisation du receveur. Il permet d’analyser les flux entre wilayas et de détecter certains comportements inhabituels.

---

## 12. `is_anomaly`

### Type Python

```python
bool
```

### Valeurs

```text
False
True
```

### Justification

Ce champ indique si une transaction est normale ou anormale. Il joue un rôle similaire à `isFraud` dans PaySim, mais il est plus général, car il peut couvrir plusieurs types d’anomalies.

### Règle métier

- si `is_anomaly = False`, alors `anomaly_type = NONE` ;
- si `is_anomaly = True`, alors `anomaly_type` doit être différent de `NONE`.

---

# Champs enrichis

## 13. `status`

### Type Python

```python
TransactionStatus
```

### Valeurs autorisées

```text
SUCCESS
FAILED
PENDING
```

### Justification

Ce champ indique l’état de la transaction. Il est nécessaire pour simuler les pannes opérateur et les problèmes techniques.

| Statut | Signification |
|---|---|
| `SUCCESS` | transaction réussie |
| `FAILED` | transaction échouée |
| `PENDING` | transaction en attente |

---

## 14. `anomaly_type`

### Type Python

```python
AnomalyType
```

### Valeurs autorisées

```text
NONE
HIGH_AMOUNT
STRUCTURING
OPERATOR_OUTAGE
HIGH_FREQUENCY
UNUSUAL_LOCATION
```

### Justification

Ce champ donne la raison de l’anomalie. Il est plus informatif qu’un simple booléen.

| Type | Signification |
|---|---|
| `NONE` | aucune anomalie |
| `HIGH_AMOUNT` | montant inhabituellement élevé |
| `STRUCTURING` | fractionnement d’un gros montant en petites transactions |
| `OPERATOR_OUTAGE` | panne ou problème opérateur simulé |
| `HIGH_FREQUENCY` | trop de transactions en peu de temps |
| `UNUSUAL_LOCATION` | comportement géographique inhabituel |

---

## 15. `fees`

### Type Python

```python
Decimal
```

### Contraintes

- supérieur ou égal à `0` ;
- inférieur ou égal à `amount` ;
- maximum 2 décimales.

### Justification

Les frais sont importants pour les analyses métier et pour simuler le coût réel d’une transaction Mobile Money.

---

## 16. `is_ramadan`

### Type Python

```python
bool
```

### Contrainte

Ce champ doit être calculé automatiquement depuis `timestamp` dans :

```text
backend/src/mauripay/synthetic/patterns.py
```

puis rempli dans :

```text
backend/src/mauripay/synthetic/generator.py
```

### Justification

Ramadan influence fortement le comportement transactionnel : hausse du volume, concentration le soir, transferts familiaux et paiements marchands.

### Décision

`schema.py` stocke et valide le champ, mais ne calcule pas Ramadan. Le calcul appartient aux patterns du générateur.

---

## 17. `bill_provider`

### Type Python

```python
Optional[BillProvider]
```

### Valeurs recommandées

```text
SOMELEC
SNDE
MAURITEL
CHINGUITEL
MATTEL
```

### Contraintes

- obligatoire si `transaction_type = BILL_PAY` ;
- `None` si `transaction_type != BILL_PAY`.

### Justification

Ce champ indique quel fournisseur est payé lors d’un paiement de facture. Il permet de distinguer les factures d’électricité, d’eau et de télécommunication.

---

## 18. `origin_country`

### Type Python

```python
Optional[str]
```

### Contraintes

- `None` par défaut ;
- exactement 2 lettres ;
- lettres majuscules ;
- format ISO 3166-1 alpha-2 ;
- autorisé seulement pour les transactions `CASH_IN` diaspora.

### Exemples

```text
FR
ES
US
```

### Justification

Ce champ permet de représenter les transferts entrants depuis la diaspora. Il ne doit pas être utilisé pour les transactions domestiques.

---

# Règles de cohérence globales

## Règle 1 — Comptes différents

```text
sender_id != receiver_id
```

Une transaction ne doit pas avoir le même compte comme émetteur et receveur.

## Règle 2 — Frais valides

```text
fees <= amount
```

Les frais ne peuvent pas dépasser le montant envoyé.

## Règle 3 — Paiement de facture

```text
si transaction_type = BILL_PAY → bill_provider obligatoire
si transaction_type != BILL_PAY → bill_provider = None
```

## Règle 4 — Diaspora

```text
si transaction_type != CASH_IN → origin_country = None
```

## Règle 5 — Anomalie

```text
si is_anomaly = False → anomaly_type = NONE
si is_anomaly = True → anomaly_type != NONE
```

## Règle 6 — Timestamp

```text
timestamp doit contenir une timezone UTC+0
```

---

# Lien avec l’architecture du projet

Le schéma est utilisé dans plusieurs couches du projet :

| Couche | Utilisation du schéma |
|---|---|
| Couche 1 — Générateur | générer des transactions conformes |
| Couche 2 — Ingestion | valider CSV/JSON/Parquet |
| Couche 2 — Feature engineering | créer des features fiables |
| Couche 3 — Détection | entraîner et tester les algorithmes sur des données propres |
| Couche 4 — API | recevoir et retourner des transactions validées |
| Couche 5 — Dashboard | afficher des données cohérentes |

---

# Décisions importantes pour la suite

## `is_ramadan`

Le champ reste dans `schema.py`, mais son calcul sera fait dans `synthetic/patterns.py`.

## `operator`

Le champ `operator` désigne le service Mobile Money ou wallet provider, pas l’opérateur réseau télécom.

## Plafond `amount`

La limite `500000.00` MRU est conservée comme plafond de simulation défini par le projet. Si elle est présentée comme limite réglementaire réelle dans le mémoire, une source officielle devra être citée.

## Wilayas

Le schéma doit utiliser une liste cohérente de wilayas dans tous les fichiers : `schema.py`, `patterns.md`, `generator.py`, tests et dashboard.

---

# Exemple de transaction valide

```json
{
  "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-03-15T21:30:00+00:00",
  "sender_id": "ACC_01023",
  "receiver_id": "ACC_05021",
  "amount": "2500.00",
  "currency": "MRU",
  "transaction_type": "TRANSFER",
  "channel": "USSD",
  "operator": "Bankily",
  "sender_wilaya": "Nouakchott-Ouest",
  "receiver_wilaya": "Trarza",
  "status": "SUCCESS",
  "fees": "25.00",
  "is_ramadan": true,
  "bill_provider": null,
  "origin_country": null,
  "is_anomaly": false,
  "anomaly_type": "NONE"
}
```

---

# Résumé

Le schéma MauriPay formalise une transaction Mobile Money ouest-africaine adaptée au contexte mauritanien. Il s’inspire de PaySim pour les éléments de base, mais ajoute des champs locaux importants : devise, canal, opérateur, wilaya, Ramadan, fournisseur de facture et pays d’origine diaspora.

Ce schéma est la fondation technique du projet. Tous les modules suivants doivent produire ou consommer des données conformes à ce modèle.
