# Current Project And Frontend Audit

Дата проверки: 2026-05-27.

Цель документа: зафиксировать фактическое состояние проекта после объединения текущего backend с frontend из архива `aml-graph-main (2).zip`. Источник истины здесь - код, команды проверки и browser smoke, а не старые README или презентационные формулировки.

## 1. Краткий вывод

Frontend из архива восстановлен и подключен к текущему backend через совместимый API-клиент. Новый упрощенный frontend, который был создан ранее, удален из рабочей структуры `frontend/app`; вместо него используется полноценная структура `frontend/src` из архива.

Backend запускается, тесты backend проходят, production build frontend проходит. Browser smoke подтвердил, что страница графа открывается, SSE-поток получает результат, cosmos.gl canvas присутствует, UI показывает узлы, ребра, группы AML-паттернов, detail panel выбранного узла и фильтр по risk score. Backend API E2E закреплен отдельным тестом `backend/tests/test_e2e_mvp.py`.

Не подтверждены как готовые: Excel upload, PostgreSQL/Redis/RabbitMQ runtime, GNN scoring в web runtime, AGC clustering, Docker end-to-end, benchmark на 50 000/100 000 транзакций, полный ручной сценарий с выбором файла через браузерный file picker. Docker CLI в текущей машине не найден, поэтому `docker compose config/up` завершаются на отсутствии команды `docker`.

## 2. Фактическая структура

Основные части проекта:

```text
backend/
  src/
    api/endpoints/v1/
    graph/
    usecases/
    schemas/
    di/
  tests/

frontend/
  src/
    app/
    components/
    lib/
    types/

docs/
results/
```

Назначение:

- `backend/src/api/endpoints/v1` - HTTP и SSE endpoints.
- `backend/src/usecases` - orchestration upload/stream pipeline.
- `backend/src/graph` - IBM normalization, graph builder, detectors, scoring, layout, serialization.
- `frontend/src/app` - Next.js pages.
- `frontend/src/components` - UI: uploader, column mapper, graph canvas, sidebar, details, progress.
- `frontend/src/lib` - API client, SSE client, graph store.
- `docs` - проверенная документация по архитектуре, API и фактам для диплома.
- `results` - benchmark и screenshot smoke-проверки.

## 3. Frontend Audit

| Функция | Найдена в коде | Проверена запуском | Статус | Что важно |
|---|---:|---:|---|---|
| Next.js frontend из архива | Да, `frontend/src` | Да, `npm run build` | Работает | Starter frontend удален из `frontend/app` |
| Главная страница upload | Да, `frontend/src/app/page.tsx` | Build | Работает на уровне сборки | Полный file picker smoke не выполнялся |
| File uploader | Да, `frontend/src/components/FileUploader.tsx` | Build | Работает на уровне сборки | API client адаптирован под backend |
| Column mapper | Да, `frontend/src/components/ColumnMapper.tsx` | Build | Работает на уровне сборки | Убраны поля, которых нет в backend `ColumnMapping` |
| API client | Да, `frontend/src/lib/api-client.ts` | Build + browser smoke | Работает | Upload перенаправлен на `/api/v1/upload/ibm` и `/api/v1/upload` |
| SSE client | Да, `frontend/src/lib/sse-client.ts` | Browser smoke | Работает | Добавлен fallback через `fetch` stream, так как `EventSource` был недоступен в in-app browser |
| Graph page | Да, `frontend/src/app/graph/[sessionId]/page.tsx` | Browser smoke | Работает | Открывалась с реальным `session_id` backend |
| cosmos.gl canvas | Да, `frontend/src/components/GraphCanvas.tsx` | Browser smoke | Работает | На странице было 2 canvas |
| Progress UI | Да, `frontend/src/components/StreamProgress.tsx` | Browser smoke косвенно | Частично подтверждено | Страница получила completed result; пошаговую визуальную динамику отдельно не замерял |
| Pattern sidebar | Да, `frontend/src/components/Sidebar.tsx` | Browser smoke | Работает | UI показал cycle, fan-out, transit, shared identity groups |
| Risk filter | Да, `frontend/src/components/Sidebar.tsx` и `frontend/src/components/GraphCanvas.tsx` | Browser smoke | Работает | При пороге 90% UI показал `Показано 7 из 12`; узлы/ребра ниже порога скрываются визуально |
| Node details | Да, `frontend/src/components/DetailPanel.tsx` | Browser smoke | Работает | Клик по `1:A001` открыл risk score, финансовые потоки, alerts, атрибуты и соседей |
| Transaction details | Да, `frontend/src/components/DetailPanel.tsx` | Build | Работает на уровне сборки | В detail panel выбранного узла показываются и раскрываются связанные операции; отдельный click по ребру в cosmos.gl не реализован |
| Clustering UI/metadata | Да, `analysis_result` и `AnalysisMetadataPanel` | Build + backend SSE tests | Частично подтверждено | Backend отдаёт clustering; frontend принимает metadata, но отдельный browser smoke после clustering не запускался |
| Google fonts | Было | Build | Исправлено | Убрана зависимость от внешнего Google Fonts для offline build |

