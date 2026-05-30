import argparse
import csv
import os
import platform
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd

from src.graph.builder import GraphBuilder
from src.graph.clustering import cluster_graph
from src.graph.detectors import detect_cycles, detect_fanout, detect_shared_device, detect_transit
from src.graph.ibm import normalize_ibm_transactions
from src.graph.layout import compute_graph_layout
from src.graph.scoring import apply_alert_scores, flatten_alerts
from src.ml.gnn_dataset import build_transaction_graph_dataset
from src.ml.ibm_sampling import prepare_ibm_training_frame

DEFAULT_SIZES = [1000, 5000, 10000]
DEFAULT_INPUT = Path('tests/fixtures/ibm_aml_patterns.csv')
DEFAULT_RESULTS_DIR = Path('..') / 'results'


def _parse_sizes(value: str) -> list[int]:
    sizes = [int(part.strip()) for part in value.split(',') if part.strip()]
    if not sizes:
        raise ValueError('At least one benchmark size is required')
    if any(size <= 0 for size in sizes):
        raise ValueError('Benchmark sizes must be positive')
    return sizes


def _expand_ibm_rows(df: pd.DataFrame, target_size: int) -> pd.DataFrame:
    if len(df) >= target_size:
        return df.head(target_size).copy()

    chunks = []
    repeats = (target_size + len(df) - 1) // len(df)
    base_timestamps = pd.to_datetime(df['Timestamp'], errors='coerce')
    for block in range(repeats):
        chunk = df.copy()
        suffix = f'_{block:05d}'
        chunk['Account'] = chunk['Account'].astype(str) + suffix
        chunk['Account.1'] = chunk['Account.1'].astype(str) + suffix
        chunk['Timestamp'] = (base_timestamps + pd.Timedelta(days=block)).dt.strftime(
            '%Y-%m-%dT%H:%M:%S',
        )
        chunks.append(chunk)

    return pd.concat(chunks, ignore_index=True).head(target_size)


def _time_call[T](fn: Callable[..., T], *args: Any, **kwargs: Any) -> tuple[T, float]:
    started = time.perf_counter()
    result = fn(*args, **kwargs)
    return result, time.perf_counter() - started


