# 04. Infrastructure For Beginner

## Что такое инфраструктура

Инфраструктура — это всё, что помогает приложению запускаться и работать: Docker, базы данных, очереди, переменные окружения, контейнеры.

## Что реально используется сейчас

| Компонент | Статус в текущем MVP |
|---|---|
| Docker Compose | Файл есть, но запуск не подтверждён из-за отсутствия Docker CLI |
| PostgreSQL | Не используется в runtime backend |
| Redis | Не используется в runtime backend |
| RabbitMQ | Не используется в runtime backend |
| Taskiq/worker | Не используется в runtime backend |
| LadybugDB | Не используется в runtime backend |
| In-memory storage | Используется для сессий |

## Что такое `.env`

`.env` — файл с настройками запуска: порты, имя приложения, режим debug. Пример лежит в `.env.example`.

Пример:

```text
APP_PORT=9090
FRONTEND_PORT=3000
NEXT_PUBLIC_API_BASE=http://127.0.0.1:9090
```

## Почему `0.0.0.0` и `127.0.0.1` отличаются

- `0.0.0.0` означает: сервер слушает все сетевые интерфейсы.
- `127.0.0.1` означает: клиент обращается к локальной машине.

Для backend host внутри сервера можно использовать `0.0.0.0`. Для браузера лучше использовать `127.0.0.1` или `localhost`.

## Docker Compose

Файл `docker-compose.yaml` сейчас описывает:

- backend;
- frontend;
- volumes для `.venv` и `node_modules`.

Проверка на машине с Docker:

```powershell
copy .env.example .env
docker compose -f docker-compose.yaml --env-file .env config
docker compose -f docker-compose.yaml --env-file .env up --build
```

## Что сказать на защите

«В текущем MVP backend использует in-memory storage, поэтому система демонстрационная и не претендует на промышленное хранение данных. Docker Compose описывает запуск backend и frontend, но внешние сервисы PostgreSQL/Redis/RabbitMQ не являются подтверждённой частью текущего runtime».