## 4. Backend Audit

| Функция | Найдена в коде | Проверена запуском | Статус | Что важно |
|---|---:|---:|---|---|
| Health endpoint | Да, `/api/v1/health` | Да | Работает | Возвращает `ok` |
| Generic CSV upload | Да, `/api/v1/upload` | Pytest | Работает по тестам | Использует column mapping |
| IBM CSV upload | Да, `/api/v1/upload/ibm` | Pytest + curl smoke | Работает | Возвращает `session_id` |
| IBM normalization | Да, `backend/src/graph/ibm.py` | Pytest | Работает | Composite account ids: `bank:account` |
| Graph builder | Да, `backend/src/graph/builder.py` | Pytest | Работает | Использует `MultiDiGraph`, повторные транзакции не теряются |
| Cycle detector | Да, `backend/src/graph/detectors.py` | Pytest + smoke | Работает | Циклы длины 2-6 |
| Fan-out detector | Да | Pytest + smoke | Работает | На synthetic fixture найден 1 паттерн |
| Transit detector | Да | Pytest + smoke | Работает | На synthetic fixture найдено 4 паттерна |
| Shared device/IP detector | Да | Pytest + smoke | Работает условно | Для IBM без device/IP возвращает пустой список |
| Risk scoring | Да, `backend/src/graph/scoring.py` | Pytest | Работает | Noisy-OR aggregation, score в диапазоне `[0, 1]` |
| Layout | Да, `backend/src/graph/layout.py` | Pytest + smoke | Работает | `spring_layout` fallback; ForceAtlas2 не внедрен как обязательная зависимость |
| Clustering | Да, `backend/src/graph/clustering.py` | Pytest + SSE tests | Работает | Louvain для небольших графов, WCC fallback для крупных |
| Graph serialization | Да, `backend/src/graph/serialization.py` | Pytest + smoke | Работает | Payload содержит nodes, edges, alerts |
| SSE | Да, `/api/v1/stream/{session_id}` | Pytest + browser smoke | Работает | Frontend получает completed graph result |
| Stats/graph/alerts API | Да, `/api/v1/sessions/...` | Pytest | Работает | Используется для API-доступа к session data |
| Benchmark script | Да, `backend/src/benchmark.py` | Да, 1k/5k/10k tx | Работает | Подтверждено до 10 000 транзакций на synthetic fixture expansion |
| API E2E smoke test | Да, `backend/tests/test_e2e_mvp.py` | Pytest | Работает | Upload IBM fixture -> stats/graph/alerts/filters/subgraph/SSE |
| Optional GNN dataset/training path | Да, `backend/src/ml/gnn_dataset.py`, `backend/src/ml/numpy_gcn.py`, `backend/src/ml/gnn_baseline.py` | Pytest + GNN smoke run | Работает как offline задел | NumPy GCN не подключен к backend runtime; feature-only baseline на synthetic expansion даёт те же метрики |
| Docker Compose | Да, `docker-compose.yaml`, `Dockerfile` | Нет | Не подтверждено | Docker CLI не найден в текущем окружении |
| Excel upload | Нет как подтвержденная функция | Нет | Не готово | Не заявлять как реализованное |
| PostgreSQL/Redis/RabbitMQ runtime | Не найден как реально используемый pipeline | Нет | Не готово | Не включать в факты MVP |
| GNN scoring | Нет в runtime | Нет | Roadmap | Можно делать только offline experiment после стабилизации MVP |
| AGC clustering | Не реализовано | Нет | Roadmap | Можно описывать только как дальнейшее развитие |

