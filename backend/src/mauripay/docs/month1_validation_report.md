# Rapport de validation M1

Ce rapport donne un exemple reproductible pour la presentation M1.

Commande executee depuis `backend/` :

```powershell
$env:PYTHONPATH="src"
python -m mauripay.synthetic.generator --rows 10000 --output data/generated/mauripay_s_10k.csv
python -m mauripay.synthetic.validate data/generated/mauripay_s_10k.csv
```

## Resultat schema

- Colonnes obligatoires : OK
- Validation Pydantic ligne par ligne : OK
- Nombre total de transactions : 10 000
- Devise M1 : `MRU` a 100 %

## Distributions principales

| Indicateur | Resultat |
|---|---:|
| USSD | 71.67 % |
| APP | 23.26 % |
| AGENT | 5.07 % |
| Nouakchott total | 59.66 % |
| Dakhlet Nouadhibou | 15.27 % |
| Autres wilayas | 25.07 % |
| Anomalies | 8.36 % |
| Multiplicateur Ramadan | x2.68 |
| Multiplicateur salarial | x1.74 |

## Types de transactions

| Type | Nombre |
|---|---:|
| TRANSFER | 3362 |
| CASH_OUT | 1831 |
| BILL_PAY | 1554 |
| MERCHANT | 1527 |
| CASH_IN | 870 |
| AIRTIME | 856 |

## Types d'anomalies

| Type | Nombre |
|---|---:|
| NONE | 9164 |
| HIGH_FREQUENCY | 434 |
| STRUCTURING | 198 |
| HIGH_AMOUNT | 104 |
| OPERATOR_OUTAGE | 66 |
| UNUSUAL_LOCATION | 34 |

## Lecture pour l'encadrant

Le generateur respecte le schema, produit des distributions proches des
hypotheses M1 et garde les tontines comme comportements normaux. La couverture
de tests complete reste planifiee en M3, conformement au CDC.
