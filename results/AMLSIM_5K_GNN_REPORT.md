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
| feature_count | 8 |
| train_size | 3500 |
| test_size | 1500 |
| loss | 0.6276487787385621 |
| accuracy | 0.656 |
| precision | 0.0 |
| recall | 0.0 |
| f1 | 0.0 |
| roc_auc | 0.6478560061763408 |
| pr_auc | 0.4572546113114794 |

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
| majority_class | 0.656 | 0.0 | 0.0 | 0.0 | 0.5113620249574589 | 0.352180018559777 |
| feature_logistic_regression | 0.656 | 0.0 | 0.0 | 0.0 | 0.6102169597277368 | 0.4260640056116664 |

## Confusion Matrix

```json
{
  "tp": 0,
  "tn": 984,
  "fp": 0,
  "fn": 516
}
```

## Ограничения

- Если датасет получен расширением маленького synthetic fixture, такие метрики нельзя считать production evidence.
- Модель является offline experiment, а не web runtime scorer.
- Если feature-only logistic baseline показывает те же метрики, преимущество GNN над табличными признаками не доказано.
- Метрики на реальном или более крупном внешнем датасете можно указывать только после отдельного запуска.
