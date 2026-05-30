# GNN Diploma Summary And Frontend Plan

## 1. Текущий статус GNN

GNN в проекте реализован как **отдельный offline ML-модуль**.

Он:

- не участвует в основном FastAPI upload pipeline;
- не заменяет текущий rule-based risk score;
- не нужен для работы текущего MVP backend/frontend;
- используется как исследовательский слой для отдельного обучения, сохранения модели, inference и quality evaluation.

## 2. Техническая реализация

### Что это за модель

Текущая модель не опирается на PyTorch Geometric или другую тяжёлую runtime-библиотеку.

Используется:

- самописный `NumPy`-baseline;
- transaction-node graph;
- residual two-layer GCN;
- train/validation/test split;
- class weighting;
- threshold tuning;
- multi-seed experiment runner;
- model persistence и offline predict.

Основные файлы:

- `backend/src/ml/gnn_dataset.py`
- `backend/src/ml/numpy_gcn.py`
- `backend/src/ml/gnn_baseline.py`
- `backend/src/ml/gnn_experiment.py`

## 3. Что подтверждено запуском

### AMLSim 10k, money_flow

- `F1 ≈ 0.6987`
- `Precision ≈ 0.7214`
- `Recall ≈ 0.6773`
- `ROC-AUC ≈ 0.9338`
- `PR-AUC ≈ 0.7460`

Это умеренно сильный результат, но не готовый production scorer.

### External IBM Small / Medium, money_flow, temporal_stratified

Подтверждённые сильные результаты:

- `HI-Small 10k`: `F1 ≈ 0.9885`
- `LI-Small 10k`: `F1 ≈ 0.9736`
- `HI-Medium 10k`: `F1 ≈ 0.9871`
- `LI-Medium 10k`: `F1 ≈ 0.9766`

Важно:

- чистый `temporal` split на sampled IBM Small оказался некорректным;
- для внешнего IBM-эксперимента рабочим протоколом зафиксирован `temporal_stratified`.

## 4. Benchmark-вывод

На sampled external IBM 10k узкие места backend/GNN-пути сейчас такие:

1. chunked sampling большого IBM CSV;
2. detectors, особенно transit-related часть;
3. layout остаётся заметным, но уже не главным bottleneck;
4. построение GNN transaction dataset занимает порядка `11 секунд` на sampled `10k`.

Это усиливает GNN как исследовательский слой, но не делает её автоматически лучшим runtime-путём для MVP.

## 5. Что можно честно писать в дипломе

Можно:

- реализован отдельный графовый ML-модуль для AML-экспериментов;
- используется transaction-node постановка;
- модель обучается offline;
- проведены сравнения режимов построения transaction graph;
- проведена более строгая temporal-style evaluation;
- получены измеренные метрики на AMLSim и внешних IBM CSV;
- rule-based backend остаётся основным operational контуром MVP.

Нельзя без дополнительной интеграции:

- писать, что GNN уже является основным scoring engine веб-приложения;
- писать, что frontend уже умеет переключаться на реальные GNN scores из backend runtime;
- писать, что inference встроен в upload/SSE pipeline.

## 6. Что уже подготовлено во frontend

Frontend уже подготовлен к мягкой интеграции второго score-слоя.

Сделано безопасное groundwork:

- тип `AnalysisResult` теперь допускает `gnn_scoring`;
- graph page понимает `ScoreMode = rule_based | gnn`;
- скрытый toggle появится только если backend реально пришлёт `gnn_scoring`;
- canvas, tooltip, detail panel и risk filter уже могут переключаться на активный score-слой.

То есть frontend теперь **готов к GNN score-layer**, но сам backend этот слой ещё не отправляет.

## 7. Как правильно интегрировать GNN во frontend дальше

### Минимальный корректный путь

1. Backend считает GNN inference offline или по отдельному endpoint.
2. Backend возвращает `analysis_result.gnn_scoring`.
3. Frontend показывает toggle:
   - `Rule`
   - `GNN`
4. При переключении меняются:
   - node size;
   - risk color/visibility;
   - tooltip score;
   - detail panel score;
   - risk filter count.

### Чего не стоит делать

- не смешивать rule-based score и GNN score в один непрозрачный показатель без отдельного объяснения;
- не подменять текущий `risk_score` молча;
- не встраивать GNN inference в upload path, пока не зафиксированы:
  - модель;
  - threshold;
  - preprocessing;
  - latency;
  - устойчивость на новых сплитах.

## 8. Практическая рекомендация

На текущем этапе:

- для MVP продукта оставить основной путь rule-based;
- GNN показывать как сильный исследовательский модуль;
- frontend уже подготовить под будущий score toggle, но не делать вид, что runtime-интеграция уже завершена.

Следующий разумный шаг:

1. добавить backend-контракт `gnn_scoring` в `analysis_result`;
2. не менять upload pipeline;
3. сначала сделать отдельный controlled inference path;
4. потом включить реальный toggle в UI на демонстрации.
