# GNN External Medium And Benchmark

## External IBM Medium: quality

### HI-Medium 10k

Конфиг:

- input: `HI-Medium_Trans.csv`
- sample size: `10000`
- graph mode: `money_flow`
- split mode: `temporal_stratified`
- seeds: `42,43,44`

Лучший run:

- `F1 = 0.9871`
- `Precision = 0.9803`
- `Recall = 0.9940`
- `ROC-AUC = 0.9987`
- `PR-AUC = 0.9989`

Sampling:

- `selected_rows = 10000`
- `selected_positive_rows = 5000`
- `selected_negative_rows = 5000`

Артефакты:

- `backend/data/generated/hi_medium_10k_money_flow_temporal_stratified_multiseed_summary.json`
- `backend/data/generated/HI_MEDIUM_10K_MONEY_FLOW_TEMPORAL_STRATIFIED_MULTI_SEED_REPORT.md`

### LI-Medium 10k

Конфиг:

- input: `LI-Medium_Trans.csv`
- sample size: `10000`
- graph mode: `money_flow`
- split mode: `temporal_stratified`
- seeds: `42,43,44`

Лучший run:

- `F1 = 0.9766`
- `Precision = 0.9722`
- `Recall = 0.9810`
- `ROC-AUC = 0.9985`
- `PR-AUC = 0.9984`

Артефакты:

- `backend/data/generated/li_medium_10k_money_flow_temporal_stratified_multiseed_summary.json`
- `backend/data/generated/LI_MEDIUM_10K_MONEY_FLOW_TEMPORAL_STRATIFIED_MULTI_SEED_REPORT.md`

## External IBM Small: backend benchmark

### HI-Small 10k sampled

- `total_seconds = 94.3205`
- `expand_seconds = 40.9405`
- `parse_seconds = 0.1573`
- `build_seconds = 1.7366`
- `gnn_dataset_seconds = 11.0391`
- `detectors_seconds ≈ 34.2642`
- `layout_seconds = 6.0519`
- `node_count = 9177`
- `edge_count = 10842`

Артефакты:

- `backend/data/generated/benchmark_external_hi_small/benchmark_results.csv`
- `backend/data/generated/benchmark_external_hi_small/BENCHMARK_REPORT.md`

### LI-Small 10k sampled

- `total_seconds = 146.3935`
- `expand_seconds = 57.0063`
- `parse_seconds = 0.1750`
- `build_seconds = 1.6135`
- `gnn_dataset_seconds = 10.9965`
- `detectors_seconds ≈ 70.7201`
- `layout_seconds = 5.7020`
- `node_count = 11319`
- `edge_count = 12959`

Артефакты:

- `backend/data/generated/benchmark_external_li_small/benchmark_results.csv`
- `backend/data/generated/benchmark_external_li_small/BENCHMARK_REPORT.md`

## Вывод

1. На external IBM Small и Medium текущий offline GNN показывает стабильно очень сильные метрики.
2. На benchmark-пути узким местом уже является не парсинг и не построение графа, а:
   - sampling из большого IBM CSV;
   - detectors, особенно transit-related часть.
3. Построение GNN transaction dataset на sampled `10k` занимает примерно `11 секунд`, что измеримо и воспроизводимо.
4. Эти результаты усиливают GNN как исследовательский модуль, но не отменяют того, что основной web MVP всё ещё разумно держать на rule-based backend path.
