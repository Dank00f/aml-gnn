# GNN Data Audit

## Статус

GNN в проекте реализован как отдельный offline experiment. Он не входит в FastAPI runtime, не участвует в upload pipeline, не влияет на rule-based risk score и не отображается во frontend.

Сейчас в проекте есть:

- построение transaction-node graph dataset из IBM-format транзакций;
- residual NumPy GCN baseline без PyTorch/PyG;
- сравнение с простыми baseline-моделями;
- отдельный подготовитель более реалистичного IBM-format датасета для GNN-эксперимента.

## Почему GNN вынесен отдельно

PyTorch и PyTorch Geometric не добавлялись в обязательный backend runtime. Для текущего Windows-окружения и Python 3.14 это лишний риск установки и сопровождения. Поэтому baseline реализован на NumPy и запускается отдельно от web-приложения.

## Файлы

| Файл | Назначение |
|---|---|
| `backend/src/ml/gnn_dataset.py` | Строит transaction graph dataset из нормализованных IBM транзакций |
| `backend/src/ml/numpy_gcn.py` | Residual NumPy GCN baseline, weighted loss, validation threshold tuning |
| `backend/src/ml/gnn_baseline.py` | CLI для describe-only summary и offline training |
| `backend/src/ml/realistic_ibm_dataset.py` | Готовит более реалистичный IBM-format датасет на базе реального IBM sample |
| `backend/src/ml/prepare_realistic_ibm_dataset.py` | CLI для генерации derived dataset |
| `backend/tests/test_gnn_dataset.py` | Тесты dataset construction, generator CLI и GCN smoke |

## Формулировка задачи

Используется постановка transaction graph / line graph:

- каждая транзакция становится вершиной графа;
- label вершины берётся из `Is Laundering`;
- связи между transaction nodes строятся по общим аккаунтам и временному окну;
- задача формулируется как binary node classification для transaction nodes.

## Признаки transaction node

Подтверждённый набор признаков:

- `amount`;
- `amount_log1p`;
- `amount_received`;
- `amount_received_to_paid_ratio`;
- код `payment_currency`;
- код `receiving_currency`;
- код `payment_format`;
- `hour`;
- `sender_out_count`;
- `receiver_in_count`.
- `sender_in_count`;
- `receiver_out_count`;
- `sender_out_amount_sum`;
- `receiver_in_amount_sum`;
- `sender_unique_receivers`;
- `receiver_unique_senders`.

## Что улучшено в GNN pipeline

До доработки модель на AMLSim 5k уходила в all-negative prediction:

- `precision = 0.0`;
- `recall = 0.0`;
- `f1 = 0.0`.

Исправления:

- train/validation/test split вместо одного train/test;
- стандартизация признаков только по train split;
- balanced class-weighted cross-entropy;
- подбор decision threshold по validation split;
- sparse adjacency aggregation вместо плотной матрицы смежности;
- residual GCN: модель использует и собственные признаки транзакции, и агрегированные признаки соседей;
- top-k метрики для investigative сценария.

## Базовый smoke-run

Команда:

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph\backend
.\.venv\Scripts\python.exe -m src.ml.gnn_baseline --input tests/fixtures/ibm_aml_patterns.csv --describe-only
```

Расширенный synthetic smoke:

```powershell
$env:PYTHONPATH='backend'
.\backend\.venv\Scripts\python.exe -m src.ml.gnn_baseline --input backend\tests\fixtures\ibm_aml_patterns.csv --expand-size 1000 --epochs 200 --hidden-dim 16 --metrics-output results\gnn_metrics.json --report-output results\GNN_EXPERIMENT_REPORT.md
```

Этот запуск подтверждает работоспособность pipeline, но не качество модели на более сложных данных: feature-only logistic baseline показывает те же метрики.

## Более реалистичный IBM-format датасет

Источник фона:

- `backend/data/ibm_archive/IBM-Small_Trans_1000.csv`

Этот файл взят из присланного архива и соответствует IBM/AMLSim-схеме:

- `Timestamp`
- `From Bank`
- `Account`
- `To Bank`
- `Account.1`
- `Amount Received`
- `Receiving Currency`
- `Amount Paid`
- `Payment Currency`
- `Payment Format`
- `Is Laundering`

Проблема исходного sample: в `IBM-Small_Trans_1000.csv` все labels равны `0`, поэтому для supervised GNN он бесполезен сам по себе.

Решение:

- взять реальный IBM-format sample как background noise;
- сохранить его схему без изменений;
- инжектить структурные laundering-паттерны;
- инжектить и benign структурные паттерны, чтобы задача не сводилась к тривиальному “любая плотная структура = laundering”.

Использованные injected groups:

- positive cycles;
- positive fan-out;
- positive transit;
- benign fan-out;
- benign transit.

Команда генерации:

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph\backend
$env:PYTHONPATH='C:\Users\Dankoff\PycharmProjects\aml-graph\backend'
.\.venv\Scripts\python.exe -m src.ml.prepare_realistic_ibm_dataset --input data/ibm_archive/IBM-Small_Trans_1000.csv --output data/generated/ibm_realistic_gnn_1246.csv --stats-output data/generated/ibm_realistic_gnn_1246_stats.json --positive-cycle-groups 10 --positive-fanout-groups 12 --positive-transit-groups 12 --benign-fanout-groups 12 --benign-transit-groups 12
```