def _version(command: list[str]) -> str:
    try:
        result = subprocess.run(  # noqa: S603
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except OSError:
        return 'not available'
    output = (result.stdout or result.stderr).strip()
    return output.splitlines()[0] if output else 'not available'


def run_benchmark(
    input_path: Path,
    results_dir: Path,
    sizes: list[int],
    layout_max_nodes: int,
    *,
    input_mode: str = 'fixture',
    edge_mode: str = 'money_flow',
    time_window_seconds: int = 3600,
) -> list[dict[str, Any]]:
    """Run the measured backend pipeline for configured transaction counts."""
    input_size_bytes = input_path.stat().st_size
    rows: list[dict[str, Any]] = []

    for size in sizes:
        row: dict[str, Any] = {
            'input_file': str(input_path),
            'input_file_size_bytes': input_size_bytes,
            'transaction_count': size,
            'clustering_algorithm': 'not_implemented',
            'layout_algorithm': 'forceatlas2_or_spring_fallback',
            'errors': '',
        }
        total_started = time.perf_counter()

        try:
            expanded_df, expand_seconds = _time_call(
                _prepare_benchmark_frame,
                input_path,
                size,
                input_mode=input_mode,
            )
            normalized_df, parse_seconds = _time_call(normalize_ibm_transactions, expanded_df)
            graph, build_seconds = _time_call(
                GraphBuilder().build_from_normalized_transactions,
                normalized_df,
            )
            _, gnn_dataset_seconds = _time_call(
                build_transaction_graph_dataset,
                normalized_df,
                time_window_seconds=time_window_seconds,
                edge_mode=edge_mode,
            )
            cycles, cycles_seconds = _time_call(detect_cycles, graph)
            fanout, fanout_seconds = _time_call(detect_fanout, graph)
            transit, transit_seconds = _time_call(detect_transit, graph)
            shared_identity, shared_identity_seconds = _time_call(
                detect_shared_device,
                graph,
            )
            alerts = flatten_alerts(cycles, fanout, transit, shared_identity)
            (node_scores, edge_scores), scoring_seconds = _time_call(
                apply_alert_scores,
                graph,
                alerts,
            )
            layout, layout_seconds = _time_call(
                compute_graph_layout,
                graph,
                max_nodes=layout_max_nodes,
            )
            clustering, clustering_seconds = _time_call(
                cluster_graph,
                graph,
                layout,
            )

            row.update(
                {
                    'expand_seconds': expand_seconds,
                    'parse_seconds': parse_seconds,
                    'build_seconds': build_seconds,
                    'gnn_dataset_seconds': gnn_dataset_seconds,
                    'cycles_seconds': cycles_seconds,
                    'fanout_seconds': fanout_seconds,
                    'transit_seconds': transit_seconds,
                    'shared_identity_seconds': shared_identity_seconds,
                    'scoring_seconds': scoring_seconds,
                    'clustering_seconds': clustering_seconds,
                    'layout_seconds': layout_seconds,
                    'total_seconds': time.perf_counter() - total_started,
                    'node_count': graph.number_of_nodes(),
                    'edge_count': graph.number_of_edges(),
                    'cycle_alerts': len(cycles),
                    'fanout_alerts': len(fanout),
                    'transit_alerts': len(transit),
                    'shared_identity_alerts': len(shared_identity),
                    'total_alerts': len(alerts),
                    'max_risk_score': max(
                        [*node_scores.values(), *edge_scores.values()],
                        default=0.0,
                    ),
                    'mean_node_risk_score': sum(node_scores.values()) / len(node_scores)
                    if node_scores
                    else 0.0,
                    'mean_edge_risk_score': sum(edge_scores.values()) / len(edge_scores)
                    if edge_scores
                    else 0.0,
                },
            )
            row['clustering_algorithm'] = clustering['method']
        except Exception as exc:
            row['errors'] = f'{type(exc).__name__}: {exc}'
            row['total_seconds'] = time.perf_counter() - total_started

        rows.append(row)

    results_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(results_dir / 'benchmark_results.csv', rows)
    _write_report(
        results_dir / 'BENCHMARK_REPORT.md',
        rows,
        input_path,
        results_dir,
        sizes,
        layout_max_nodes,
        input_mode=input_mode,
        edge_mode=edge_mode,
        time_window_seconds=time_window_seconds,
    )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row})
    with path.open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    path: Path,
    rows: list[dict[str, Any]],
    input_path: Path,
    results_dir: Path,
    sizes: list[int],
    layout_max_nodes: int,
    *,
    input_mode: str,
    edge_mode: str,
    time_window_seconds: int,
) -> None:
    versions = {
        'Python': platform.python_version(),
        'Node': _version(['node', '--version']),
        'pandas': pd.__version__,
        'networkx': nx.__version__,
    }
    machine = {
        'platform': platform.platform(),
        'processor': platform.processor() or 'not reported',
        'cpu_count': os.cpu_count(),
    }

    lines = [
        '# Benchmark Report',
        '',
        '## Machine',
        '',
        '| Parameter | Value |',
        '|---|---|',
        *[f'| {key} | {value} |' for key, value in machine.items()],
        '',
        '## Versions',
        '',
        '| Package | Version |',
        '|---|---|',
        *[f'| {key} | {value} |' for key, value in versions.items()],
        '',
        '## Command',
        '',
        '```powershell',
        (
            'uv run python -m src.benchmark '
            f'--input {input_path} --results-dir {results_dir} '
            f'--sizes {",".join(map(str, sizes))} '
            f'--layout-max-nodes {layout_max_nodes} '
            f'--input-mode {input_mode} --edge-mode {edge_mode} '
            f'--time-window-seconds {time_window_seconds}'
        ),
        '```',
        '',
        '## Results',
        '',
        (
            '| Transactions | Nodes | Edges | Total s | Parse s | Build s | '
            'GNN dataset s | Detectors s | '
            'Scoring s | Layout s | Clustering | Clustering s | Alerts | Max risk | Errors |'
        ),
        '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---|',
    ]

    for row in rows:
        detectors_seconds = sum(
            float(row.get(key, 0.0) or 0.0)
            for key in (
                'cycles_seconds',
                'fanout_seconds',
                'transit_seconds',
                'shared_identity_seconds',
            )
        )
        lines.append(
            '| {transaction_count} | {node_count} | {edge_count} | {total_seconds:.4f} | '
            '{parse_seconds:.4f} | {build_seconds:.4f} | {gnn_dataset_seconds:.4f} | '
            '{detectors_seconds:.4f} | '
            '{scoring_seconds:.4f} | {layout_seconds:.4f} | {clustering_algorithm} | '
            '{clustering_seconds:.4f} | {total_alerts} | '
            '{max_risk_score:.4f} | {errors} |'.format(
                transaction_count=row.get('transaction_count', 0),
                node_count=row.get('node_count', 0),
                edge_count=row.get('edge_count', 0),
                total_seconds=float(row.get('total_seconds', 0.0) or 0.0),
                parse_seconds=float(row.get('parse_seconds', 0.0) or 0.0),
                build_seconds=float(row.get('build_seconds', 0.0) or 0.0),
                gnn_dataset_seconds=float(row.get('gnn_dataset_seconds', 0.0) or 0.0),
                detectors_seconds=detectors_seconds,
                scoring_seconds=float(row.get('scoring_seconds', 0.0) or 0.0),
                layout_seconds=float(row.get('layout_seconds', 0.0) or 0.0),
                clustering_algorithm=row.get('clustering_algorithm') or '',
                clustering_seconds=float(row.get('clustering_seconds', 0.0) or 0.0),
                total_alerts=row.get('total_alerts', 0),
                max_risk_score=float(row.get('max_risk_score', 0.0) or 0.0),
                errors=row.get('errors') or '',
            ),
        )

    lines.extend(
        [
            '',
            '## Bottlenecks',
            '',
            (
                '- Server-side layout dominates runtime on the measured synthetic graph. '
                'Use subgraphs or lower `--layout-max-nodes` for faster demo runs.'
            ),
            (
                '- Transit detection uses betweenness centrality and becomes visible in larger '
                'runs; it should stay approximate for bigger graphs.'
            ),
            (
                '- Clustering uses NetworkX Louvain on small graphs and WCC fallback on larger '
                'graphs to keep the MVP path responsive.'
            ),
            (
                '- 50 000 and 100 000 transaction runs are supported by CLI parameters but were '
                'not measured unless rows for those sizes appear in the table.'
            ),
            '',
            '## Confirmed MVP Scale',
            '',
            (
                '- The confirmed scale is the largest completed row in the table above on this '
                'machine and this fixture expansion strategy.'
            ),
            '',
            '## Confirmed Scope',
            '',
            '- Results are measured on the local machine above.',
            _scope_line(input_mode),
            '- Clustering is computed in the current backend pipeline.',
            (
                '- Layout uses the backend layout function with ForceAtlas2 when available and '
                'spring-layout fallback otherwise.'
            ),
            '- These numbers describe the current MVP path, not production AML throughput.',
            '',
        ],
    )

    path.write_text('\n'.join(lines), encoding='utf-8')


