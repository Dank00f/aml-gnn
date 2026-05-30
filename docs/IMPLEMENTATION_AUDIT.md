# Implementation Audit

Дата перепроверки: 2026-05-27  
Рабочая директория: `C:\Users\Dankoff\PycharmProjects\aml-graph`

Источник статусов ниже - текущий код, локальные команды проверки и browser smoke.

## Что изменилось после сравнения с архивом

Архив `D:\сюда качается хуйня\aml-graph-main (2).zip` содержит полноценный frontend в `frontend/src/...`. Этот frontend перенесён в текущий проект и адаптирован к текущему backend API.

Сделано:

- удалена стартовая `frontend/app`;
- добавлена архивная `frontend/src`;
- добавлена зависимость `@radix-ui/react-icons`;
- `frontend/src/lib/api-client.ts` переключён с архивных `/api/v1/graph/processing/...` на текущие `/api/v1/upload...`;
- `frontend/src/lib/sse-client.ts` переключён на `/api/v1/stream/{session_id}`;
- добавлен fallback на `fetch` streaming, если в браузере нет `EventSource`;
- custom CSV mapper приведён к текущему `ColumnMapping` backend;
- отключён `next/font/google`, чтобы production build не зависел от доступа к `fonts.gstatic.com`;
- `prettier-check` во frontend переведён с pattern `.` на явные globs, чтобы команда стабильно работала в Windows/Codex окружении.

## Проверенные Команды

| Команда | Результат |
|---|---|
| `uv run pytest` из `backend` | `48 passed` |
| `.venv\Scripts\ruff.exe check . --config=ruff.toml` из `backend` | `All checks passed` |
| `.venv\Scripts\ty.exe check` из `backend` | `All checks passed` |
| `.venv\Scripts\python.exe -m compileall src` из `backend` | успешно |
| `npm.cmd install` из `frontend` | успешно, `3 vulnerabilities` от npm audit остаются |
| `npm.cmd run eslint-check` из `frontend` | успешно |
| `npm.cmd run prettier-check` из `frontend` | успешно |
| `npm.cmd run build` из `frontend` | успешно |
| `GET /api/v1/health` | `{"status":"ok"}` |
| browser smoke `/graph/{session_id}` | показаны `12 узлов · 10 рёбер`, detector groups, canvas |
| browser smoke risk filter | при пороге 90% показано `7 из 12` узлов |
| browser smoke node details | клик по `1:A001` открыл detail panel с risk score, потоками, alerts и соседями |
| API E2E smoke | `backend/tests/test_e2e_mvp.py` проверяет upload -> stats -> graph -> alerts -> filters -> subgraph -> SSE |
| Optional GNN smoke | NumPy GCN CLI на `--expand-size 1000` вернул 1000 transaction nodes, 1200 transaction edges, 8 features, 300 labels и сохранил `results/gnn_metrics.json` |
| Docker CLI | команда `docker` не найдена | 

## Матрица Функций

