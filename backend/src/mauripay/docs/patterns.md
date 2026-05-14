# Patterns mauritaniens — MauriPay-Analytics

## Objectif du document

Ce document formalise les patterns mauritaniens que le générateur synthétique MauriPay devra reproduire. Il sert de spécification pour les futurs fichiers :

```text
backend/src/mauripay/synthetic/patterns.py
backend/src/mauripay/synthetic/generator.py
```

Le but est de générer des transactions Mobile Money réalistes pour la Mauritanie et l’Afrique de l’Ouest. Les transactions ne doivent pas être créées au hasard : elles doivent reproduire des comportements plausibles comme la saisonnalité Ramadan, les salaires, les paiements de factures, les transferts diaspora, les tontines, la distribution géographique et les canaux USSD/APP/AGENT.

Chaque pattern est décrit avec :

- le nom du pattern ;
- la règle en langage naturel ;
- les paramètres numériques ;
- les champs du schéma impactés ;
- une idée de future implémentation.

---

## Pattern 1 — Saisonnalité Ramadan

### Règle naturelle

Pendant le mois de Ramadan, le volume global des transactions augmente fortement. Les utilisateurs effectuent davantage de transferts familiaux, de paiements marchands, d’achats alimentaires et de dons. La concentration horaire se déplace vers le soir, surtout après l’Iftar.

Les transactions de type `TRANSFER` et `MERCHANT` augmentent plus fortement que `CASH_OUT`.

### Paramètres numériques

| Paramètre | Valeur recommandée |
|---|---:|
| Multiplicateur de volume global | `random.uniform(2.0, 3.0)` |
| Plage horaire normale | distribution uniforme entre 07h et 22h |
| Plage horaire Ramadan | 60% des transactions entre 19h et 23h |
| Flag Ramadan | `is_ramadan = True` pendant la période |
| Types favorisés | `TRANSFER`, `MERCHANT` |

### Dates Ramadan 2026

Pour une première version du générateur, on peut utiliser une période fixe approximative :

```text
2026-02-17 à 2026-03-18
```

Ces dates doivent être vérifiées avec un calendrier islamique officiel ou une bibliothèque Python comme `hijri-converter`.

### Champs du schéma impactés

| Champ | Impact |
|---|---|
| `timestamp` | plus de transactions le soir |
| `is_ramadan` | `True` pendant Ramadan |
| `transaction_type` | hausse de `TRANSFER` et `MERCHANT` |
| `amount` | possible hausse des montants liés aux dépenses familiales |
| `channel` | maintien fort de l’USSD, surtout pour les populations rurales |

### Idée d’implémentation

```python
RAMADAN_2026_START = date(2026, 2, 17)
RAMADAN_2026_END = date(2026, 3, 18)


def is_ramadan_period(ts: datetime) -> bool:
    return RAMADAN_2026_START <= ts.date() <= RAMADAN_2026_END
```

---

## Pattern 2 — Cycles salariaux

### Règle naturelle

En début de mois, les fonctionnaires et salariés reçoivent leurs salaires. Cela crée un pic d’activité sur les transactions Mobile Money, surtout les retraits (`CASH_OUT`), les paiements de factures (`BILL_PAY`) et les transferts familiaux (`TRANSFER`).

Le pic principal se produit autour du 1er et du 5 du mois, mais l’effet peut s’étaler sur les cinq premiers jours.

### Paramètres numériques

| Paramètre | Valeur recommandée |
|---|---:|
| Jours de pic | `day in [1, 2, 3, 4, 5]` |
| Multiplicateur de volume | `×1.8` |
| Hausse `CASH_OUT` | `+40%` |
| Hausse `BILL_PAY` | `+30%` |
| Hausse `TRANSFER` | `+20%` |

### Champs du schéma impactés

| Champ | Impact |
|---|---|
| `timestamp` | pics en début de mois |
| `transaction_type` | hausse de `CASH_OUT`, `BILL_PAY`, `TRANSFER` |
| `amount` | montants moyens potentiellement plus élevés |
| `status` | peut rester majoritairement `SUCCESS` |

### Idée d’implémentation

```python
def is_salary_period(ts: datetime) -> bool:
    return ts.day in {1, 2, 3, 4, 5}
```

---

## Pattern 3 — Paiements SOMELEC / SNDE

### Règle naturelle

Chaque mois, une partie des utilisateurs paie des factures récurrentes. En Mauritanie, les paiements de factures importants concernent notamment l’électricité et l’eau.

- `SOMELEC` : électricité, souvent payée en début de mois.
- `SNDE` : eau, souvent payée en milieu de mois.

Ces transactions sont de type `BILL_PAY` et doivent obligatoirement avoir un `bill_provider`.

### Paramètres numériques

| Paramètre | Valeur recommandée |
|---|---:|
| Proportion d’utilisateurs concernés | environ `15%` des comptes actifs |
| Fréquence | 1 paiement par mois par utilisateur concerné |
| Montants SOMELEC | `800` à `8000` MRU |
| Montants SNDE | `400` à `2000` MRU |
| Type de transaction | `BILL_PAY` |
| Fournisseur | `SOMELEC` ou `SNDE` |