def _scope_line(input_mode: str) -> str:
    if input_mode == 'fixture':
        return (
            '- The benchmark expands the bundled IBM-format synthetic pattern fixture when '
            'requested size exceeds fixture size.'
        )
    if input_mode == 'ibm_sampled':
        return (
            '- The benchmark reads an external IBM CSV in chunks and samples a bounded training '
            'frame before running the backend pipeline.'
        )
    return '- Benchmark input mode is custom and should be interpreted from the command above.'


def main() -> None:
    """Parse CLI arguments and run the benchmark."""
    parser = argparse.ArgumentParser(description='Run AML graph backend benchmark')
    parser.add_argument('--input', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('--results-dir', type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument('--sizes', default=','.join(map(str, DEFAULT_SIZES)))
    parser.add_argument('--layout-max-nodes', type=int, default=2000)
    parser.add_argument('--input-mode', choices=['fixture', 'ibm_sampled'], default='fixture')
    parser.add_argument(
        '--edge-mode',
        choices=['shared_account', 'money_flow', 'hybrid'],
        default='money_flow',
    )
    parser.add_argument('--time-window-seconds', type=int, default=3600)
    args = parser.parse_args()

    run_benchmark(
        input_path=args.input,
        results_dir=args.results_dir,
        sizes=_parse_sizes(args.sizes),
        layout_max_nodes=args.layout_max_nodes,
        input_mode=args.input_mode,
        edge_mode=args.edge_mode,
        time_window_seconds=args.time_window_seconds,
    )


def _prepare_benchmark_frame(
    input_path: Path,
    size: int,
    *,
    input_mode: str,
) -> pd.DataFrame:
    if input_mode == 'fixture':
        base_df = pd.read_csv(input_path)
        return _expand_ibm_rows(base_df, size)
    if input_mode == 'ibm_sampled':
        sampled_df, _ = prepare_ibm_training_frame(str(input_path), sample_size=size)
        return sampled_df
    raise ValueError(f'Unsupported input_mode: {input_mode}')


if __name__ == '__main__':
    main()
