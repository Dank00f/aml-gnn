# Demo Readiness Report

Дата: 2026-05-27.

| Проверка | Команда/действие | Ожидаемый результат | Фактический результат | Статус | Если ошибка - что делать |
|---|---|---|---|---|---|
| Backend tests | `cd backend; uv run pytest` | Все тесты проходят | `48 passed in 1.09s` | Готово | Читать первый failing test и stack trace |
| Backend lint | `.\.venv\Scripts\ruff.exe check . --config=ruff.toml` из `backend` | `All checks passed` | `All checks passed` | Готово | Исправить файл и строку из вывода ruff |
| Backend type check | `.\.venv\Scripts\ty.exe check` из `backend` | `All checks passed` | `All checks passed` | Готово | Проверить типы в указанном файле |
| Python compile | `.\.venv\Scripts\python.exe -m compileall src` из `backend` | Все файлы компилируются | Успешно | Готово | Исправить syntax error |
| Frontend lint | `cd frontend; npm.cmd run eslint-check` | Нет ошибок ESLint | Успешно | Готово | Исправить компонент из вывода ESLint |
| Frontend format | `npm.cmd run prettier-check` из `frontend` | Все файлы отформатированы | Успешно | Готово | Выполнить `npm.cmd run prettier-fix` |
| Frontend production build | `npm.cmd run build` из `frontend` | Next.js build проходит | Успешно | Готово | Читать ошибку TypeScript или bundler |
| Backend health | `curl.exe http://127.0.0.1:9090/api/v1/health` | `{"status":"ok"}` | Ранее подтверждено browser/API smoke | Готово локально | Проверить, запущен ли backend |
| IBM upload API | `backend/tests/test_upload_ibm.py` | Возвращается `session_id` | Покрыто pytest | Готово | Проверить обязательные IBM columns |
| Generic upload API | `backend/tests/test_upload.py` | Custom mapping работает | Покрыто pytest | Готово | Проверить `ColumnMapping` |
| MultiDiGraph regression | `backend/tests/test_graph_builder.py` | Две операции между одной парой сохраняются | Покрыто pytest | Готово | Проверить graph builder |
| AML detectors | `backend/tests/test_detectors.py` | Cycle/fan-out/transit/shared identity находятся | Покрыто pytest | Готово | Проверить synthetic fixture |
| Risk score | `backend/tests/test_scoring.py` | Score в `[0, 1]`, Noisy-OR | Покрыто pytest | Готово | Проверить alert scores |
| Clustering | `backend/tests/test_clustering.py` | Labels есть для всех узлов | Покрыто pytest | Готово | Проверить `graph/clustering.py` |
| Layout payload | `backend/tests/test_layout_payload.py` | Узлы имеют `x/y` | Покрыто pytest | Готово | Проверить `graph/layout.py` |
| SSE contract | `backend/tests/test_stream.py` | Stream отдаёт progress, chunks, detectors, `analysis_result`, completed | Покрыто pytest | Готово | Проверить session storage |
| API E2E MVP | `backend/tests/test_e2e_mvp.py` | Upload -> stats/graph/alerts/filters/subgraph/SSE | Покрыто pytest | Готово | Проверить endpoints |
| Benchmark | `python -m src.benchmark ...` | CSV и Markdown отчёт | `results/benchmark_results.csv`, `results/BENCHMARK_REPORT.md` | Готово до 10k | Для 50k/100k запускать отдельно |
| GNN dataset | `python -m src.ml.gnn_baseline --describe-only` | Dataset summary | Покрыто тестами и smoke | Экспериментально | Проверить входной CSV |
| GNN training smoke | `python -m src.ml.gnn_baseline --input ... --expand-size 1000 --epochs 200 --metrics-output results/gnn_metrics.json --report-output results/GNN_EXPERIMENT_REPORT.md` | JSON metrics и Markdown report | Подтверждено на synthetic expansion до 1000 транзакций | Экспериментально | Не переносить метрики как production evidence; feature-only baseline даёт те же метрики |
| Docker Compose config | `docker compose ... config` | Валидная compose config | Команда не стартует: Docker CLI отсутствует | Блокер окружения | Установить Docker Desktop |
| Docker Compose up | `docker compose ... up --build` | Поднимаются backend/frontend | Команда не стартует: Docker CLI отсутствует | Блокер окружения | Проверить на машине с Docker |
| File picker UI | Ручная загрузка CSV в браузере | Переход на graph page | Полностью вручную не подтверждено после последних правок | Частично | Запустить backend/frontend и пройти сценарий |
| Transaction details | Раскрыть транзакцию в detail panel узла | Видны source/target, суммы, risk, label, attributes | Работает на уровне build; ручной UI smoke отложен | Частично | Пройти ручной demo-flow в конце |
| Edge click | Клик по ребру в canvas | Открываются details ребра | Не реализовано как отдельный сценарий | Roadmap | Сейчас транзакции раскрываются через node detail panel |

## Минимальный сценарий демо

1. Запустить backend.
2. Запустить frontend.
3. Открыть `http://127.0.0.1:3000`.
4. Загрузить CSV IBM формата.
5. Дождаться страницы графа.
6. Показать узлы, рёбра, alerts, risk filter.
7. Открыть подозрительный узел.
8. Показать связанные транзакции.
9. Показать вкладку кластеров и metadata.
10. Объяснить ограничения: in-memory storage, CSV-only, GNN offline, Docker не подтверждён в текущем окружении.