### Champs du schéma impactés

| Champ | Impact |
|---|---|
| `transaction_type` | doit être `BILL_PAY` |
| `bill_provider` | `SOMELEC` ou `SNDE` obligatoire |
| `amount` | dépend du fournisseur |
| `timestamp` | début ou milieu du mois |
| `fees` | souvent `0.00` ou faible selon la règle choisie |

### Idée d’implémentation

```python
def choose_bill_provider(day: int) -> str:
    if day <= 10:
        return "SOMELEC"
    return "SNDE"
```

---

## Pattern 4 — Transferts diaspora

### Règle naturelle

Une partie des transactions `CASH_IN` représente des flux entrants depuis la diaspora. Les pays d’origine principaux dans cette première version sont la France, l’Espagne et les États-Unis.

Ces transferts ont souvent des montants plus élevés que les transactions domestiques. Ils peuvent être plus fréquents le vendredi et le week-end.

### Paramètres numériques

| Paramètre | Valeur recommandée |
|---|---:|
| Proportion des `CASH_IN` depuis l’étranger | environ `20%` |
| France | `50%` des transferts diaspora |
| Espagne | `25%` |
| USA | `25%` |
| Montants | `5000` à `80000` MRU |
| Jours favoris | vendredi, samedi, dimanche |
| Multiplicateur week-end | `×1.4` |

### Champs du schéma impactés

| Champ | Impact |
|---|---|
| `transaction_type` | `CASH_IN` |
| `origin_country` | `FR`, `ES`, `US` |
| `amount` | plus élevé que les transferts locaux |
| `timestamp` | probabilité plus forte le vendredi/week-end |
| `receiver_id` | compte local qui reçoit l’argent |
| `receiver_wilaya` | souvent Nouakchott ou grandes zones urbaines |

### Règle de cohérence

Dans `schema.py`, `origin_country` doit rester `None` sauf pour les transactions de type `CASH_IN`.

### Idée d’implémentation

```python
DIASPORA_COUNTRY_WEIGHTS = {
    "FR": 0.50,
    "ES": 0.25,
    "US": 0.25,
}
```

---

## Pattern 5 — Tontines El Lewha

### Règle naturelle

Les tontines El Lewha sont des systèmes d’épargne collective. Un groupe de personnes cotise régulièrement un montant fixe. À chaque période, la somme collectée va à un bénéficiaire tournant.

Dans les données, cela peut apparaître comme plusieurs transactions `TRANSFER` du même montant, envoyées vers le même compte, dans une fenêtre temporelle courte.

### Paramètres numériques

| Paramètre | Valeur recommandée |
|---|---:|
| Taille du groupe | `random.randint(10, 30)` comptes |
| Montant de cotisation | montant fixe, exemple `500` MRU |
| Fréquence | hebdomadaire ou mensuelle |
| Fenêtre temporelle | toutes les transactions dans une fenêtre de 2h |
| Signature détectable | N comptes → 1 compte, même montant, même journée |

### Champs du schéma impactés

| Champ | Impact |
|---|---|
| `transaction_type` | `TRANSFER` |
| `sender_id` | plusieurs comptes différents |
| `receiver_id` | même bénéficiaire |
| `amount` | même montant pour toutes les cotisations |
| `timestamp` | même jour, fenêtre de 2h |
| `is_anomaly` | généralement `False`, car c’est un comportement culturel normal |

### Importance pour la détection d’anomalies

Une tontine peut ressembler à une anomalie de type `HIGH_FREQUENCY` ou à du `STRUCTURING` si le contexte culturel n’est pas pris en compte. Le générateur doit donc modéliser ce pattern comme un comportement normal afin d’éviter des faux positifs.

### Idée d’implémentation

```python
def generate_tontine_transactions(accounts, start, end):
    # Générer 10 à 30 TRANSFER du même montant vers le même receiver_id.
    # Ces transactions restent normales : is_anomaly=False, anomaly_type=NONE.
    ...
```

---

## Pattern 6 — Distribution géographique

### Règle naturelle

Les transactions doivent respecter une distribution géographique réaliste. Les grandes zones urbaines concentrent une part importante de l’activité Mobile Money, surtout Nouakchott et Nouadhibou.

La distribution ci-dessous est une approximation pour le générateur synthétique. Elle doit être raffinée plus tard avec des sources publiques comme GSMA, Banque Mondiale Findex, BCM ou données démographiques officielles.

### Paramètres numériques

| Wilaya / zone | Poids recommandé |
|---|---:|
| Nouakchott, 3 wilayas combinées | `60%` |
| Dakhlet Nouadhibou | `15%` |
| Trarza | `5%` |
| Brakna | `4%` |
| Gorgol | `3%` |
| Hodh El Chargui | `3%` |
| Assaba | `3%` |
| Guidimakha | `2%` |
| Autres wilayas | `7%` |

### Répartition interne proposée pour Nouakchott

