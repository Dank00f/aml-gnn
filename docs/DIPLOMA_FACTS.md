# Diploma Facts

Только факты, подтверждённые кодом или локальным запуском в текущем checkout.

## Реально Реализовано

- Backend на FastAPI.
- Парсинг и валидация IBM Transactions for AML CSV через pandas.
- Нормализация account id в формате `bank:account`.
- Построение ориентированного `NetworkX MultiDiGraph`.
- Сохранение нескольких транзакций между одной парой accounts.
- Rule-based detectors:
  - cycles length 2-6;
  - fan-out;
  - transit;
  - shared device/IP при наличии соответствующих полей.
- Risk scoring на основе alerts:

```text
score = 1 - product(1 - alert_score_i)
```

- `Is Laundering` хранится как label и не используется в rule-based scoring.
- Server-side layout через NetworkX ForceAtlas2 при наличии и fallback на spring layout.
- Backend clustering для визуализации: Louvain на небольших графах, WCC fallback на крупных графах.
- SSE stream с progress events и graph chunks.
- Graph API: stats, graph, alerts, filters, subgraph.
- In-memory session storage.
- Frontend на Next.js/React/TypeScript/Radix UI/cosmos.gl.
- Upload page, graph page, sidebar filters, risk filter, pattern list, graph canvas, node details and раскрываемые transaction details for the selected node.
- Benchmark script, CSV output и Markdown report.
- Optional offline GNN dataset construction and NumPy GCN baseline for transaction-node classification experiments.

## Проверенные Команды

- `uv run pytest`: `48 passed in 1.09s`.
- `.venv\Scripts\ruff.exe check . --config=ruff.toml`: passed.
- `.venv\Scripts\ty.exe check`: passed.
- `.venv\Scripts\python.exe -m compileall src`: passed.
- `npm.cmd install`: passed, добавлена зависимость `@radix-ui/react-icons`.
- `npm.cmd run eslint-check`: passed.
- `npm.cmd run prettier-check`: passed.
- `npm.cmd run build`: passed.
- Browser smoke:
  - backend health returned `ok`;
  - frontend page opened at `http://127.0.0.1:3000`;
  - graph page showed `12 узлов · 10 рёбер`;
  - detector groups appeared in sidebar;
  - risk filter at 90% showed `7 из 12` nodes;
  - node details opened for `1:A001`;
  - cosmos canvas was present.
- API E2E smoke:
  - `backend/tests/test_e2e_mvp.py` passed;
  - проверяет IBM upload, stats, graph, alerts, filters, subgraph и SSE.
- Optional GNN dataset smoke:
  - describe-only CLI confirms dataset construction from IBM fixture;
  - expanded GNN run confirms 1000 transaction nodes, 1200 transaction edges, 8 features, 300 laundering labels.
- GNN smoke experiment:
  - trained `numpy_two_layer_gcn` on synthetic expansion to 1000 transaction nodes;
  - metrics saved to `results/gnn_metrics.json`;
  - test split contains 300 transaction nodes;
  - feature-only logistic regression baseline reaches the same metrics, so GNN advantage is not proven on this synthetic data.

## Benchmark

Результаты сохранены в:

- `results/benchmark_results.csv`;
- `results/BENCHMARK_REPORT.md`.

Подтверждённый успешный benchmark:

| Transactions | Nodes | Edges | Total seconds | Detectors seconds | Layout seconds | Clustering | Clustering seconds | Alerts |
|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 1 000 | 1 200 | 1 000 | 5.2063 | 0.3047 | 4.6714 | louvain | 0.0406 | 250 |
| 5 000 | 6 000 | 5 000 | 14.9171 | 9.4000 | 4.5192 | wcc | 0.0460 | 1 050 |
| 10 000 | 12 000 | 10 000 | 51.2487 | 44.4195 | 4.8151 | wcc | 0.1082 | 2 050 |

Команда:

```powershell
$env:PYTHONPATH='backend'
.\backend\.venv\Scripts\python.exe -m src.benchmark --input backend\tests\fixtures\ibm_aml_patterns.csv --results-dir results --sizes 1000,5000,10000 --layout-max-nodes 500
```

50 000 и 100 000 transactions в этом окружении не проверялись.

## Корректные Формулировки Для Диплома

- Backend реализует MVP pipeline для анализа транзакционного графа AML/anti-fraud.
- Risk score является индикатором внимания аналитика, не доказательством мошенничества.
- Повторные транзакции между одной парой счетов сохраняются за счёт `MultiDiGraph`.
- ForceAtlas2 используется как алгоритм визуальной раскладки, а не как AML detector.
- Для визуальной группировки backend рассчитывает clustering: Louvain для небольших графов и WCC fallback для крупных графов.
- Shared device/IP detector работает только на входных данных, где такие поля присутствуют.
- Текущий backend хранит результаты в памяти, поэтому данные сессий теряются при restart.
- Frontend визуализирует graph payload через cosmos.gl и получает данные по SSE.
- Frontend позволяет фильтровать визуализацию по минимальному risk score и открывать detail panel выбранного узла.
- Связанные транзакции доступны и раскрываются в detail panel выбранного узла; отдельный click по ребру на canvas не подтверждён.
- GNN можно описывать только как offline experimental NumPy GCN baseline: каждая транзакция является node, label берётся из `Is Laundering`, обучение не входит в web runtime.
- На текущем synthetic expansion NumPy GCN и feature-only baseline показывают одинаковые метрики; это подтверждает работоспособность experiment pipeline, но не превосходство GNN.

## Не Реализовано Или Не Подтверждено

- Excel upload.
- PostgreSQL persistence в текущем backend runtime.
- Redis/RabbitMQ/Taskiq worker pipeline в текущем backend runtime.
- LadybugDB или другое постоянное storage результатов в текущем backend runtime.
- AGC clustering в текущем backend pipeline.
- GNN scoring/training в backend runtime.
- Temporal slider.
- Export cases.
- Промышленная масштабируемость.
- Работа на реальных банковских данных.
- Benchmark на 50 000 и 100 000 transactions с чистым успешным завершением.
- Docker Compose запуск в текущем окружении, потому что Docker CLI не найден.