| Функция | Заявлена | Найдена в коде | Проверена запуском | Статус | Что исправить |
|---|---|---|---|---|---|
| Backend FastAPI | да | `backend/src/main.py`, routers `api/v1` | да | работает | Нет критичных правок |
| Backend tests | да | `backend/tests` | да, `48 passed` | работает | Поддерживать regression suite |
| IBM AML CSV upload | да | `POST /api/v1/upload/ibm`, `graph/ibm.py` | да, tests/browser smoke | работает | Нет критичных правок |
| Custom CSV upload | да | `POST /api/v1/upload` | да, tests | работает | UI mapper адаптирован |
| Excel upload | местами заявлен | backend отвергает `.xlsx/.xls` | да, test на отказ | не реализовано | Не заявлять как готовое |
| IBM normalization | да | `normalize_ibm_transactions` | да, tests | работает | Нет критичных правок |
| `MultiDiGraph` и повторные транзакции | да | builder сохраняет parallel edges | да, regression test | работает | Нет критичных правок |
| Cycle detector | да | `detect_cycles`, cycles 2-6 | да, tests | работает | Нет критичных правок |
| Fan-out detector | да | `detect_fanout` | да, tests/browser smoke | работает | Нет критичных правок |
| Transit detector | да | `detect_transit` | да, tests/browser smoke | работает | Для больших графов нужен benchmark |
| Shared device/IP detector | да | `detect_shared_device` | да, tests | работает при наличии полей | Чистый IBM CSV таких полей не содержит |
| Risk scoring | да | `apply_alert_scores`, Noisy-OR aggregation | да, tests/browser smoke | работает | Описывать как risk indicator |
| Graph serialization payload | да | `graph/serialization.py` и SSE DTO | да | работает | Нет критичных правок |
| Server-side layout | да | `graph/layout.py` | да, tests/browser smoke | работает | Layout доминирует benchmark runtime |
| ForceAtlas2 | да | `nx.forceatlas2_layout` с fallback | да косвенно | работает при наличии в NetworkX | Описывать как layout algorithm |
| Clustering Louvain/WCC | да | `backend/src/graph/clustering.py` | да, tests + SSE contract | работает | AGC остаётся roadmap |
| SSE stream | да | `GET /api/v1/stream/{session_id}` | да, tests/browser smoke | работает | Нет критичных правок |
| Backend API E2E | требуется для MVP | `backend/tests/test_e2e_mvp.py` | да, `uv run pytest` | работает | Нет критичных правок |
| Frontend upload flow | да | `frontend/src/components/FileUploader.tsx` | build/browser smoke страницы | работает на уровне UI/API client | Полный ручной file upload smoke можно повторить локально |
| Frontend SSE client | да | `frontend/src/lib/sse-client.ts` | да, browser smoke | работает | Нет критичных правок |
| Frontend graph visualization | да | `frontend/src/components/GraphCanvas.tsx` | да, canvas present | работает | Дальше проверить UX на больших графах |
| Frontend filters/sidebar | да | `Sidebar.tsx`, `GraphCanvas.tsx` | да, sidebar показал detector groups, risk filter изменил счётчик до `7 из 12` | работает | Нет критичных правок |
| Frontend node/transaction details | да | `DetailPanel.tsx` | да, build после раскрываемых деталей операций | работает | Отдельный click по ребру на canvas не реализован |
| PostgreSQL/Redis/RabbitMQ/Taskiq | заявлено в архивной архитектуре | в текущем runtime не используется | нет | не реализовано в текущем runtime | Не указывать как фактический runtime |
| GNN scoring | упоминается как будущая возможность | runtime scoring не найден | нет | не реализовано в web runtime | Roadmap/offline experiment |
| Optional GNN baseline | roadmap | `backend/src/ml/gnn_dataset.py`, `backend/src/ml/numpy_gcn.py`, `backend/src/ml/gnn_baseline.py` | да, tests + GNN smoke CLI | offline задел | Runtime scoring не реализован |
| Benchmark script | требуется | `backend/src/benchmark.py` | да, 1k/5k/10k run | работает | 50k/100k не подтверждены |
| Docker Compose | есть в репозитории | `docker-compose.yaml`, `Dockerfile` | нет, Docker CLI отсутствует | не подтверждено | Проверить на машине с Docker |

## Основные Оставшиеся Риски

- Текущий backend in-memory, без persistent storage.
- Архивный frontend был адаптирован к текущему backend, но не весь архивный backend/worker stack перенесён.
- Clustering result приходит через SSE `analysis_result`; отдельный browser smoke после добавления clustering не запускался.
- In-app browser не поддерживает `EventSource`; поэтому добавлен `fetch` streaming fallback.
- PowerShell в текущей среде может отображать UTF-8 как mojibake. Исходники frontend проверены через Node как нормальный UTF-8; это не считается дефектом кода.
- Docker CLI в текущей машине не установлен или не доступен через `PATH`; Docker Compose нельзя считать проверенным.
- GNN dataset construction и NumPy GCN smoke подтверждены; GNN scoring не является частью MVP runtime.
