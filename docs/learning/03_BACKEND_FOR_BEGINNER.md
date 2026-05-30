# 03. Backend For Beginner

## Что такое backend

Backend — это серверная часть приложения. Она принимает файлы, валидирует данные, строит граф, запускает алгоритмы и отдаёт результат frontend.

## Что такое FastAPI

FastAPI — Python-фреймворк для создания API. В проекте он создаёт HTTP endpoints для загрузки CSV, получения графа и SSE stream.

## Где начинается backend

| Файл | Назначение |
|---|---|
| `backend/src/main.py` | Создаёт FastAPI app и запускает uvicorn |
| `backend/src/api/endpoints/v1/upload.py` | Upload endpoints |
| `backend/src/api/endpoints/v1/stream.py` | SSE endpoint |
| `backend/src/api/endpoints/v1/sessions.py` | Stats/graph/alerts/filters/subgraph |
| `backend/src/usecases/upload_graph.py` | Главная обработка файла |
| `backend/src/usecases/stream_graph.py` | Подготовка stream events |

## Что такое endpoint

Endpoint — конкретный URL backend API. Например:

- `POST /api/v1/upload/ibm` — загрузить IBM CSV;
- `GET /api/v1/stream/{session_id}` — получить SSE stream;
- `GET /api/v1/sessions/{session_id}/graph` — получить граф;
- `GET /api/v1/health` — проверить, что backend жив.

## Как проверить backend

```powershell
cd backend
uv sync
uv run python -m src.main
```

Во втором PowerShell:

```powershell
curl.exe http://127.0.0.1:9090/api/v1/health
```

## Что сказать на защите

«Backend реализован на FastAPI. Он принимает CSV-файл, нормализует транзакции, строит граф в NetworkX, запускает детекторы, считает risk score, layout и clustering, после чего отдаёт результат через API и SSE».

## Ограничения

- Session storage находится в памяти.
- После restart backend результаты сессий теряются.
- PostgreSQL/Redis/RabbitMQ не используются в текущем runtime MVP.
