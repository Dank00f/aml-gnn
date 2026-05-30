# AML Graph

MVP дипломного проекта для визуального AML/anti-fraud анализа транзакционного графа.

Текущий проверенный состав:

- FastAPI backend;
- pandas parser для IBM Transactions for AML CSV;
- NetworkX `MultiDiGraph`;
- rule-based detectors: cycles, fan-out, transit, shared device/IP;
- risk scoring по alerts;
- clustering: Louvain на небольших графах и WCC fallback на крупных;
- server-side layout;
- SSE stream;
- frontend из архивной версии проекта на Next.js + React + TypeScript + cosmos.gl;
- frontend risk filter, detail panel выбранного узла и раскрываемые детали связанных транзакций;
- backend tests;
- benchmark script.
- optional offline GNN dataset and NumPy GCN baseline.

## Стек

Backend:

- Python 3.14;
- FastAPI;
- pandas;
- NetworkX;
- Pydantic;
- SSE;
- in-memory session storage;
- pytest, ruff, ty.

Frontend:

- Next.js 16;
- React 19;
- TypeScript;
- Radix UI;
- Tailwind CSS;
- `@cosmos.gl/graph`.

Не используется в текущем backend runtime: PostgreSQL, Redis, RabbitMQ, Taskiq, LadybugDB, GNN training/inference.

## Запуск Backend

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph\backend
uv sync
uv run python -m src.main
```

Проверка:

```powershell
Invoke-RestMethod http://127.0.0.1:9090/api/v1/health
```

Ожидаемый ответ:

```json
{"status":"ok"}
```

## Запуск Frontend

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph\frontend
npm.cmd install
npm.cmd run dev
```

Открыть:

```text
http://127.0.0.1:3000
```

Frontend ожидает backend на:

```text
http://127.0.0.1:9090
```

Это задано в `.env.example` через `NEXT_PUBLIC_API_BASE`.

## CSV Формат

Основной endpoint:

```http
POST /api/v1/upload/ibm
```

Ожидаемые IBM columns:

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

Нормализация:

- `sender_id = From Bank + ":" + Account`;
- `receiver_id = To Bank + ":" + Account.1`;
- `amount = Amount Paid`;
- `Is Laundering` хранится как label и не используется в rule-based scoring.

Excel upload не включён. `.xlsx/.xls` сейчас roadmap.

## API

См. [docs/API_AND_SSE_CONTRACT.md](docs/API_AND_SSE_CONTRACT.md).

Основные endpoints:

```text
POST /api/v1/upload/ibm
POST /api/v1/upload
GET  /api/v1/stream/{session_id}
GET  /api/v1/sessions/{session_id}/stats
GET  /api/v1/sessions/{session_id}/graph
GET  /api/v1/sessions/{session_id}/alerts
GET  /api/v1/sessions/{session_id}/filters
GET  /api/v1/sessions/{session_id}/subgraph?node_id=...&k=2
```

Frontend адаптирован к этому контракту. Архивный frontend изначально ожидал `/api/v1/graph/processing/...`, но сейчас клиентские функции переподключены на текущие backend endpoints.

SSE также отдаёт `analysis_result` с cluster labels и node scoring для вкладки кластеров во frontend.

## Проверки

Backend:

```powershell
cd backend
uv run pytest
uv run ruff check . --config=ruff.toml
uv run ty check
```

Frontend:

```powershell
cd frontend
npm.cmd run eslint-check
npm.cmd run prettier-check
npm.cmd run build
```

API E2E smoke:

```powershell
cd backend
uv run pytest tests/test_e2e_mvp.py
```

## Docker

В репозитории есть `Dockerfile` и `docker-compose.yaml` для backend и frontend:

```powershell
copy .env.example .env
docker compose -f docker-compose.yaml --env-file .env config
docker compose -f docker-compose.yaml --env-file .env up --build
```

В текущем окружении Docker CLI не найден, поэтому Docker Compose не был подтверждён запуском. PostgreSQL, Redis, RabbitMQ и worker в текущий compose не входят.

## Optional GNN Dataset

GNN не подключён к runtime backend и не используется в upload pipeline. Сейчас есть offline NumPy GCN baseline, где каждая транзакция становится node, а `Is Laundering` используется как transaction-level label. Результаты текущего smoke-эксперимента сохранены в `results/gnn_metrics.json` и `results/GNN_EXPERIMENT_REPORT.md`; это маленький synthetic fixture, не production evidence.

Проверить построение dataset:

```powershell
cd backend
.\.venv\Scripts\python.exe -m src.ml.gnn_baseline --input tests/fixtures/ibm_aml_patterns.csv --describe-only
```

Запустить NumPy GCN smoke-обучение:

```powershell
$env:PYTHONPATH='backend'
.\backend\.venv\Scripts\python.exe -m src.ml.gnn_baseline --input backend\tests\fixtures\ibm_aml_patterns.csv --expand-size 1000 --epochs 200 --hidden-dim 16 --metrics-output results\gnn_metrics.json --report-output results\GNN_EXPERIMENT_REPORT.md
```

GNN training остаётся offline-экспериментом и не входит в upload pipeline. На текущем synthetic expansion feature-only baseline показывает те же метрики, поэтому преимущество GNN не доказано.

## Benchmark

```powershell
$env:PYTHONPATH='backend'
.\backend\.venv\Scripts\python.exe -m src.benchmark --input backend\tests\fixtures\ibm_aml_patterns.csv --results-dir results --sizes 1000,5000,10000 --layout-max-nodes 500
```

Outputs:

- `results/benchmark_results.csv`;
- `results/BENCHMARK_REPORT.md`.

Текущий успешный benchmark подтверждён на 1 000, 5 000 и 10 000 transactions. 50 000 и 100 000 transactions не проверены и не должны заявляться без свежего результата в `results/`.

## Ограничения

- Session storage находится в памяти.
- Session results теряются при restart backend.
- Нет фоновой очереди задач в текущем backend runtime.
- Нет persistent database в текущем backend runtime.
- Нет AGC clustering в текущем backend pipeline.
- Нет GNN scoring.
- Shared device/IP detector пуст для чистого IBM CSV без таких колонок.
- NetworkX и server-side layout ограничивают масштаб.
