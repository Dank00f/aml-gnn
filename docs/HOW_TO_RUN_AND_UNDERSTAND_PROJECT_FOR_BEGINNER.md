# Как Запустить И Понять Проект

Документ написан для Windows и PowerShell. Все команды выполняй из указанной папки.

## 1. Что нужно установить

| Программа | Зачем нужна | Как проверить |
|---|---|---|
| Python 3.14 | Запуск backend и тестов | `python --version` |
| uv | Установка Python-зависимостей backend | `uv --version` |
| Node.js 24 | Запуск frontend на Next.js | `node --version` |
| npm 11 | Установка frontend-зависимостей | `npm --version` |
| Git | Просмотр изменений и работа с репозиторием | `git --version` |
| Docker Desktop | Только если нужен Docker Compose | `docker --version` |
| VS Code или PyCharm | Удобное редактирование кода | открыть папку проекта |

В текущем проекте backend требует Python `>=3.14`, frontend требует Node `>24.0.0 <25.0.0`.

## 2. Как открыть проект

1. Распакуй архив проекта.
2. Открой папку `C:\Users\Dankoff\PycharmProjects\aml-graph` в IDE.
3. Открой PowerShell.
4. Перейди в корень проекта:

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph
```

5. Проверь, что ты в правильной папке:

```powershell
Get-ChildItem
```

Ожидаемые папки: `backend`, `frontend`, `docs`, `results`.

## 3. Что где лежит

| Путь | Что находится |
|---|---|
| `backend/src/main.py` | Точка входа FastAPI приложения |
| `backend/src/api/endpoints/v1` | HTTP и SSE endpoints |
| `backend/src/usecases` | Оркестрация pipeline upload/stream |
| `backend/src/graph` | IBM parser, graph builder, detectors, scoring, layout, clustering |
| `backend/src/ml` | Экспериментальный GNN dataset/entrypoint |
| `backend/tests` | Backend tests |
| `frontend/src/app` | Страницы Next.js |
| `frontend/src/components` | UI компоненты: upload, graph, sidebar, details |
| `frontend/src/lib` | API client и SSE client |
| `docker-compose.yaml` | Docker Compose только для backend/frontend |
| `results` | Benchmark, скриншоты и отчёты |

## 4. Как работает проект простыми словами

1. Пользователь выбирает CSV во frontend.
2. Frontend отправляет файл в backend.
3. Backend читает CSV через pandas.
4. Для IBM CSV backend нормализует поля в единую transaction schema.
5. Из транзакций строится `NetworkX MultiDiGraph`.
6. AML detectors ищут cycles, fan-out, transit и shared device/IP.
7. Risk scoring агрегирует alerts в score `[0, 1]`.
8. Clustering группирует узлы для визуального анализа.
9. Layout считает координаты узлов.
10. SSE stream отдаёт прогресс, chunks графа, detector results и `analysis_result`.
11. Frontend рисует граф через cosmos.gl.

## 5. Локальный запуск backend

Открой PowerShell:

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph\backend
uv sync
uv run python -m src.main
```

Ожидаемый результат: backend слушает порт `9090`.

Проверка во втором PowerShell:

```powershell
curl.exe http://127.0.0.1:9090/api/v1/health
```

Ожидаемый ответ:

```json
{"status":"ok"}
```

Swagger:

```text
http://127.0.0.1:9090/api/docs
```

## 6. Локальный запуск frontend

Открой второй PowerShell:

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph\frontend
npm.cmd install
npm.cmd run dev
```

Открой в браузере:

```text
http://127.0.0.1:3000
```

Если frontend не видит backend, проверь `.env.example` и `frontend/next.config.ts`. Для браузера нормальный адрес backend: `http://127.0.0.1:9090` или `http://localhost:9090`. Адрес `0.0.0.0` подходит серверу для прослушивания всех интерфейсов, но не является обычным адресом, по которому браузер должен ходить к API.

## 7. Как проверить backend

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph\backend
uv run pytest
.\.venv\Scripts\ruff.exe check . --config=ruff.toml
.\.venv\Scripts\ty.exe check
.\.venv\Scripts\python.exe -m compileall src
```

Последний подтверждённый результат: `48 passed in 1.09s`.

## 8. Как проверить frontend

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph\frontend
npm.cmd run eslint-check
npm.cmd run prettier-check
npm.cmd run build
```

Ожидаемый результат: команды завершаются без ошибок, `next build` показывает route `/` и `/graph/[sessionId]`.

## 9. Как запустить через Docker

В текущем окружении Docker CLI не найден, поэтому Docker Compose не подтверждён запуском. Статически конфигурация содержит только `backend` и `frontend`, без PostgreSQL, Redis, RabbitMQ и worker.

На машине с Docker Desktop:

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph
copy .env.example .env
docker compose -f docker-compose.yaml --env-file .env config
docker compose -f docker-compose.yaml --env-file .env up --build
```

Проверки:

```powershell
curl.exe http://127.0.0.1:9090/api/v1/health
```

Открыть frontend:

```text
http://127.0.0.1:3000
```

Остановить:

```powershell
docker compose -f docker-compose.yaml --env-file .env down
```

## 10. Как запустить benchmark

Из корня проекта:

```powershell
$env:PYTHONPATH='backend'
.\backend\.venv\Scripts\python.exe -m src.benchmark --input backend\tests\fixtures\ibm_aml_patterns.csv --results-dir results --sizes 1000,5000,10000 --layout-max-nodes 500
```

Результаты:

- `results/benchmark_results.csv`
- `results/BENCHMARK_REPORT.md`

## 11. Как проверить GNN задел

GNN не подключён к runtime backend. Реализована подготовка transaction graph dataset и offline NumPy GCN training command.

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph\backend
.\.venv\Scripts\python.exe -m src.ml.gnn_baseline --input tests/fixtures/ibm_aml_patterns.csv --describe-only
```

Ожидаемый смысл результата:

- количество transaction nodes;
- количество transaction edges;
- число признаков;
- количество laundering labels.

Training command:

```powershell
$env:PYTHONPATH='backend'
.\backend\.venv\Scripts\python.exe -m src.ml.gnn_baseline --input backend\tests\fixtures\ibm_aml_patterns.csv --expand-size 1000 --epochs 200 --hidden-dim 16 --metrics-output results\gnn_metrics.json --report-output results\GNN_EXPERIMENT_REPORT.md
```

Ожидаемый результат: JSON с метриками в консоли, файл `results/gnn_metrics.json` и отчёт `results/GNN_EXPERIMENT_REPORT.md`. Если feature-only baseline показывает те же метрики, это значит, что текущий synthetic dataset слишком простой для доказательства преимущества GNN.

## 12. Что говорить на защите

- «В приложении реализован полный MVP-пайплайн: загрузка CSV, построение мультиграфа, детекторы, risk score, layout, clustering и визуализация».
- «Повторные транзакции между одной парой счетов не теряются, потому что используется `MultiDiGraph`».
- «Risk score является индикатором внимания аналитика, а не доказательством преступления».
- «GNN вынесен в экспериментальный offline-модуль, чтобы не ломать основной backend; текущий baseline реализован на NumPy и не требует тяжёлых ML-зависимостей».
- «Docker Compose в текущей версии описывает backend и frontend; PostgreSQL/Redis/RabbitMQ не являются подтверждённым runtime MVP».