## 5. Исправленные frontend/backend несовпадения

В архивном frontend были ожидания старого API:

- `POST /api/v1/graph/processing/ibm`
- `POST /api/v1/graph/processing`
- `GET /api/v1/graph/{job_id}/stream`
- `GET /api/v1/algorithms`
- `GET /api/v1/graph/processing/latest`

В текущем backend реальные endpoints другие:

- `POST /api/v1/upload/ibm`
- `POST /api/v1/upload`
- `GET /api/v1/stream/{session_id}`
- `GET /api/v1/sessions/{session_id}/graph`
- `GET /api/v1/sessions/{session_id}/stats`
- `GET /api/v1/sessions/{session_id}/alerts`
- `GET /api/v1/sessions/{session_id}/filters`
- `GET /api/v1/sessions/{session_id}/subgraph`

Что сделано:

- `frontend/src/lib/api-client.ts` адаптирован к текущим upload endpoints.
- `frontend/src/lib/sse-client.ts` адаптирован к `/api/v1/stream/{session_id}`.
- SSE payload нормализуется для старого frontend store.
- Добавлен `fetch` streaming fallback для окружений без `EventSource`.
- `ColumnMapper` приведен к backend `ColumnMapping`.
- Next rewrite настроен на backend `http://127.0.0.1:9090`.
- `prettier-check` во frontend переведен с нестабильного pattern `.` на явные frontend globs.

## 6. Проверенные команды

Backend:

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph\backend
uv run pytest
```

Последний результат:

```text
48 passed in 1.09s
```

Static checks:

```text
ruff check: All checks passed
ty check: All checks passed
compileall src: passed
```

E2E API regression:

```text
backend/tests/test_e2e_mvp.py passed
```

Optional GNN dataset describe-only:

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph\backend
.\.venv\Scripts\python.exe -m src.ml.gnn_baseline --input tests/fixtures/ibm_aml_patterns.csv --describe-only
```

Результат:

```text
transaction_nodes=10
transaction_edges=12
feature_count=8
laundering_labels=3
```

Frontend:

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph\frontend
npm.cmd run eslint-check
npm.cmd run prettier-check
npm.cmd run build
```

Результат: все три команды завершились успешно.

Browser smoke:

- backend был запущен на `http://127.0.0.1:9090`;
- frontend был запущен на `http://127.0.0.1:3000`;
- IBM fixture была загружена через `/api/v1/upload/ibm`;
- страница `/graph/{session_id}` открылась;
- SSE result был получен;
- UI показал `12 узлов · 10 рёбер`;
- UI показал группы паттернов: cycle, fan-out, transit, shared identity;
- клик по подозрительному узлу `1:A001` открыл detail panel;
- risk filter при значении 90% показал `Показано 7 из 12`;
- screenshot сохранен в `results/frontend_merged_smoke.png`.

Benchmark:

