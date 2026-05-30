# 09. GNN For Beginner

## Что такое ML

Machine Learning — подход, при котором модель учится на данных, а не задаётся только ручными правилами.

## Что такое нейронная сеть

Нейронная сеть — модель, которая преобразует входные признаки в прогноз. Например, признаки транзакции в вероятность подозрительности.

## Что такое GNN

Graph Neural Network — нейронная сеть для графов. Она учитывает не только признаки объекта, но и связи с соседями.

## Зачем GNN в AML

AML-схемы часто проявляются в связях: кто кому переводит, через какие промежуточные счета, какие транзакции идут рядом во времени. GNN может учиться на таких структурах.

## Что реализовано сейчас

Реализована подготовка данных и NumPy GCN training path:

- каждая транзакция становится node;
- label берётся из `Is Laundering`;
- строятся связи между transaction nodes;
- считаются признаки транзакций.
- можно запустить offline training command без PyTorch/PyG.

Файлы:

- `backend/src/ml/gnn_dataset.py`;
- `backend/src/ml/gnn_baseline.py`;
- `backend/tests/test_gnn_dataset.py`.

## Как проверить

```powershell
cd backend
.\.venv\Scripts\python.exe -m src.ml.gnn_baseline --input tests/fixtures/ibm_aml_patterns.csv --describe-only
```

Training:

```powershell
$env:PYTHONPATH='backend'
.\backend\.venv\Scripts\python.exe -m src.ml.gnn_baseline --input backend\tests\fixtures\ibm_aml_patterns.csv --expand-size 1000 --epochs 200 --hidden-dim 16 --metrics-output results\gnn_metrics.json --report-output results\GNN_EXPERIMENT_REPORT.md
```

Результат сохраняется в `results/gnn_metrics.json` и `results/GNN_EXPERIMENT_REPORT.md`.

Если feature-only baseline даёт такой же результат, это значит, что текущий датасет решается табличными признаками. Тогда нельзя утверждать, что именно графовая нейросеть дала преимущество.

## Чем GNN score отличается от rule-based score

- Rule-based score считается по явно заданным правилам и alerts.
- GNN score во frontend должен появиться только после отдельной inference-интеграции.
- Сейчас GNN score не используется в backend runtime.

## Что сказать на защите

«GNN-модуль находится в экспериментальной стадии. В проекте подготовлена постановка задачи, построение transaction graph dataset и NumPy GCN baseline, но inference не включён в основной runtime».

## Что нельзя утверждать

- Нельзя утверждать, что GNN подтверждена на больших или реальных данных.
- Нельзя утверждать, что GNN улучшает качество без сравнения с baselines на большом датасете.
- Нельзя показывать ML-метрики без реального эксперимента.
