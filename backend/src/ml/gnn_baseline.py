import argparse
import json
import sys
from pathlib import Path
from typing import cast

import pandas as pd

from src.graph.ibm import normalize_ibm_transactions, read_ibm_transactions
from src.ml.amlsim_dataset import normalize_amlsim_transactions, prepare_amlsim_training_frame
from src.ml.gnn_dataset import TransactionGraphDataset, build_transaction_graph_dataset
from src.ml.ibm_sampling import prepare_ibm_training_frame
from src.ml.numpy_gcn import (
    build_numpy_gcn_manifest,
    fit_numpy_gcn,
    load_numpy_gcn_model,
    predict_numpy_gcn,
    save_numpy_gcn_model,
)

__all__ = ['load_gnn_dataset', 'main']


def _expand_ibm_rows(df: pd.DataFrame, target_size: int) -> pd.DataFrame:
    if target_size <= 0:
        raise ValueError('expand size must be positive')
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


def load_gnn_dataset(
    input_path: Path,
    *,
    input_format: str,
    expand_size: int | None = None,
    sample_size: int | None = None,
    time_window_seconds: int,
    edge_mode: str = 'shared_account',
) -> tuple[TransactionGraphDataset, dict[str, object]]:
    """Load and normalize an IBM or AMLSim dataset for offline GNN experiments."""
    metadata: dict[str, object] = {
        'expanded_to': expand_size,
        'sampled_to': sample_size,
        'edge_mode': edge_mode,
    }

    if input_format == 'ibm':
        if sample_size is not None:
            sampled, stats = prepare_ibm_training_frame(str(input_path), sample_size=sample_size)
            metadata['sampling'] = stats.to_dict()
            normalized = normalize_ibm_transactions(sampled)
        elif expand_size:
            expanded = _expand_ibm_rows(pd.read_csv(input_path), expand_size)
            normalized = normalize_ibm_transactions(expanded)
        else:
            normalized = read_ibm_transactions(input_path.read_bytes(), input_path.name)
    elif input_format == 'amlsim':
        raw = pd.read_csv(input_path)
        if sample_size is not None:
            sampled, stats = prepare_amlsim_training_frame(raw, sample_size=sample_size)
            metadata['sampling'] = stats.to_dict()
            raw = sampled
        normalized = normalize_amlsim_transactions(raw)
    else:
        raise ValueError(f'Unsupported input format: {input_format}')

    dataset = build_transaction_graph_dataset(
        normalized,
        time_window_seconds=time_window_seconds,
        edge_mode=edge_mode,
    )
    return dataset, metadata


def _describe(
    input_path: Path,
    dataset: TransactionGraphDataset,
    metadata: dict[str, object],
) -> dict[str, object]:
    laundering = sum(dataset.labels)
    return {
        'input': str(input_path),
        **metadata,
        'transaction_nodes': dataset.num_nodes,
        'transaction_edges': dataset.num_edges,
        'feature_count': len(dataset.feature_names),
        'laundering_labels': laundering,
        'class_balance': {
            'negative': dataset.labels.count(0),
            'positive': dataset.labels.count(1),
        },
        'feature_names': dataset.feature_names,
    }


def _default_manifest_output(model_output: Path) -> Path:
    return model_output.with_suffix('.manifest.json')


def _write_report(metrics: dict[str, object], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        '# GNN Experiment Report',
        '',
        '## Статус',
        '',
        (
            'Это offline NumPy GCN baseline над transaction nodes. '
            'Он не входит в FastAPI runtime и не влияет на rule-based scoring.'
        ),
        '',
        '## Метрики',
        '',
        f'- Input: `{metrics.get("input")}`',
        f'- Expanded to: `{metrics.get("expanded_to")}`',
        f'- Model artifact: `{metrics.get("model_output")}`',
        '',
        '| Metric | Value |',
        '|---|---:|',
    ]

    for key in [
        'transaction_nodes',
        'transaction_edges',
        'feature_count',
        'train_size',
        'validation_size',
        'test_size',
        'loss',
        'decision_threshold',
        'accuracy',
        'precision',
        'recall',
        'f1',
        'roc_auc',
        'pr_auc',
    ]:
        lines.append(f'| {key} | {metrics.get(key)} |')

    lines.extend([
        '',
        '## Class Balance',
        '',
        '```json',
        json.dumps(metrics.get('class_balance'), ensure_ascii=False, indent=2),
        '```',
        '',
        '## Baselines',
        '',
        '| Baseline | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC |',
        '|---|---:|---:|---:|---:|---:|---:|',
        _baseline_row(metrics, 'majority_class'),
        _baseline_row(metrics, 'feature_logistic_regression'),
        '',
        '## Confusion Matrix',
        '',
        '```json',
        json.dumps(metrics.get('confusion_matrix'), ensure_ascii=False, indent=2),
        '```',
        '',
        '## Validation Metrics',
        '',
        '```json',
        json.dumps(metrics.get('validation_metrics'), ensure_ascii=False, indent=2),
        '```',
        '',
        '## Default Threshold Metrics',
        '',
        '```json',
        json.dumps(metrics.get('default_threshold_metrics'), ensure_ascii=False, indent=2),
        '```',
        '',
        '## Top-K Metrics',
        '',
        '```json',
        json.dumps(metrics.get('top_k_metrics'), ensure_ascii=False, indent=2),
        '```',
        '',
        '## Ограничения',
        '',
        (
            '- Если датасет получен расширением маленького synthetic fixture, '
            'такие метрики нельзя считать production evidence.'
        ),
        '- Модель является offline experiment, а не web runtime scorer.',
        (
            '- Если feature-only logistic baseline показывает те же метрики, '
            'преимущество GNN над табличными признаками не доказано.'
        ),
        (
            '- Метрики на реальном или более крупном внешнем датасете можно указывать '
            'только после отдельного запуска.'
        ),
        '',
    ])
    output.write_text('\n'.join(lines), encoding='utf-8')


