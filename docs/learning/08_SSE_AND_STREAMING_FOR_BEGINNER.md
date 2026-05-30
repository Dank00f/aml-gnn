# 08. SSE And Streaming For Beginner

## Что такое SSE

SSE, Server-Sent Events, — способ, при котором backend держит HTTP-соединение открытым и постепенно отправляет события frontend.

## Зачем SSE в проекте

Обработка графа может занимать время. Пользователь должен видеть прогресс и постепенно получать данные, а не ждать молча.

## Где находится код

| Часть | Файл |
|---|---|
| Backend endpoint | `backend/src/api/endpoints/v1/stream.py` |
| Stream usecase | `backend/src/usecases/stream_graph.py` |
| Frontend client | `frontend/src/lib/sse-client.ts` |
| Progress UI | `frontend/src/components/StreamProgress.tsx` |

## Какие события есть

Основные события:

- `started`;
- `parsed`;
- `graph_built`;
- `layout_done`;
- `nodes_chunk`;
- `edges_chunk`;
- `detector_results`;
- `analysis_result`;
- `scoring_done`;
- `completed`;
- `error`.

## Как проверить

```powershell
cd backend
uv run pytest tests/test_stream.py
```

## Что сказать на защите

«SSE используется для передачи прогресса и результата обработки во frontend. Это делает интерфейс отзывчивым: frontend получает события pipeline и graph chunks по мере готовности».
