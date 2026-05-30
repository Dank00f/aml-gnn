# GNN Experiment Report

## Статус

Это offline NumPy GCN baseline над transaction nodes. Он не входит в FastAPI runtime и не влияет на rule-based scoring.

## Метрики

- Input: `data\generated\ibm_realistic_gnn_1246.csv`
- Expanded to: `None`

| Metric | Value |
|---|---:|
| transaction_nodes | 1246 |
| transaction_edges | 1177 |
| feature_count | 8 |
| train_size | 873 |
| test_size | 373 |
| loss | 0.2705436900145348 |
| accuracy | 0.935656836461126 |
| precision | 1.0 |
| recall | 0.4146341463414634 |
| f1 | 0.5862068965517241 |
| roc_auc | 0.8830443726124009 |
| pr_auc | 0.6628564335533503 |

## Class Balance

```json
{
  "negative": 1108,
  "positive": 138
}
```

## Baselines

| Baseline | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| majority_class | 0.8900804289544236 | 0.0 | 0.0 | 0.0 | 0.575668527769615 | 0.17067625922120438 |
| feature_logistic_regression | 0.8847184986595175 | 0.0 | 0.0 | 0.0 | 0.7782104025859535 | 0.3188298316433533 |

## Confusion Matrix

```json
{
  "tp": 17,
  "tn": 332,
  "fp": 0,
  "fn": 24
}
```

## Ограничения

- Если датасет получен расширением маленького synthetic fixture, такие метрики нельзя считать production evidence.
- Модель является offline experiment, а не web runtime scorer.
- Если feature-only logistic baseline показывает те же метрики, преимущество GNN над табличными признаками не доказано.
- Метрики на реальном или более крупном внешнем датасете можно указывать только после отдельного запуска.
