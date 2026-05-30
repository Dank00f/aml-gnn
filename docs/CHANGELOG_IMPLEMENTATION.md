# Changelog Implementation

Этот файл фиксирует изменения по ТЗ из `Codex_prompt_AML_full_project_GNN_beginner.txt`.

| Этап | Проблема | Изменённые файлы | Решение | Как проверено | Не потерян ли старый функционал |
|---|---|---|---|---|---|
| Аудит frontend | В рабочем проекте был упрощённый frontend, хуже архивного | `frontend/src/**`, `frontend/app/**` | Восстановлена полноценная структура `frontend/src` из архивного frontend; starter `frontend/app` удалён из активной структуры | `npm.cmd run build`, browser smoke | Сохранены upload page, graph page, GraphCanvas, Sidebar, DetailPanel, SSE client |
| API contract | Архивный frontend ожидал старые endpoints | `frontend/src/lib/api-client.ts`, `frontend/src/lib/sse-client.ts`, `frontend/next.config.ts` | Frontend подключён к реальным backend endpoints `/api/v1/upload`, `/api/v1/upload/ibm`, `/api/v1/stream/{session_id}` | `npm.cmd run build`, browser smoke | Старый UI сохранён, изменён только слой API |
| Custom mapping | Поля frontend не совпадали с backend `ColumnMapping` | `frontend/src/components/ColumnMapper.tsx`, `frontend/src/types/api/column-mapping.ts` | Маппинг приведён к фактическому backend contract | `npm.cmd run build` | Custom CSV flow не удалён |
| Risk filter | Фильтр риска был не подтверждён как рабочий сценарий | `frontend/src/components/Sidebar.tsx`, `frontend/src/components/GraphCanvas.tsx`, `frontend/src/app/graph/[sessionId]/page.tsx` | Добавлена фильтрация отображаемых узлов/рёбер по минимальному risk score | Browser smoke: порог 90% показал `7 из 12` | Остальные фильтры и pattern toggles сохранены |
| Transaction details | Не было явного списка и раскрываемых деталей связанных операций выбранного узла | `frontend/src/components/DetailPanel.tsx` | Добавлен список входящих/исходящих транзакций и раскрытие конкретной операции | `npm.cmd run build`, browser smoke node details | Node details сохранены и расширены |
| Graph model | Повторные транзакции могли быть критичным риском потери данных | `backend/src/graph/builder.py`, `backend/tests/test_graph_builder.py` | Закреплён `NetworkX MultiDiGraph` и regression test на две операции между одной парой счетов | `uv run pytest` | Existing upload и stream tests проходят |
| Detectors/scoring | Нужно подтвердить AML detectors и scoring тестами | `backend/src/graph/detectors.py`, `backend/src/graph/scoring.py`, `backend/tests/test_detectors.py`, `backend/tests/test_scoring.py` | Уточнены устойчивость и проверяемость detectors/scoring | `uv run pytest` | Старые detector contracts сохранены |
| Clustering | Clustering был заявлен, но не подтверждён backend pipeline | `backend/src/graph/clustering.py`, `backend/src/usecases/upload_graph.py`, `backend/src/usecases/stream_graph.py`, `frontend/src/lib/sse-client.ts`, `frontend/src/types/graph/analysis.ts` | Добавлен Louvain для небольших графов и WCC fallback для крупных, payload идёт через SSE `analysis_result` | `uv run pytest`, `npm.cmd run build` | AGC не симулируется; отмечен как roadmap |
| Benchmark | Не было воспроизводимого benchmark отчёта для диплома | `backend/src/benchmark.py`, `backend/tests/test_benchmark.py`, `results/benchmark_results.csv`, `results/BENCHMARK_REPORT.md` | Добавлен benchmark CLI с измерением parse/build/detectors/scoring/layout/clustering | Benchmark run 1k/5k/10k | Runtime backend не зависит от benchmark |
| GNN задел | GNN нельзя заявлять как готовую runtime модель | `backend/src/ml/gnn_dataset.py`, `backend/src/ml/numpy_gcn.py`, `backend/src/ml/gnn_baseline.py`, `backend/tests/test_gnn_dataset.py` | Добавлен offline dataset и NumPy GCN baseline без обязательной runtime dependency | `uv run pytest`, GNN smoke CLI | Upload endpoint не запускает GNN |
| Документация | README/документы расходились с кодом | `README.md`, `backend/README.md`, `docs/*.md` | Документы обновлены по фактическому коду и проверкам | Ручная сверка + tests/build | Неподтверждённые функции помечены как ограничения |

## Конфликты и выбранные решения

| Конфликт | Варианты | Выбранное решение | Почему |
|---|---|---|---|
| Excel upload заявлялся в ранних формулировках, но `openpyxl` не является обязательной зависимостью | Добавить `openpyxl`; убрать Excel claim | Убрать Excel claim из фактов MVP | CSV закрывает основной сценарий, новая dependency не нужна без тестов |
| ForceAtlas2 как обязательный layout может быть проблемным на Windows | Добавить тяжёлую dependency; использовать NetworkX при наличии и fallback | ForceAtlas2 через NetworkX API при наличии, fallback spring layout | MVP должен запускаться стабильно |
| GNN training на PyTorch/PyG усложняет установку | Добавить обязательные ML dependencies; сделать NumPy offline baseline | NumPy GCN baseline, без runtime dependency | Основной backend не должен ломаться из-за ML стека |
| Docker Compose заявляет только backend/frontend, а не PostgreSQL/Redis/RabbitMQ | Добавить сервисы искусственно; честно описать фактическую конфигурацию | Не добавлять неиспользуемые сервисы | Документация должна соответствовать коду |
