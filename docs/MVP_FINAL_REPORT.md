# Итог проверки AML-проекта

Дата: 2026-05-27.

Источник фактов: текущий код, локальные проверки, browser smoke, API E2E test и benchmark output в `results/`.

## 1. Что было обнаружено

| Проблема | Критичность | Статус |
|---|---|---|
| Текущий frontend был заменён starter-версией и не соответствовал архивному полноценному frontend | critical | Исправлено: восстановлен `frontend/src` из архива и адаптирован к backend |
| Архивный frontend ожидал старые endpoints `/api/v1/graph/processing/...` | critical | Исправлено в API/SSE clients |
| В frontend не было подтверждённого risk filter | major | Исправлено и проверено browser smoke |
| В detail panel не было явного списка и раскрываемых деталей связанных транзакций выбранного узла | major | Исправлено |
| Не было сквозного API E2E теста MVP-сценария | major | Исправлено |
| Clustering был заявлен, но не был подтверждён в backend pipeline | major | Исправлено: добавлен Louvain/WCC backend clustering и SSE `analysis_result` |
| GNN нельзя было заявлять как runtime-функцию | major | Исправлено: добавлен offline dataset и NumPy GCN baseline, без runtime scoring |
| Docker Compose не проверен | major | Не подтверждено: Docker CLI отсутствует в окружении |
| Старые benchmark-цифры были ограничены 1 000 транзакций | minor | Обновлено: подтверждены 1k/5k/10k |
| `prettier-check` иногда падал на pattern `.` в Windows/Codex окружении | minor | Исправлено явными globs |

## 2. Что исправлено

| Изменение | Файлы | Проверка |
|---|---|---|
| Восстановлен полноценный frontend из архива | `frontend/src/**`, удалён starter `frontend/app/**` | `npm.cmd run build`, browser smoke |
| Адаптирован frontend upload/SSE contract | `frontend/src/lib/api-client.ts`, `frontend/src/lib/sse-client.ts`, `frontend/next.config.ts` | browser smoke graph page |
| Добавлен risk filter | `frontend/src/components/Sidebar.tsx`, `frontend/src/components/GraphCanvas.tsx`, `frontend/src/app/graph/[sessionId]/page.tsx` | browser smoke: 90% -> `Показано 7 из 12` |
| Добавлены список и раскрываемые детали транзакций в detail panel | `frontend/src/components/DetailPanel.tsx` | `npm.cmd run build`, browser smoke node details |
| Добавлен API E2E test | `backend/tests/test_e2e_mvp.py` | `uv run pytest`, 48 passed |
| Добавлен backend clustering и SSE analysis payload | `backend/src/graph/clustering.py`, `backend/src/usecases/upload_graph.py`, `backend/src/usecases/stream_graph.py`, `frontend/src/lib/sse-client.ts` | `uv run pytest`, `npm.cmd run build` |
| Добавлен optional GNN baseline | `backend/src/ml/gnn_dataset.py`, `backend/src/ml/numpy_gcn.py`, `backend/src/ml/gnn_baseline.py`, `backend/tests/test_gnn_dataset.py` | pytest + GNN smoke CLI |
| Обновлён benchmark | `backend/src/benchmark.py`, `results/benchmark_results.csv`, `results/BENCHMARK_REPORT.md` | 1k/5k/10k successful |
| Обновлена документация | `README.md`, `backend/README.md`, `docs/*.md` | Ручная сверка с кодом и командами |

## 3. Что реально реализовано

- FastAPI backend.
- CSV upload для IBM Transactions for AML.
- Custom mapped CSV upload.
- pandas validation и normalization.
- `NetworkX MultiDiGraph`, сохраняющий повторные переводы между одной парой accounts.
- AML detectors:
  - cycles длины 2-6;
  - fan-out;
  - transit;
  - shared device/IP при наличии соответствующих полей.
- Rule-based risk scoring через Noisy-OR aggregation.
- Server-side layout: ForceAtlas2 через NetworkX при наличии, fallback на spring layout.
- Backend clustering: Louvain на небольших графах, WCC fallback на крупных графах.
- SSE stream: progress events, graph chunks, detector results, completed.
- Graph API: stats, graph, alerts, filters, subgraph.
- Next.js frontend с cosmos.gl.
- Sidebar filters, pattern groups, risk filter.
- Node detail panel, список связанных транзакций и раскрытие деталей операции.
- API E2E regression test.
- Benchmark script и реальные результаты в CSV/Markdown.
- Optional offline GNN dataset construction и NumPy GCN baseline.

## 4. Что не реализовано или не подтверждено

- Excel upload.
- PostgreSQL/Redis/RabbitMQ/Taskiq runtime.
- Persistent storage.
- Background worker queue.
- AGC clustering в backend pipeline.
- GNN training/scoring в backend runtime.
- Temporal slider.
- Export cases.
- Docker Compose запуск в текущем окружении.
- Benchmark на 50 000 и 100 000 транзакций.
- Отдельный click по ребру на canvas. Сейчас транзакции раскрываются через detail panel выбранного узла.

## 5. Результаты тестирования

Backend:

