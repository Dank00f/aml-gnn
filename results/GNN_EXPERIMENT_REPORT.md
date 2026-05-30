# GNN Experiment Report

## Статус

Это offline NumPy GCN baseline над transaction nodes. Он не входит в FastAPI runtime и не влияет на rule-based scoring.

## Метрики

- Input: `backend\tests\fixtures\ibm_aml_patterns.csv`
- Expanded to: `1000`

| Metric | Value |
|---|---:|
| transaction_nodes | 1000 |
| transaction_edges | 1200 |
| feature_count | 8 |
| train_size | 700 |
| test_size | 300 |
| loss | 0.03448285714252497 |
| accuracy | 1.0 |
| precision | 1.0 |
| recall | 1.0 |
| f1 | 1.0 |
| roc_auc | 1.0 |
| pr_auc | 1.0 |

## Class Balance

```json
{
  "negative": 700,
  "positive": 300
}
```

## Baselines

| Baseline | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| majority_class | 0.7 | 0.0 | 0.0 | 0.0 | 0.48777777777777775 | 0.3009833359403201 |
| feature_logistic_regression | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

## Confusion Matrix

```json
{
  "tp": 90,
  "tn": 210,
  "fp": 0,
  "fn": 0
}
```

## Ограничения

- Текущий dataset получен расширением маленького synthetic fixture; метрики не являются production evidence.
- Модель является offline experiment, а не web runtime scorer.
- Feature-only logistic baseline показывает те же метрики на текущем synthetic наборе, поэтому преимущество GNN над табличными признаками здесь не доказано.
- Метрики на реальном или большем внешнем датасете можно указывать только после отдельного запуска.
