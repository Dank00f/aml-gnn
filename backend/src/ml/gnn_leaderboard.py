import argparse
import json
import sys
from pathlib import Path

__all__ = ['main']


def _load_summary(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding='utf-8'))


def _resolve_metrics_path(summary_path: Path, summary: dict[str, object]) -> Path:
    value = summary.get('best_metrics_output')
    if not isinstance(value, str):
        raise ValueError('Summary does not contain best_metrics_output')
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    if candidate.exists():
        return candidate
    return summary_path.parent / candidate


def _summary_row(label: str, summary_path: Path) -> dict[str, object]:
    summary = _load_summary(summary_path)
    metrics_path = _resolve_metrics_path(summary_path, summary)
    metrics = json.loads(metrics_path.read_text(encoding='utf-8'))
    return {
        'label': label,
        'sample_size': summary.get('sample_size'),
        'edge_mode': summary.get('edge_mode', 'shared_account'),
        'best_seed': summary.get('best_seed'),
        'selected_metric': summary.get('selected_metric'),
        'accuracy': metrics.get('accuracy'),
        'precision': metrics.get('precision'),
        'recall': metrics.get('recall'),
        'f1': metrics.get('f1'),
        'roc_auc': metrics.get('roc_auc'),
        'pr_auc': metrics.get('pr_auc'),
        'decision_threshold': metrics.get('decision_threshold'),
        'summary_path': str(summary_path),
        'best_metrics_output': str(metrics_path),
        'best_model_output': summary.get('best_model_output'),
    }


def _write_report(rows: list[dict[str, object]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        '# GNN Mode Leaderboard',
        '',
        (
            '| label | sample_size | edge_mode | best_seed | accuracy | precision | '
            'recall | f1 | roc_auc | pr_auc | threshold |'
        ),
        '|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for row in rows:
        lines.append(
            f'| {row["label"]} | {row["sample_size"]} | {row["edge_mode"]} | {row["best_seed"]} | '
            f'{row["accuracy"]} | {row["precision"]} | {row["recall"]} | {row["f1"]} | '
            f'{row["roc_auc"]} | {row["pr_auc"]} | {row["decision_threshold"]} |',
        )
    output.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _sort_value(row: dict[str, object], metric: str) -> float:
    value = row[metric]
    return float(value) if isinstance(value, int | float) else float('-inf')


def main(argv: list[str] | None = None) -> None:
    """Build a leaderboard from several multi-seed GNN summary files."""
    parser = argparse.ArgumentParser(
        description='Build a leaderboard from several multi-seed GNN summary files.',
    )
    parser.add_argument(
        '--entry',
        nargs=2,
        action='append',
        metavar=('LABEL', 'SUMMARY'),
        required=True,
        help='Pair of leaderboard label and summary json path.',
    )
    parser.add_argument(
        '--sort-metric',
        choices=['f1', 'pr_auc', 'roc_auc', 'precision', 'recall', 'accuracy'],
        default='f1',
    )
    parser.add_argument('--output', type=Path)
    parser.add_argument('--report-output', type=Path)
    args = parser.parse_args(argv)

    rows = [_summary_row(label, Path(summary)) for label, summary in args.entry]
    rows.sort(key=lambda row: _sort_value(row, args.sort_metric), reverse=True)

    payload = {
        'sort_metric': args.sort_metric,
        'row_count': len(rows),
        'leader': rows[0] if rows else None,
        'rows': rows,
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    if args.report_output:
        _write_report(rows, args.report_output)

    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
