import argparse
import json
import sys
from pathlib import Path
from typing import cast

import pandas as pd

from src.ml.gnn_baseline import load_gnn_dataset
from src.ml.numpy_gcn import load_numpy_gcn_model, predict_numpy_gcn

__all__ = ['main']


def _frange(start: float, stop: float, step: float) -> list[float]:
    values: list[float] = []
    current = start
    while current <= stop + 1e-12:
        values.append(round(current, 10))
        current += step
    return values


def _sweep_thresholds(
    *,
    model_path: Path,
    input_path: Path,
    input_format: str,
    expand_size: int | None,
    sample_size: int | None,
    time_window_seconds: int,
    edge_mode: str,
    thresholds: list[float],
) -> tuple[dict[str, object], pd.DataFrame]:
    dataset, metadata = load_gnn_dataset(
        input_path,
        input_format=input_format,
        expand_size=expand_size,
        sample_size=sample_size,
        time_window_seconds=time_window_seconds,
        edge_mode=edge_mode,
    )
    model = load_numpy_gcn_model(model_path)

    rows: list[dict[str, object]] = []
    best_threshold = model.decision_threshold
    best_f1 = -1.0
    default_metrics: dict[str, object] | None = None

    for threshold in thresholds:
        prediction = predict_numpy_gcn(model, dataset, decision_threshold=threshold)
        if prediction.evaluation is None:
            raise ValueError('Calibration requires labels in the evaluation dataset')
        evaluation = prediction.evaluation
        row = {
            'threshold': threshold,
            'accuracy': evaluation['accuracy'],
            'precision': evaluation['precision'],
            'recall': evaluation['recall'],
            'f1': evaluation['f1'],
            'roc_auc': evaluation['roc_auc'],
            'pr_auc': evaluation['pr_auc'],
            'predicted_positive_count': prediction.predicted_positive_count,
        }
        rows.append(row)
        if abs(threshold - model.decision_threshold) < 1e-12:
            default_metrics = row
        f1 = cast(float, evaluation['f1'])
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold

    if default_metrics is None:
        default_prediction = predict_numpy_gcn(model, dataset)
        if default_prediction.evaluation is None:
            raise ValueError('Calibration requires labels in the evaluation dataset')
        default_metrics = {
            'threshold': model.decision_threshold,
            'accuracy': default_prediction.evaluation['accuracy'],
            'precision': default_prediction.evaluation['precision'],
            'recall': default_prediction.evaluation['recall'],
            'f1': default_prediction.evaluation['f1'],
            'roc_auc': default_prediction.evaluation['roc_auc'],
            'pr_auc': default_prediction.evaluation['pr_auc'],
            'predicted_positive_count': default_prediction.predicted_positive_count,
        }

    summary: dict[str, object] = {
        'input': str(input_path),
        'input_format': input_format,
        'expand_size': expand_size,
        'sample_size': sample_size,
        'time_window_seconds': time_window_seconds,
        'edge_mode': edge_mode,
        'model_input': str(model_path),
        'transaction_nodes': dataset.num_nodes,
        'transaction_edges': dataset.num_edges,
        'threshold_count': len(thresholds),
        'default_threshold': model.decision_threshold,
        'best_f1_threshold': best_threshold,
        'best_f1': best_f1,
        'default_metrics': default_metrics,
        'metadata': metadata,
    }
    return summary, pd.DataFrame(rows)


def _write_report(summary: dict[str, object], table: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    best_row = table.sort_values(
        ['f1', 'recall', 'precision'],
        ascending=[False, False, False],
    ).iloc[0]
    default_metrics = summary['default_metrics']
    lines = [
        '# GNN Threshold Study',
        '',
        '| Key | Value |',
        '|---|---:|',
        f'| input | {summary["input"]} |',
        f'| model_input | {summary["model_input"]} |',
        f'| transaction_nodes | {summary["transaction_nodes"]} |',
        f'| transaction_edges | {summary["transaction_edges"]} |',
        f'| default_threshold | {summary["default_threshold"]} |',
        f'| best_f1_threshold | {summary["best_f1_threshold"]} |',
        f'| best_f1 | {summary["best_f1"]} |',
        '',
        '## Default Threshold Metrics',
        '',
        '```json',
        json.dumps(default_metrics, ensure_ascii=False, indent=2),
        '```',
        '',
        '## Best Threshold Row',
        '',
        '```json',
        best_row.to_json(force_ascii=False, indent=2),
        '```',
        '',
    ]
    output.write_text('\n'.join(lines), encoding='utf-8')


def main(argv: list[str] | None = None) -> None:
    """Evaluate a saved GNN artifact across a threshold grid."""
    parser = argparse.ArgumentParser(
        description='Evaluate a saved GNN artifact across multiple decision thresholds.',
    )
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--model-input', required=True, type=Path)
    parser.add_argument('--input-format', choices=['ibm', 'amlsim'], default='ibm')
    parser.add_argument('--expand-size', type=int)
    parser.add_argument('--sample-size', type=int)
    parser.add_argument('--time-window-seconds', type=int, default=24 * 60 * 60)
    parser.add_argument(
        '--edge-mode',
        choices=['shared_account', 'money_flow', 'hybrid'],
        default='shared_account',
    )
    parser.add_argument('--min-threshold', type=float, default=0.1)
    parser.add_argument('--max-threshold', type=float, default=0.9)
    parser.add_argument('--threshold-step', type=float, default=0.05)
    parser.add_argument('--table-output', type=Path)
    parser.add_argument('--summary-output', type=Path)
    parser.add_argument('--report-output', type=Path)
    args = parser.parse_args(argv)

    thresholds = _frange(args.min_threshold, args.max_threshold, args.threshold_step)
    summary, table = _sweep_thresholds(
        model_path=args.model_input,
        input_path=args.input,
        input_format=args.input_format,
        expand_size=args.expand_size,
        sample_size=args.sample_size,
        time_window_seconds=args.time_window_seconds,
        edge_mode=args.edge_mode,
        thresholds=thresholds,
    )

    if args.table_output:
        args.table_output.parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(args.table_output, index=False)
        summary['table_output'] = str(args.table_output)

    if args.summary_output:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        summary['summary_output'] = str(args.summary_output)

    if args.report_output:
        _write_report(summary, table, args.report_output)
        summary['report_output'] = str(args.report_output)

    sys.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2))
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
