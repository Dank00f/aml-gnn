# GNN Experiment Report

## Статус

Это offline NumPy GCN baseline над transaction nodes. Он не входит в FastAPI runtime и не влияет на rule-based scoring.

## Метрики

- Input: `data\AMLSim CSV\transactions.csv`
- Expanded to: `None`

| Metric | Value |
|---|---:|
| transaction_nodes | 10000 |
| transaction_edges | 2076 |
| feature_count | 16 |
| train_size | 6000 |
| validation_size | 2000 |
| test_size | 2000 |
| loss | 0.38003739888892285 |
| decision_threshold | 0.6863151349219649 |
| accuracy | 0.8735 |
| precision | 0.5945945945945946 |
| recall | 0.8313953488372093 |
| f1 | 0.6933333333333334 |
| roc_auc | 0.932186341422312 |
| pr_auc | 0.7543872132550722 |

## Class Balance

```json
{
  "negative": 8281,
  "positive": 1719
}
```

## Baselines

| Baseline | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| majority_class | 0.828 | 0.0 | 0.0 | 0.0 | 0.49932942927760926 | 0.17225608820043892 |
| feature_logistic_regression | 0.875 | 0.6175 | 0.7180232558139535 | 0.663978494623656 | 0.9414900713402988 | 0.7735956054100428 |

## Confusion Matrix

```json
{
  "tp": 286,
  "tn": 1461,
  "fp": 195,
  "fn": 58
}
```

## Validation Metrics

```json
{
  "accuracy": 0.862,
  "precision": 0.5755555555555556,
  "recall": 0.752906976744186,
  "f1": 0.6523929471032746,
  "roc_auc": 0.9223243877092462,
  "pr_auc": 0.7252313315676067,
  "confusion_matrix": {
    "tp": 259,
    "tn": 1465,
    "fp": 191,
    "fn": 85
  }
}
```

## Default Threshold Metrics

```json
{
  "accuracy": 0.8135,
  "precision": 0.47806354009077157,
  "recall": 0.9186046511627907,
  "f1": 0.6288557213930348,
  "roc_auc": 0.932186341422312,
  "pr_auc": 0.7543872132550722,
  "confusion_matrix": {
    "tp": 316,
    "tn": 1311,
    "fp": 345,
    "fn": 28
  }
}
```

## Top-K Metrics

```json
{
  "positive_count": 344,
  "at_10": {
    "k": 10,
    "precision": 1.0,
    "recall": 0.029069767441860465,
    "true_positives": 10
  },
  "at_50": {
    "k": 50,
    "precision": 0.92,
    "recall": 0.13372093023255813,
    "true_positives": 46
  },
  "at_100": {
    "k": 100,
    "precision": 0.91,
    "recall": 0.26453488372093026,
    "true_positives": 91
  },
  "at_positive_count": {
    "k": 344,
    "precision": 0.6831395348837209,
    "recall": 0.6831395348837209,
    "true_positives": 235
  }
}
```

## Ограничения

- Если датасет получен расширением маленького synthetic fixture, такие метрики нельзя считать production evidence.
- Модель является offline experiment, а не web runtime scorer.
- Если feature-only logistic baseline показывает те же метрики, преимущество GNN над табличными признаками не доказано.
- Метрики на реальном или более крупном внешнем датасете можно указывать только после отдельного запуска.