```powershell
$env:PYTHONPATH='backend'
.\backend\.venv\Scripts\python.exe -m src.benchmark --input backend\tests\fixtures\ibm_aml_patterns.csv --results-dir results --sizes 1000,5000,10000 --layout-max-nodes 500
```

Результаты сохранены:

- `results/benchmark_results.csv`
- `results/BENCHMARK_REPORT.md`

Подтверждены прогоны на 1 000, 5 000 и 10 000 транзакций. Benchmark теперь включает clustering algorithm/time. 50 000 и 100 000 нельзя заявлять как подтвержденные.

## 7. Как запустить проект локально

Backend:

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph\backend
uv sync
uv run python -m src.main
```

Проверка backend:

```powershell
curl.exe http://127.0.0.1:9090/api/v1/health
```

Frontend:

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph\frontend
npm.cmd install
npm.cmd run dev
```

Открыть:

```text
http://127.0.0.1:3000
```

Тесты:

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph\backend
uv run pytest
```

Frontend build:

```powershell
cd C:\Users\Dankoff\PycharmProjects\aml-graph\frontend
npm.cmd run build
```

Docker Compose сейчас можно проверить только на машине с установленным Docker:

```powershell
copy .env.example .env
docker compose -f docker-compose.yaml --env-file .env config
docker compose -f docker-compose.yaml --env-file .env up --build
```

В текущем окружении команда `docker` не найдена, поэтому Docker не считается подтвержденным.

## 8. Что можно честно писать в дипломе

Подтвержденные формулировки:

- Реализован backend на FastAPI для загрузки CSV и построения транзакционного графа.
- Для IBM AML-like CSV реализована нормализация в единую схему транзакций.
- Счета представлены как вершины графа, транзакции - как направленные ребра.
- Для сохранения повторных переводов между одной парой счетов используется `networkx.MultiDiGraph`.
- Реализованы rule-based AML detectors: cycle, fan-out, transit, shared device/IP при наличии таких атрибутов.
- Risk score рассчитывается эвристически на основе найденных alert через Noisy-OR aggregation.
- Backend предрассчитывает координаты layout и сериализует graph payload для frontend.
- SSE endpoint передает прогресс и результат обработки во frontend.
- Frontend на Next.js и cosmos.gl отображает граф, статистику и группы найденных AML-паттернов.
- Реализован backend clustering для визуализации: Louvain на небольших графах и WCC fallback на крупных.
- GNN реализован как offline experimental dataset/entrypoint: transaction graph из транзакций, признаки транзакций и labels `Is Laundering`; NumPy GCN baseline не подключен к runtime backend.

Нельзя писать как готовое:

- Excel upload;
- GNN scoring в runtime;
- промышленная масштабируемость;
- PostgreSQL/Redis/RabbitMQ pipeline, если они не будут реально подключены и проверены;
- AGC clustering;
- производительность на 50000/100000 транзакций без реальных benchmark-результатов.

## 9. Ближайшие действия

Приоритет 1:

- Выполнить ручной frontend E2E через браузер: выбрать CSV через UI, дождаться graph page, проверить полный upload flow от file picker до graph page.
- Зафиксировать screenshot каждого ключевого состояния для диплома.
- Если нужен именно click по ребру на canvas, отдельно проверять поддержку этого сценария в `@cosmos.gl/graph`; сейчас транзакции раскрываются через detail panel выбранного узла.

Приоритет 2:

- PowerShell в этой среде может показывать UTF-8 текст как mojibake; исходники frontend проверены через Node как нормальный UTF-8. Если в обычном браузере появится битый текст, проверять конкретный файл через UTF-8 reader, а не по выводу PowerShell.
- Добавить минимальный Playwright smoke только если это не усложнит проект.
- Проверить Docker Compose отдельно; пока Docker end-to-end не подтвержден.

Приоритет 3:

- Для серьёзного GNN-эксперимента прогнать NumPy GCN на большем IBM/AMLSim CSV и сравнить с простыми baselines.