def _write_predictions(
    dataset: TransactionGraphDataset,
    payload: dict[str, object],
    output: Path,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            'transaction_id': dataset.node_ids,
            'predicted_label': payload['predictions'],
            'positive_score': payload['positive_scores'],
            'actual_label': dataset.labels,
        },
    ).to_csv(output, index=False)


def _prediction_stdout_payload(payload: dict[str, object]) -> dict[str, object]:
    summary = dict(payload)
    scores = summary.pop('positive_scores', None)
    predictions = summary.pop('predictions', None)
    if isinstance(scores, list):
        summary['positive_scores_count'] = len(scores)
    if isinstance(predictions, list):
        summary['predictions_count'] = len(predictions)
    return summary


def _baseline_row(metrics: dict[str, object], name: str) -> str:
    baselines_obj = metrics.get('baselines')
    if not isinstance(baselines_obj, dict):
        return f'| {name} |  |  |  |  |  |  |'
    baselines = cast(dict[str, object], baselines_obj)
    baseline_obj = baselines.get(name, None)
    if not isinstance(baseline_obj, dict):
        return f'| {name} |  |  |  |  |  |  |'
    baseline = cast(dict[str, object], baseline_obj)
    return (
        f'| {name} | {baseline.get("accuracy")} | {baseline.get("precision")} | '
        f'{baseline.get("recall")} | {baseline.get("f1")} | {baseline.get("roc_auc")} | '
        f'{baseline.get("pr_auc")} |'
    )


def main(argv: list[str] | None = None) -> None:
    """Train or run offline inference for the NumPy GCN transaction baseline."""
    parser = argparse.ArgumentParser(
        description='Offline experimental GNN baseline dataset entrypoint.',
    )
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--input-format', choices=['ibm', 'amlsim'], default='ibm')
    parser.add_argument('--describe-only', action='store_true')
    parser.add_argument('--expand-size', type=int)
    parser.add_argument('--sample-size', type=int)
    parser.add_argument('--time-window-seconds', type=int, default=24 * 60 * 60)
    parser.add_argument(
        '--edge-mode',
        choices=['shared_account', 'money_flow', 'hybrid'],
        default='shared_account',
    )
    parser.add_argument('--model-input', type=Path)
    parser.add_argument('--model-output', type=Path)
    parser.add_argument('--manifest-output', type=Path)
    parser.add_argument('--predictions-output', type=Path)
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
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--metrics-output', type=Path)
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
    summary = _describe(args.input, dataset, metadata)
    if args.describe_only:
        sys.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2))
        sys.stdout.write('\n')
        return

    if args.model_input:
        model = load_numpy_gcn_model(args.model_input)
        predictions = predict_numpy_gcn(
            model,
            dataset,
            decision_threshold=args.decision_threshold,
        ).to_dict()
        payload = summary | predictions | {'model_input': str(args.model_input)}

        if args.predictions_output:
            _write_predictions(dataset, predictions, args.predictions_output)
            payload['predictions_output'] = str(args.predictions_output)

        if args.metrics_output:
            args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
            args.metrics_output.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )

        sys.stdout.write(
            json.dumps(
                _prediction_stdout_payload(payload),
                ensure_ascii=False,
                indent=2,
            ),
        )
        sys.stdout.write('\n')
        return

    model, metrics = fit_numpy_gcn(
        dataset,
        epochs=args.epochs,
        hidden_dim=args.hidden_dim,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        seed=args.seed,
        train_ratio=args.train_ratio,
        validation_ratio=args.validation_ratio,
        split_mode=args.split_mode,
        class_weighting=args.class_weighting,
        decision_threshold=args.decision_threshold,
        time_window_seconds=args.time_window_seconds,
        edge_mode=args.edge_mode,
    )
    payload = summary | metrics.to_dict()
    payload['split_mode'] = args.split_mode

    if args.model_output:
        save_numpy_gcn_model(model, args.model_output)
        payload['model_output'] = str(args.model_output)
        manifest_path = args.manifest_output or _default_manifest_output(args.model_output)
        manifest = build_numpy_gcn_manifest(
            model,
            metrics=metrics,
            input_path=str(args.input),
            input_format=args.input_format,
            sample_size=args.sample_size,
            edge_mode=args.edge_mode,
            split_mode=args.split_mode,
        )
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        payload['manifest_output'] = str(manifest_path)

    if args.predictions_output:
        predictions = predict_numpy_gcn(model, dataset).to_dict()
        _write_predictions(dataset, predictions, args.predictions_output)
        payload['predictions_output'] = str(args.predictions_output)

    if args.metrics_output:
        args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
        args.metrics_output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

    if args.report_output:
        _write_report(payload, args.report_output)

    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write('\n')


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as exc:
        sys.stderr.write(f'{exc}\n')
        raise SystemExit(2) from None
