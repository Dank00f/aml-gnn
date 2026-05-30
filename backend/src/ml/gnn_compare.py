import argparse
import json
import sys
from pathlib import Path
from typing import cast

__all__ = ['main']


def _load_summary(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding='utf-8'))


def _extract_best(summary: dict[str, object]) -> dict[str, object]:
    return {
        'input': summary['input'],
        'sample_size': summary.get('sample_size'),
        'selected_metric': summary.get('selected_metric'),
        'best_seed': summary.get('best_seed'),
        'best_model_output': summary.get('best_model_output'),
        'best_metrics_output': summary.get('best_metrics_output'),
    }


def _load_best_metrics(summary: dict[str, object]) -> dict[str, object]:
    metrics_path = Path(str(summary['best_metrics_output']))
    if not metrics_path.is_absolute():
        metrics_path = Path.cwd() / metrics_path
    return json.loads(metrics_path.read_text(encoding='utf-8'))


def _build_comparison(
    left_summary: dict[str, object],
    right_summary: dict[str, object],
) -> dict[str, object]:
    left_metrics = _load_best_metrics(left_summary)
    right_metrics = _load_best_metrics(right_summary)
    return {
        'left': _extract_best(left_summary) | {
            'accuracy': left_metrics['accuracy'],
            'precision': left_metrics['precision'],
            'recall': left_metrics['recall'],
            'f1': left_metrics['f1'],
            'roc_auc': left_metrics['roc_auc'],
            'pr_auc': left_metrics['pr_auc'],
            'decision_threshold': left_metrics['decision_threshold'],
        },
        'right': _extract_best(right_summary) | {
            'accuracy': right_metrics['accuracy'],
            'precision': right_metrics['precision'],
            'recall': right_metrics['recall'],
            'f1': right_metrics['f1'],
            'roc_auc': right_metrics['roc_auc'],
            'pr_auc': right_metrics['pr_auc'],
            'decision_threshold': right_metrics['decision_threshold'],
        },
    }


def _write_report(comparison: dict[str, object], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    left = comparison['left']
    right = comparison['right']
    if not isinstance(left, dict) or not isinstance(right, dict):
        raise ValueError('Invalid comparison payload')
    left_payload = cast(dict[str, object], left)
    right_payload = cast(dict[str, object], right)
    lines = [
        '# GNN Scale Comparison',
        '',
        '| Metric | Left | Right |',
        '|---|---:|---:|',
    ]
    for key in [
        'sample_size',
        'best_seed',
        'accuracy',
        'precision',
        'recall',
        'f1',
        'roc_auc',
        'pr_auc',
        'decision_threshold',
    ]:
        lines.append(f'| {key} | {left_payload.get(key)} | {right_payload.get(key)} |')
    output.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main(argv: list[str] | None = None) -> None:
    """Compare two multi-seed GNN summaries and extract best-run metrics."""
    parser = argparse.ArgumentParser(
        description='Compare two multi-seed GNN summaries.',
    )
    parser.add_argument('--left-summary', required=True, type=Path)
    parser.add_argument('--right-summary', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--report-output', type=Path)
    args = parser.parse_args(argv)

    left_summary = _load_summary(args.left_summary)
    right_summary = _load_summary(args.right_summary)
    comparison = _build_comparison(left_summary, right_summary)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(comparison, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

    if args.report_output:
        _write_report(comparison, args.report_output)

    sys.stdout.write(json.dumps(comparison, ensure_ascii=False, indent=2))
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
