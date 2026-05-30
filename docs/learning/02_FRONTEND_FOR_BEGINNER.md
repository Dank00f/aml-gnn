# 02. Frontend For Beginner

## Что такое frontend

Frontend — это часть приложения, которую видит пользователь в браузере. В этом проекте frontend отвечает за загрузку файла, отображение прогресса и визуализацию графа.

## Зачем он нужен в проекте

AML-граф трудно анализировать в виде таблицы. Frontend показывает связи между счетами, фильтры, подсветку паттернов и детали выбранного объекта.

## Технологии

| Технология | Простыми словами | Где используется |
|---|---|---|
| Next.js | Фреймворк для React-приложений | `frontend/src/app` |
| React | Библиотека UI-компонентов | `frontend/src/components` |
| TypeScript | JavaScript с типами | Почти все `.tsx/.ts` файлы |
| cosmos.gl | Рендеринг большого графа на canvas/WebGL | `GraphCanvas.tsx` |
| Radix UI | Готовые UI-компоненты | Sidebar, buttons, panels |

## Главные файлы

| Файл | За что отвечает |
|---|---|
| `frontend/src/app/page.tsx` | Главная страница загрузки |
| `frontend/src/app/graph/[sessionId]/page.tsx` | Страница анализа графа |
| `frontend/src/components/FileUploader.tsx` | Выбор и отправка CSV |
| `frontend/src/components/ColumnMapper.tsx` | Маппинг колонок custom CSV |
| `frontend/src/components/GraphCanvas.tsx` | Отрисовка графа |
| `frontend/src/components/Sidebar.tsx` | Фильтры, паттерны, risk filter |
| `frontend/src/components/DetailPanel.tsx` | Детали выбранного узла и операции |
| `frontend/src/lib/api-client.ts` | HTTP-запросы к backend |
| `frontend/src/lib/sse-client.ts` | Получение stream events |

## Как проверить

```powershell
cd frontend
npm.cmd run eslint-check
npm.cmd run prettier-check
npm.cmd run build
npm.cmd run dev
```

Открыть:

```text
http://127.0.0.1:3000
```

## Что сказать на защите

«Frontend реализован на Next.js и TypeScript. Для визуализации графа используется cosmos.gl, потому что он рассчитан на интерактивную отрисовку графовых структур в браузере. Пользователь может загрузить CSV, наблюдать прогресс обработки, фильтровать граф и смотреть детали узлов».

## Ограничения

- Отдельный click по ребру на canvas не подтверждён.
- Детали транзакций доступны через detail panel выбранного узла: карточку операции можно раскрыть.
- GNN score во frontend не отображается, потому что inference не реализован.