Полученный dataset:

| Показатель | Значение |
|---|---:|
| total_rows | 1246 |
| positive_rows | 138 |
| negative_rows | 1108 |
| injected_positive_rows | 138 |
| injected_benign_rows | 108 |

Артефакты:

- `backend/data/generated/ibm_realistic_gnn_1246.csv`
- `backend/data/generated/ibm_realistic_gnn_1246_stats.json`
- `results/gnn_realistic_dataset_stats.json`

## GNN run на более реалистичном датасете

Команда:

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph\backend
$env:PYTHONPATH='C:\Users\Dankoff\PycharmProjects\aml-graph\backend'
.\.venv\Scripts\python.exe -m src.ml.gnn_baseline --input data/generated/ibm_realistic_gnn_1246.csv --epochs 200 --hidden-dim 16 --metrics-output data/generated/gnn_realistic_metrics.json --report-output data/generated/GNN_REALISTIC_REPORT.md
```

Скопированные артефакты:

- `results/gnn_realistic_metrics.json`
- `results/GNN_REALISTIC_REPORT.md`

Подтверждённые метрики:

| Metric | Value |
|---|---:|
| transaction_nodes | 1246 |
| transaction_edges | 1177 |
| train_size | 873 |
| test_size | 373 |
| accuracy | 0.9357 |
| precision | 1.0000 |
| recall | 0.4146 |
| f1 | 0.5862 |
| roc_auc | 0.8830 |
| pr_auc | 0.6629 |

Baselines:

| Baseline | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| majority_class | 0.8901 | 0.0000 | 0.0000 | 0.0000 | 0.5757 | 0.1707 |
| feature_logistic_regression | 0.8847 | 0.0000 | 0.0000 | 0.0000 | 0.7782 | 0.3188 |

Вывод по этому запуску:

- на derived realistic IBM-format dataset GCN действительно лучше простых baseline-моделей;
- графовая структура даёт полезный сигнал;
- но recall остаётся умеренным, а сам dataset остаётся подготовленным экспериментальным набором, а не внешним production-like benchmark.

## GNN run на внешнем AMLSim `transactions.csv`

В проект был добавлен внешний набор:

- `backend/data/AMLSim CSV/transactions.csv`
- `backend/data/AMLSim CSV/alerts.csv`
- `backend/data/AMLSim CSV/accounts.csv`

Подтверждённые характеристики `transactions.csv`:

| Показатель | Значение |
|---|---:|
| total_rows | 1 323 234 |
| fraud_rows | 1 719 |
| tx_type | `TRANSFER` |
| timestamp_min | 0 |
| timestamp_max | 199 |

Полный файл нельзя честно прогонять через текущий NumPy GCN:

- текущая реализация использует плотную матрицу смежности;
- для full AMLSim это неадекватно по памяти;
- поэтому был добавлен отдельный AMLSim-path с подвыборкой для offline эксперимента.

Что добавлено:

- `backend/src/ml/amlsim_dataset.py`
- поддержка `--input-format amlsim` в `backend/src/ml/gnn_baseline.py`

Стратегия подвыборки:

- сохранить все fraud-транзакции;
- добрать benign-контекст, связанный с fraud accounts;
- ограничить размер подвыборки до управляемого уровня для dense NumPy GCN.

Команда describe-only:

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph\backend
$env:PYTHONPATH='C:\Users\Dankoff\PycharmProjects\aml-graph\backend'
.\.venv\Scripts\python.exe -m src.ml.gnn_baseline --input "data/AMLSim CSV/transactions.csv" --input-format amlsim --sample-size 5000 --time-window-seconds 3600 --describe-only
```

Подтверждённый summary:

| Показатель | Значение |
|---|---:|
| sampled_to | 5000 |
| selected_positive_rows | 1719 |
| selected_negative_rows | 3281 |
| fraud_account_count | 1639 |
| transaction_nodes | 5000 |
| transaction_edges | 637 |