Comme Nouakchott est séparée en trois wilayas dans le schéma, les 60% peuvent être divisés ainsi :

| Wilaya | Poids proposé |
|---|---:|
| Nouakchott-Ouest | `25%` |
| Nouakchott-Nord | `20%` |
| Nouakchott-Sud | `15%` |

### Champs du schéma impactés

| Champ | Impact |
|---|---|
| `sender_wilaya` | distribution géographique de l’expéditeur |
| `receiver_wilaya` | distribution géographique du receveur |
| `channel` | les wilayas rurales peuvent avoir plus d’USSD |
| `transaction_type` | certains types peuvent être plus urbains, comme `MERCHANT` |

### Idée d’implémentation

```python
WILAYA_WEIGHTS = {
    "Nouakchott-Ouest": 0.25,
    "Nouakchott-Nord": 0.20,
    "Nouakchott-Sud": 0.15,
    "Dakhlet Nouadhibou": 0.15,
    "Trarza": 0.05,
    "Brakna": 0.04,
    "Gorgol": 0.03,
    "Hodh El Chargui": 0.03,
    "Assaba": 0.03,
    "Guidimakha": 0.02,
    "Adrar": 0.015,
    "Tagant": 0.015,
    "Tiris Zemmour": 0.015,
    "Inchiri": 0.015,
    "Hodh El Gharbi": 0.015,
}
```

---

## Pattern 7 — Distribution des canaux

### Règle naturelle

Les transactions Mobile Money en Mauritanie et en Afrique de l’Ouest passent souvent par l’USSD, surtout dans les zones rurales ou lorsque les utilisateurs ont des téléphones basiques. Les applications mobiles sont plus utilisées en zone urbaine. Les agents physiques servent aux opérations de dépôt/retrait et aux utilisateurs moins autonomes numériquement.

### Paramètres numériques globaux

```python
CHANNEL_WEIGHTS = {
    "USSD": 0.70,
    "APP": 0.25,
    "AGENT": 0.05,
}
```

### Corrélation avec la géographie

Les wilayas rurales peuvent avoir un taux USSD plus élevé, par exemple `85%` ou plus.

Exemples de wilayas où l’USSD peut être renforcé :

```text
Adrar
Tiris Zemmour
Tagant
Hodh El Chargui
Hodh El Gharbi
Guidimakha
```

### Champs du schéma impactés

| Champ | Impact |
|---|---|
| `channel` | choix entre `USSD`, `APP`, `AGENT` |
| `sender_wilaya` | influence la probabilité du canal |
| `transaction_type` | `CASH_IN` et `CASH_OUT` peuvent être plus liés à `AGENT` |
| `operator` | certains opérateurs peuvent être plus utilisés via APP ou USSD |

### Idée d’implémentation

```python
RURAL_WILAYAS = {
    "Adrar",
    "Tiris Zemmour",
    "Tagant",
    "Hodh El Chargui",
    "Hodh El Gharbi",
    "Guidimakha",
}


def choose_channel(wilaya: str) -> str:
    if wilaya in RURAL_WILAYAS:
        return weighted_choice({"USSD": 0.85, "APP": 0.10, "AGENT": 0.05})
    return weighted_choice({"USSD": 0.70, "APP": 0.25, "AGENT": 0.05})
```

---

## Synthèse des patterns et champs impactés

| Pattern | Champs principalement impactés |
|---|---|
| Ramadan | `timestamp`, `is_ramadan`, `transaction_type`, `amount`, `channel` |
| Cycles salariaux | `timestamp`, `transaction_type`, `amount` |
| SOMELEC / SNDE | `transaction_type`, `bill_provider`, `amount`, `fees` |
| Diaspora | `transaction_type`, `origin_country`, `amount`, `timestamp`, `receiver_wilaya` |
| Tontines El Lewha | `sender_id`, `receiver_id`, `amount`, `timestamp`, `transaction_type` |
| Distribution géographique | `sender_wilaya`, `receiver_wilaya`, `channel` |
| Distribution des canaux | `channel`, `sender_wilaya`, `transaction_type` |

---

## Règles générales pour le générateur

1. Une transaction générée doit toujours être validable par `Transaction` dans `schema.py`.
2. `bill_provider` doit être rempli uniquement si `transaction_type = BILL_PAY`.
3. `origin_country` doit être rempli uniquement pour les `CASH_IN` diaspora.
4. `is_ramadan` doit être calculé depuis `timestamp`.
5. Les anomalies injectées doivent avoir `is_anomaly = True` et un `anomaly_type` différent de `NONE`.
6. Les comportements culturels normaux, comme les tontines, ne doivent pas être marqués automatiquement comme anomalies.
7. Les distributions numériques sont des hypothèses de simulation et doivent être documentées comme telles dans le mémoire.

---

## Notes de traçabilité

Ces patterns sont alignés avec le CDC MauriPay-Analytics : générateur synthétique, saisonnalité Ramadan, cycles salariaux, paiements SOMELEC/SNDE, transferts diaspora, tontines El Lewha, distribution géographique et distribution des canaux.
