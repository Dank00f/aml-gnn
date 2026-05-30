# GNN Experiment Report

## Статус

Это offline NumPy GCN baseline над transaction nodes. Он не входит в FastAPI runtime и не влияет на rule-based scoring.

## Метрики

- Input: `data\AMLSim CSV\transactions.csv`
- Expanded to: `None`

| Metric | Value |
|---|---:|
| transaction_nodes | 5000 |
| transaction_edges | 637 |
| feature_count | 16 |
| train_size | 3000 |
| validation_size | 1000 |
| test_size | 1000 |
| loss | 0.3304981087318405 |
| decision_threshold | 0.5509277266170834 |
| accuracy | 0.858 |
| precision | 0.731651376146789 |
| recall | 0.9273255813953488 |
| f1 | 0.8179487179487179 |
| roc_auc | 0.9376861174134997 |
| pr_auc | 0.8626697003379585 |

## Class Balance

```json
{
  "negative": 3281,
  "positive": 1719
}
```

## Baselines

| Baseline | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| majority_class | 0.656 | 0.0 | 0.0 | 0.0 | 0.49674737663074303 | 0.3454033920021443 |
| feature_logistic_regression | 0.851 | 0.7044025157232704 | 0.9767441860465116 | 0.8185140073081608 | 0.9398796440726035 | 0.8572617947120043 |

## Confusion Matrix

```json
{
  "tp": 319,
  "tn": 539,
  "fp": 117,
  "fn": 25
}
```

## Validation Metrics

```json
{
  "accuracy": 0.854,
  "precision": 0.7313084112149533,
  "recall": 0.9098837209302325,
  "f1": 0.810880829015544,
  "roc_auc": 0.9293551474758934,
  "pr_auc": 0.8501190383714219,
  "confusion_matrix": {
    "tp": 313,
    "tn": 541,
    "fp": 115,
    "fn": 31
  }
}
```

## Default Threshold Metrics

```json
{
  "accuracy": 0.851,
  "precision": 0.7161862527716186,
  "recall": 0.938953488372093,
  "f1": 0.8125786163522013,
  "roc_auc": 0.9376861174134997,
  "pr_auc": 0.8626697003379585,
  "confusion_matrix": {
    "tp": 323,
    "tn": 528,
    "fp": 128,
    "fn": 21
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
    "precision": 0.93,
    "recall": 0.2703488372093023,
    "true_positives": 93
  },
  "at_positive_count": {
    "k": 344,
    "precision": 0.8023255813953488,
    "recall": 0.8023255813953488,
    "true_positives": 276
  }
}
```

## Ограничения

- Если датасет получен расширением маленького synthetic fixture, такие метрики нельзя считать production evidence.
- Модель является offline experiment, а не web runtime scorer.
- Если feature-only logistic baseline показывает те же метрики, преимущество GNN над табличными признаками не доказано.
- Метрики на реальном или более крупном внешнем датасете можно указывать только после отдельного запуска.