Команда training:

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph\backend
$env:PYTHONPATH='C:\Users\Dankoff\PycharmProjects\aml-graph\backend'
.\.venv\Scripts\python.exe -m src.ml.gnn_baseline --input "data/AMLSim CSV/transactions.csv" --input-format amlsim --sample-size 5000 --time-window-seconds 3600 --epochs 200 --hidden-dim 16 --metrics-output data/generated/amlsim_5k_gnn_metrics.json --report-output data/generated/AMLSIM_5K_GNN_REPORT.md
```

Скопированные артефакты:

- `results/amlsim_5k_gnn_metrics.json`
- `results/AMLSIM_5K_GNN_REPORT.md`

Старые подтверждённые метрики до доработки:

| Metric | Value |
|---|---:|
| accuracy | 0.6560 |
| precision | 0.0000 |
| recall | 0.0000 |
| f1 | 0.0000 |
| roc_auc | 0.6479 |
| pr_auc | 0.4573 |

Baselines:

| Baseline | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| majority_class | 0.6560 | 0.0000 | 0.0000 | 0.0000 | 0.5114 | 0.3522 |
| feature_logistic_regression | 0.6560 | 0.0000 | 0.0000 | 0.0000 | 0.6102 | 0.4261 |

После доработки residual GCN, AMLSim 5k:

| Metric | Value |
|---|---:|
| transaction_nodes | 5000 |
| transaction_edges | 637 |
| feature_count | 16 |
| train_size | 3000 |
| validation_size | 1000 |
| test_size | 1000 |
| decision_threshold | 0.5509 |
| accuracy | 0.8580 |
| precision | 0.7317 |
| recall | 0.9273 |
| f1 | 0.8179 |
| roc_auc | 0.9377 |
| pr_auc | 0.8627 |
| top_100_precision | 0.9300 |

AMLSim 5k baselines:

| Baseline | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| majority_class | 0.6560 | 0.0000 | 0.0000 | 0.0000 | 0.4967 | 0.3454 |
| feature_logistic_regression | 0.8510 | 0.7044 | 0.9767 | 0.8185 | 0.9399 | 0.8573 |

AMLSim 10k:

| Metric | Value |
|---|---:|
| transaction_nodes | 10000 |
| transaction_edges | 2076 |
| feature_count | 16 |
| train_size | 6000 |
| validation_size | 2000 |
| test_size | 2000 |
| decision_threshold | 0.6863 |
| accuracy | 0.8735 |
| precision | 0.5946 |
| recall | 0.8314 |
| f1 | 0.6933 |
| roc_auc | 0.9322 |
| pr_auc | 0.7544 |
| top_100_precision | 0.9100 |

AMLSim 10k baselines:

| Baseline | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| majority_class | 0.8280 | 0.0000 | 0.0000 | 0.0000 | 0.4993 | 0.1723 |
| feature_logistic_regression | 0.8750 | 0.6175 | 0.7180 | 0.6640 | 0.9415 | 0.7736 |

Артефакты:

- `results/amlsim_5k_residual_gnn_metrics.json`
- `results/AMLSIM_5K_RESIDUAL_GNN_REPORT.md`
- `results/amlsim_10k_residual_gnn_metrics.json`
- `results/AMLSIM_10K_RESIDUAL_GNN_REPORT.md`

Вывод по AMLSim после доработки:

- GNN больше не уходит в all-negative prediction;
- на 5k модель даёт высокий recall и сильный top-k для расследования;
- на 10k residual GCN даёт лучший F1, чем feature-only baseline, но уступает ему по ROC-AUC/PR-AUC;
- это уже нормальный offline ML baseline, но ещё не runtime scorer.

## Решение по inference endpoint и frontend score

После этого запуска **не стоит** сразу добавлять GNN в runtime backend и frontend.

Причины:

1. Модель пока является offline baseline, а не стабилизированным inference-модулем.
2. Dataset подготовлен внутри проекта и полезен для эксперимента, но это ещё не внешний валидирующий benchmark.
3. Нет калибровки score, модели версий, сериализации, загрузки весов, inference latency measurement и деградационных тестов.
4. Текущий MVP уже имеет рабочий и объяснимый rule-based score.
5. Для диплома безопаснее и честнее описывать GNN как отдельный экспериментальный трек.
6. На внешнем AMLSim-подмножестве после доработки рабочая классификация появилась, но модель ещё не сериализуется, не калибруется и не обслуживается как runtime inference service.

Итоговое решение:

- inference endpoint для GNN сейчас не добавлять;
- GNN score во frontend сейчас не показывать;
- использовать GNN только как подтверждённый offline research module.

## Что можно писать в дипломе

- «В проекте реализован отдельный экспериментальный модуль подготовки transaction graph dataset и residual NumPy GCN baseline для анализа laundering labels на уровне транзакций».
- «Дополнительно подготовлен более реалистичный IBM-format dataset на базе реального IBM sample с инжекцией suspicious и benign структурных паттернов».
- «На этом датасете графовая модель показала лучшие метрики, чем majority и feature-only baseline, что подтверждает полезность графового контекста для задачи».
- «GNN не включён в runtime MVP и не используется для текущего operational risk scoring; он рассматривается как отдельное направление развития».
- «После доработки GNN pipeline на AMLSim-подвыборках модель перестала уходить в all-negative prediction и показала рабочие test-метрики, включая F1, recall и top-k precision».

## Что нельзя писать

- Нельзя писать, что GNN уже работает в web runtime.
- Нельзя писать, что GNN score показывается пользователю во frontend.
- Нельзя писать, что модель подтверждена на реальных банковских данных.
- Нельзя писать, что текущий offline baseline готов для продакшн-инференса.
