# Benchmark Report

## Machine

| Parameter | Value |
|---|---|
| platform | Windows-10-10.0.19045-SP0 |
| processor | Intel64 Family 6 Model 140 Stepping 1, GenuineIntel |
| cpu_count | 8 |

## Versions

| Package | Version |
|---|---|
| Python | 3.14.4 |
| Node | v24.15.0 |
| pandas | 3.0.2 |
| networkx | 3.6.1 |

## Command

```powershell
uv run python -m src.benchmark --input backend\tests\fixtures\ibm_aml_patterns.csv --results-dir results --sizes 1000,5000,10000 --layout-max-nodes 500
```

## Results

| Transactions | Nodes | Edges | Total s | Parse s | Build s | Detectors s | Scoring s | Layout s | Clustering | Clustering s | Alerts | Max risk | Errors |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---|
| 1000 | 1200 | 1000 | 5.2063 | 0.0169 | 0.0825 | 0.3047 | 0.0030 | 4.6714 | louvain | 0.0406 | 250 | 0.9987 |  |
| 5000 | 6000 | 5000 | 14.9171 | 0.0512 | 0.4320 | 9.4000 | 0.0162 | 4.5192 | wcc | 0.0460 | 1050 | 0.9987 |  |
| 10000 | 12000 | 10000 | 51.2487 | 0.0864 | 0.9039 | 44.4195 | 0.0342 | 4.8151 | wcc | 0.1082 | 2050 | 0.9987 |  |

## Bottlenecks

- Server-side layout dominates runtime on the measured synthetic graph. Use subgraphs or lower `--layout-max-nodes` for faster demo runs.
- Transit detection uses betweenness centrality and becomes visible in larger runs; it should stay approximate for bigger graphs.
- Clustering uses NetworkX Louvain on small graphs and WCC fallback on larger graphs to keep the MVP path responsive.
- 50 000 and 100 000 transaction runs are supported by CLI parameters but were not measured unless rows for those sizes appear in the table.

## Confirmed MVP Scale

- The confirmed scale is the largest completed row in the table above on this machine and this fixture expansion strategy.

## Confirmed Scope

- Results are measured on the local machine above.
- The benchmark expands the bundled IBM-format synthetic pattern fixture when requested size exceeds fixture size.
- Clustering is computed in the current backend pipeline.
- Layout uses the backend layout function with ForceAtlas2 when available and spring-layout fallback otherwise.
- These numbers describe the current MVP path, not production AML throughput.
