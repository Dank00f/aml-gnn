import argparse
import json
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from src.ml.gnn_baseline import load_gnn_dataset
from src.ml.numpy_gcn import (
    build_numpy_gcn_manifest,
    fit_numpy_gcn,
    save_numpy_gcn_model,
)

__all__ = ['main']


@dataclass(frozen=True)
class ExperimentRun:
    seed: int
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float | None
    pr_auc: float | None
    decision_threshold: float
    metrics_output: str
    model_output: str
    manifest_output: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _parse_seeds(raw: str) -> list[int]:
    values = [part.strip() for part in raw.split(',') if part.strip()]
    if not values:
        raise ValueError('seeds must contain at least one integer')
    return [int(value) for value in values]


def _metric_value(run: ExperimentRun, metric: str) -> float:
    value = getattr(run, metric)
    if value is None:
        return float('-inf')
    return float(value)


def _write_report(summary: dict[str, object], runs: list[ExperimentRun], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        '# GNN Multi-Seed Experiment',
        '',
        '| Key | Value |',
        '|---|---:|',
        f'| selected_metric | {summary["selected_metric"]} |',
        f'| best_seed | {summary["best_seed"]} |',
        f'| run_count | {summary["run_count"]} |',
        '',
        '## Runs',
        '',
        '| seed | accuracy | precision | recall | f1 | roc_auc | pr_auc | threshold |',
        '|---|---:|---:|---:|---:|---:|---:|---:|',
    ]

    for run in runs:
        roc_auc = run.roc_auc if run.roc_auc is not None else 0.0
        pr_auc = run.pr_auc if run.pr_auc is not None else 0.0
        lines.append(
            f'| {run.seed} | {run.accuracy:.4f} | {run.precision:.4f} | {run.recall:.4f} | '
            f'{run.f1:.4f} | {roc_auc:.4f} | {pr_auc:.4f} | {run.decision_threshold:.4f} |',
        )

    output.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main(argv: list[str] | None = None) -> None:
    """Run repeated offline GNN experiments and keep the best model artifact."""
    parser = argparse.ArgumentParser(
        description='Run repeated offline GNN experiments and keep the best model artifact.',
    )
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--input-format', choices=['ibm', 'amlsim'], default='ibm')
    parser.add_argument('--expand-size', type=int)
    parser.add_argument('--sample-size', type=int)
    parser.add_argument('--time-window-seconds', type=int, default=24 * 60 * 60)
    parser.add_argument(
        '--edge-mode',
        choices=['shared_account', 'money_flow', 'hybrid'],
        default='shared_account',
    )
    parser.add_argument('--epochs', type=int, default=200)
    parser.add_argument('--hidden-dim', type=int, default=16)
    parser.add_argument('--learning-rate', type=float, default=0.05)
    parser.add_argument('--weight-decay', type=float, default=0.001)
    parser.add_argument('--train-ratio', type=float, default=0.6)
    parser.add_argument('--validation-ratio', type=float, default=0.2)
    parser.add_argument(
        '--split-mode',
        choices=['stratified', 'temporal', 'temporal_stratified'],
        default='stratified',
    )
    parser.add_argument('--class-weighting', choices=['none', 'balanced'], default='balanced')
    parser.add_argument('--decision-threshold', type=float)
    parser.add_argument('--seeds', default='42,43,44')
    parser.add_argument(
        '--select-metric',
        choices=['f1', 'pr_auc', 'roc_auc', 'recall'],
        default='f1',
    )
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--summary-output', type=Path)
    parser.add_argument('--report-output', type=Path)
    args = parser.parse_args(argv)

    dataset, metadata = load_gnn_dataset(
        args.input,
        input_format=args.input_format,
        expand_size=args.expand_size,
        sample_size=args.sample_size,
        time_window_seconds=args.time_window_seconds,
        edge_mode=args.edge_mode,
    )
    seeds = _parse_seeds(args.seeds)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    runs: list[ExperimentRun] = []
    best_run: ExperimentRun | None = None

    for seed in seeds:
        model, metrics = fit_numpy_gcn(
            dataset,
            epochs=args.epochs,
            hidden_dim=args.hidden_dim,
            learning_rate=args.learning_rate,
            weight_decay=args.weight_decay,
            seed=seed,
            train_ratio=args.train_ratio,
            validation_ratio=args.validation_ratio,
            split_mode=args.split_mode,
            class_weighting=args.class_weighting,
            decision_threshold=args.decision_threshold,
            time_window_seconds=args.time_window_seconds,
            edge_mode=args.edge_mode,
        )
        model_path = args.output_dir / f'model_seed_{seed}.npz'
        manifest_path = args.output_dir / f'model_seed_{seed}.manifest.json'
        metrics_path = args.output_dir / f'metrics_seed_{seed}.json'

        save_numpy_gcn_model(model, model_path)
        manifest = build_numpy_gcn_manifest(
            model,
            metrics=metrics,
            input_path=str(args.input),
            input_format=args.input_format,
            sample_size=args.sample_size,
            edge_mode=args.edge_mode,
            split_mode=args.split_mode,
        )
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        metrics_payload = {
            'input': str(args.input),
            'input_format': args.input_format,
            'sample_size': args.sample_size,
            'expanded_to': args.expand_size,
            'time_window_seconds': args.time_window_seconds,
            'edge_mode': args.edge_mode,
            'split_mode': args.split_mode,
            'metadata': metadata,
            **metrics.to_dict(),
            'model_output': str(model_path),
            'manifest_output': str(manifest_path),
        }
        metrics_path.write_text(
            json.dumps(metrics_payload, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

        run = ExperimentRun(
            seed=seed,
            accuracy=metrics.accuracy,
            precision=metrics.precision,
            recall=metrics.recall,
            f1=metrics.f1,
            roc_auc=metrics.roc_auc,
            pr_auc=metrics.pr_auc,
            decision_threshold=metrics.decision_threshold,
            metrics_output=str(metrics_path),
            model_output=str(model_path),
            manifest_output=str(manifest_path),
        )
        runs.append(run)
        if best_run is None or _metric_value(run, args.select_metric) > _metric_value(
            best_run,
            args.select_metric,
        ):
            best_run = run

    if best_run is None:
        raise RuntimeError('No experiment runs were produced')

    best_model_path = args.output_dir / 'best_model.npz'
    best_manifest_path = args.output_dir / 'best_model.manifest.json'
    best_metrics_path = args.output_dir / 'best_metrics.json'
    shutil.copy2(Path(best_run.model_output), best_model_path)
    shutil.copy2(Path(best_run.manifest_output), best_manifest_path)
    shutil.copy2(Path(best_run.metrics_output), best_metrics_path)

    summary = {
        'input': str(args.input),
        'input_format': args.input_format,
        'sample_size': args.sample_size,
        'expanded_to': args.expand_size,
        'time_window_seconds': args.time_window_seconds,
        'edge_mode': args.edge_mode,
        'split_mode': args.split_mode,
        'selected_metric': args.select_metric,
        'run_count': len(runs),
        'best_seed': best_run.seed,
        'best_model_output': str(best_model_path),
        'best_manifest_output': str(best_manifest_path),
        'best_metrics_output': str(best_metrics_path),
        'runs': [run.to_dict() for run in runs],
    }

    summary_output = args.summary_output or (args.output_dir / 'summary.json')
    summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    summary['summary_output'] = str(summary_output)

    if args.report_output:
        _write_report(summary, runs, args.report_output)
        summary['report_output'] = str(args.report_output)

    sys.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2))
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
