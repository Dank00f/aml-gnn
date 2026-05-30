# 01. Project Overview For Beginner

## Что это такое

Это веб-приложение для визуального расследования транзакций. Оно принимает CSV с переводами, строит граф счетов и показывает подозрительные структуры.

## Зачем это нужно

В AML/anti-fraud анализе важно видеть не только отдельную транзакцию, а связи между счетами: циклы, расщепление платежей, транзитные счета и общие устройства/IP.

## Где это находится в коде

| Часть | Путь |
|---|---|
| Backend | `backend/src` |
| Frontend | `frontend/src` |
| Graph analytics | `backend/src/graph` |
| API endpoints | `backend/src/api/endpoints/v1` |
| UI graph page | `frontend/src/app/graph/[sessionId]/page.tsx` |
| Документация | `docs` |

## Как проверить

Backend:

```powershell
cd backend
uv run pytest
uv run python -m src.main
```

Frontend:

```powershell
cd frontend
npm.cmd run build
npm.cmd run dev
```

## Что показать на защите

1. Загрузку CSV.
2. Построенный граф.
3. Найденные AML-паттерны.
4. Risk score.
5. Фильтр риска.
6. Детали выбранного узла и связанные транзакции.
7. Ограничения MVP.

## Что сказать комиссии

«Автором разработан MVP веб-инструмента для визуального анализа транзакционного графа. Система строит ориентированный мультиграф, запускает rule-based AML-детекторы, рассчитывает риск-оценку и визуализирует результат во frontend».