```powershell
cd backend
uv run pytest
```

Результат:

```text
48 passed in 1.09s
```

Backend static checks:

```powershell
cd backend
.\.venv\Scripts\ruff.exe check . --config=ruff.toml
.\.venv\Scripts\ty.exe check
.\.venv\Scripts\python.exe -m compileall src
```

Результат: все проверки прошли.

Frontend:

```powershell
cd frontend
npm.cmd run eslint-check
npm.cmd run prettier-check
npm.cmd run build
```

Результат: все проверки прошли.

Browser smoke:

- backend health вернул `{"status":"ok"}`;
- graph page открылась;
- UI показал `12 узлов · 10 рёбер`;
- sidebar показал cycle/fan-out/transit/shared identity groups;
- risk filter на 90% показал `Показано 7 из 12`;
- detail panel открылся для `1:A001`.

Infrastructure:

- Docker CLI не найден, Docker Compose не запускался.
- Локальный запуск backend/frontend проверен.

## 6. Реальные показатели производительности

Команда:

```powershell
$env:PYTHONPATH='backend'
.\backend\.venv\Scripts\python.exe -m src.benchmark --input backend\tests\fixtures\ibm_aml_patterns.csv --results-dir results --sizes 1000,5000,10000 --layout-max-nodes 500
```

| Transactions | Nodes | Edges | Total seconds | Detectors seconds | Layout seconds | Clustering | Clustering seconds | Alerts |
|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 1 000 | 1 200 | 1 000 | 5.2063 | 0.3047 | 4.6714 | louvain | 0.0406 | 250 |
| 5 000 | 6 000 | 5 000 | 14.9171 | 9.4000 | 4.5192 | wcc | 0.0460 | 1 050 |
| 10 000 | 12 000 | 10 000 | 51.2487 | 44.4195 | 4.8151 | wcc | 0.1082 | 2 050 |

Подтверждённый масштаб MVP на этой машине: 10 000 транзакций при `layout-max-nodes=500`.

Главное узкое место на 10k: transit detector, потому что он использует betweenness-related расчёты.

## 7. Что можно писать в дипломе

- Реализован веб-инструмент визуального AML-расследования транзакционного графа.
- Backend принимает CSV, валидирует данные, строит ориентированный мультиграф и сохраняет повторные транзакции.
- IBM-like CSV нормализуется в единую transaction schema.
- Rule-based detectors находят циклы, fan-out, transit nodes и shared identity при наличии device/IP.
- Для визуальной группировки backend рассчитывает clustering: Louvain на небольших графах и WCC fallback на крупных.
- Risk score является индикатором внимания аналитика, а не доказательством мошенничества.
- `Is Laundering` используется как label/evaluation field и не входит в rule-based score.
- Результаты передаются во frontend через SSE.
- Frontend отображает граф через cosmos.gl, показывает найденные паттерны, risk filter и детали выбранного узла.
- GNN описывать только как offline experimental NumPy GCN baseline, не как готовую runtime модель. На текущем synthetic expansion feature-only baseline показывает те же метрики, поэтому преимущество GNN не доказано.
- Подтверждённый benchmark: до 10 000 транзакций на локальной машине.

## 8. Что ещё мешает защите

- Нужно проверить Docker Compose на машине с Docker Desktop или убрать Docker из обязательного демо.
- Нужен ручной сценарий демонстрации через file picker в обычном браузере.
- Если требуется именно выбор ребра кликом на canvas, это отдельная frontend-задача; детали операций уже доступны через выбранный узел.
- Если в дипломе нужен именно AGC clustering, его нужно реализовать и протестировать отдельно; сейчас подтверждены Louvain/WCC.

## 9. Список изменённых файлов

Основные группы изменений:

- `.env.example`
- `README.md`
- `backend/README.md`
- `backend/src/benchmark.py`
- `backend/src/graph/*`
- `backend/src/ml/*`
- `backend/tests/*`
- `backend/tests/fixtures/*`
- `docs/*`
- `frontend/src/*`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/next.config.ts`
- `frontend/tsconfig.json`
- `results/*`

Точный список смотри через:

```powershell
git status --short
```

## 10. Команды для запуска и проверки

Backend:

```powershell
cd backend
uv sync
uv run python -m src.main
```

Frontend:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Backend tests:

```powershell
cd backend
uv run pytest
```

Frontend checks:

```powershell
cd frontend
npm.cmd run eslint-check
npm.cmd run prettier-check
npm.cmd run build
```

Benchmark:

```powershell
$env:PYTHONPATH='backend'
.\backend\.venv\Scripts\python.exe -m src.benchmark --input backend\tests\fixtures\ibm_aml_patterns.csv --results-dir results --sizes 1000,5000,10000 --layout-max-nodes 500
```

GNN smoke:

```powershell
cd backend
.\.venv\Scripts\python.exe -m src.ml.gnn_baseline --input tests/fixtures/ibm_aml_patterns.csv --describe-only
```

Docker check на машине с Docker:

```powershell
copy .env.example .env
docker compose -f docker-compose.yaml --env-file .env config
docker compose -f docker-compose.yaml --env-file .env up --build
```
