from pathlib import Path

from src.benchmark import run_benchmark


def test_benchmark_writes_results(tmp_path: Path) -> None:
    rows = run_benchmark(
        input_path=Path('tests/fixtures/ibm_aml_patterns.csv'),
        results_dir=tmp_path,
        sizes=[10],
        layout_max_nodes=20,
    )

    assert len(rows) == 1
    assert rows[0]['transaction_count'] == 10
    assert rows[0]['edge_count'] == 10
    assert rows[0]['gnn_dataset_seconds'] >= 0.0
    assert rows[0]['total_alerts'] > 0
    assert (tmp_path / 'benchmark_results.csv').exists()
    assert (tmp_path / 'BENCHMARK_REPORT.md').exists()
