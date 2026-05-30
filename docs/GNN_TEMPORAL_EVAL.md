# GNN Temporal Evaluation

## Что проверялось

Для внешних IBM Small CSV была добавлена более строгая схема оценки GNN:

- `stratified` — обычный стратифицированный split;
- `temporal` — чистый split по времени;
- `temporal_stratified` — split по времени внутри каждого класса отдельно.

## Почему понадобился новый split

Чистый `temporal` для sampled IBM Small оказался некорректным как основной протокол оценки.

Причина:

- после сортировки транзакций по времени валидация и тест могли вырождаться в один класс;
- из-за этого получались искусственно идеальные метрики `f1 = 1.0`, `precision = 1.0`, `recall = 1.0`;
- такие результаты нельзя интерпретировать как честное качество модели.

## Что использовать дальше

Для внешнего IBM-эксперимента разумно использовать:

- `temporal_stratified` как более строгий и интерпретируемый split;
- `stratified` как baseline для сравнения.

Чистый `temporal` следует сохранять только как диагностический режим.

## Результаты

### HI-Small 10k, money_flow

| split_mode | F1 | Precision | Recall | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|
| `stratified` | `0.9705` | `0.9728` | `0.9681` | `0.9936` | `0.9855` |
| `temporal_stratified` | `0.9885` | `0.9828` | `0.9942` | `0.9995` | `0.9994` |
| `temporal` | `1.0000` | `1.0000` | `1.0000` | `n/a` | `1.0000` |

### LI-Small 10k, money_flow

| split_mode | F1 | Precision | Recall | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|
| `stratified` | `0.9478` | `0.9820` | `0.9158` | `0.9892` | `0.9828` |
| `temporal_stratified` | `0.9736` | `0.9630` | `0.9846` | `0.9969` | `0.9834` |
| `temporal` | `1.0000` | `1.0000` | `1.0000` | `n/a` | `1.0000` |

### HI-Medium 10k, money_flow, temporal_stratified

После исправления IBM sampler для случаев, когда число positive строк превышает `sample_size`,
получен двухклассовый набор `5000 positive / 5000 negative`.

| split_mode | F1 | Precision | Recall | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|
| `temporal_stratified` | `0.9871` | `0.9803` | `0.9940` | `0.9987` | `0.9989` |

## Интерпретация

1. GNN на внешнем IBM Small действительно показывает сильный сигнал.
2. Чистый `temporal` здесь нельзя считать честным основным протоколом.
3. Даже после перехода на `temporal_stratified` качество остаётся очень высоким.
4. После исправления sampler модель держит очень сильные метрики и на `HI-Medium 10k`.
5. Это означает, что модель не является пустой заглушкой, но итоговые выводы всё равно нужно проверять на более крупных прогонах и на benchmark-сценариях.

## Артефакты

- `backend/data/generated/hi_small_10k_money_flow_temporal_stratified_multiseed_summary.json`
- `backend/data/generated/HI_SMALL_10K_MONEY_FLOW_TEMPORAL_STRATIFIED_MULTI_SEED_REPORT.md`
- `backend/data/generated/li_small_10k_money_flow_temporal_stratified_multiseed_summary.json`
- `backend/data/generated/LI_SMALL_10K_MONEY_FLOW_TEMPORAL_STRATIFIED_MULTI_SEED_REPORT.md`
- `backend/data/generated/ibm_small_split_mode_comparison.json`
- `backend/data/generated/IBM_SMALL_SPLIT_MODE_COMPARISON.md`
- `backend/data/generated/hi_medium_10k_money_flow_temporal_stratified_multiseed_summary.json`
- `backend/data/generated/HI_MEDIUM_10K_MONEY_FLOW_TEMPORAL_STRATIFIED_MULTI_SEED_REPORT.md`
