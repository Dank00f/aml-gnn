# GNN Research Default

## Что выбрано как основной GNN-конфиг

Для дальнейшего исследовательского трека в проекте выбран такой конфиг:

- dataset: `AMLSim transactions.csv`
- sample size: `10000`
- graph mode: `money_flow`
- time window: `3600` seconds
- model: `residual_numpy_two_layer_gcn`
- hidden dim: `32`
- epochs: `120`
- learning rate: `0.03`
- weight decay: `0.001`
- multi-seed selection: `42,43,44`
- selected metric: `F1`

Причина выбора:

- на `10k` режим `money_flow` оказался лучшим по `F1` среди `shared_account`, `money_flow`, `hybrid`;
- на `10k` у него также лучшие `ROC-AUC` и `PR-AUC` среди сравниваемых режимов;
- этот режим лучше соответствует причинной логике движения средств, чем `shared_account`.

## Контролируемое сравнение режимов

### AMLSim 10k

| edge_mode | F1 | Precision | Recall | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|
| `money_flow` | `0.6987` | `0.7214` | `0.6773` | `0.9338` | `0.7460` |
| `shared_account` | `0.6710` | `0.6071` | `0.7500` | `0.9225` | `0.7299` |
| `hybrid` | `0.6570` | `0.5995` | `0.7267` | `0.9260` | `0.7310` |

### AMLSim 5k

| edge_mode | F1 | Precision | Recall | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|
| `shared_account` | `0.8156` | `0.7371` | `0.9128` | `0.9214` | `0.8362` |
| `money_flow` | `0.8030` | `0.6966` | `0.9477` | `0.9410` | `0.8771` |
| `hybrid` | `0.8025` | `0.7108` | `0.9215` | `0.9289` | `0.8559` |

Вывод:

- для `10k` основной режим: `money_flow`;
- для `5k` лучший по `F1`: `shared_account`;
- универсального победителя на всех масштабах нет.

## Лучший 10k run

Артефакты:

- `backend/data/generated/amlsim_10k_money_flow_multiseed/best_model.npz`
- `backend/data/generated/amlsim_10k_money_flow_multiseed/best_model.manifest.json`
- `backend/data/generated/amlsim_10k_money_flow_multiseed/best_metrics.json`
- `backend/data/generated/amlsim_10k_money_flow_multiseed_summary.json`

Best seed:

- `seed = 44`

Hold-out test metrics этого лучшего run:

- `accuracy = 0.8995`
- `precision = 0.7214`
- `recall = 0.6773`
- `f1 = 0.6987`
- `roc_auc = 0.9338`
- `pr_auc = 0.7460`
- `decision_threshold = 0.7208657085398444`

## Threshold study для лучшей 10k money_flow модели

Артефакты:

- `backend/data/generated/amlsim_10k_money_flow_thresholds.csv`
- `backend/data/generated/amlsim_10k_money_flow_thresholds_summary.json`
- `backend/data/generated/AMLSIM_10K_MONEY_FLOW_THRESHOLD_REPORT.md`

Важно:

- `best_metrics.json` описывает hold-out test split из training run;
- `thresholds_summary.json` описывает sweep по всей выбранной `10k` подвыборке;
- это разные режимы оценки, их нельзя смешивать в одну таблицу без пометки.

Что показал threshold sweep:

- model default threshold: `0.7208657085398444`
- best threshold on full-sample sweep: `0.75`
- best full-sample sweep F1: `0.7239`

Практический вывод:

- сохранённый threshold уже находится рядом с сильной рабочей зоной;
- грубой ошибки в выборе threshold нет;
- для диплома безопаснее использовать как основную цифру hold-out test метрики из `best_metrics.json`;
- threshold sweep следует описывать как дополнительный sensitivity analysis, а не как замену hold-out evaluation.

## Что можно считать research-default

Если нужен один основной GNN-конфиг для описания в дипломе:

- масштаб: `10k`
- graph mode: `money_flow`
- seed selection: multi-seed with best-by-F1
- reporting metric set:
  - `F1`
  - `precision`
  - `recall`
  - `ROC-AUC`
  - `PR-AUC`

Если нужен один основной threshold для inference-эксперимента:

- использовать threshold из лучшего hold-out run:
  - `0.7208657085398444`

Если нужен sensitivity discussion:

- дополнительно показать, что sweep по threshold даёт максимум около `0.75`.

## Что не утверждать

- Нельзя утверждать, что GNN уже встроен в runtime backend.
- Нельзя утверждать, что этот конфиг подтверждён на реальных банковских данных.
- Нельзя смешивать hold-out test metrics и full-sample threshold sweep как будто это один и тот же эксперимент.
