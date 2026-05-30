from pathlib import Path

import pandas as pd
import pytest

from src.graph.ibm import read_ibm_transactions
from src.ml.amlsim_dataset import normalize_amlsim_transactions, prepare_amlsim_training_frame
from src.ml.gnn_baseline import main
from src.ml.gnn_calibration import main as gnn_calibration_main
from src.ml.gnn_compare import main as gnn_compare_main
from src.ml.gnn_experiment import main as gnn_experiment_main
from src.ml.gnn_leaderboard import main as gnn_leaderboard_main
from src.ml.gnn_dataset import build_transaction_graph_dataset
from src.ml.ibm_sampling import prepare_ibm_training_frame
from src.ml.numpy_gcn import (
    build_numpy_gcn_manifest,
    fit_numpy_gcn,
    load_numpy_gcn_model,
    predict_numpy_gcn,
)
from src.ml.prepare_realistic_ibm_dataset import main as prepare_realistic_ibm_main
from src.ml.numpy_gcn import train_numpy_gcn
from src.ml.realistic_ibm_dataset import prepare_realistic_ibm_dataset


FIXTURE_PATH = Path(__file__).parent / 'fixtures' / 'ibm_aml_patterns.csv'


def test_transaction_graph_dataset_from_ibm_fixture() -> None:
    normalized = read_ibm_transactions(FIXTURE_PATH.read_bytes(), FIXTURE_PATH.name)

    dataset = build_transaction_graph_dataset(normalized, time_window_seconds=2 * 60 * 60)

    assert dataset.num_nodes == 10
    assert dataset.labels[:3] == [1, 1, 1]
    assert len(dataset.features) == dataset.num_nodes
    assert len(dataset.features[0]) == len(dataset.feature_names)
    assert (0, 1) in dataset.edge_index
    assert (1, 2) in dataset.edge_index


def test_transaction_graph_dataset_money_flow_mode() -> None:
    normalized = read_ibm_transactions(FIXTURE_PATH.read_bytes(), FIXTURE_PATH.name)

    dataset = build_transaction_graph_dataset(
        normalized,
        time_window_seconds=2 * 60 * 60,
        edge_mode='money_flow',
    )

    assert dataset.num_nodes == 10
    assert len(dataset.feature_names) >= 18
    assert (0, 1) in dataset.edge_index
    assert (1, 2) in dataset.edge_index


def test_transaction_graph_dataset_requires_normalized_columns() -> None:
    normalized = read_ibm_transactions(FIXTURE_PATH.read_bytes(), FIXTURE_PATH.name)

    with pytest.raises(ValueError, match='Missing normalized columns'):
        build_transaction_graph_dataset(normalized.drop(columns=['sender_id']))

    with pytest.raises(ValueError, match='edge_mode must be one of'):
        build_transaction_graph_dataset(normalized, edge_mode='bad_mode')


def test_gnn_baseline_describe_only(capsys: pytest.CaptureFixture[str]) -> None:
    main(['--input', str(FIXTURE_PATH), '--describe-only'])

    captured = capsys.readouterr()
    assert '"transaction_nodes": 10' in captured.out
    assert '"laundering_labels": 3' in captured.out


def test_gnn_baseline_describe_expanded_fixture(capsys: pytest.CaptureFixture[str]) -> None:
    main(['--input', str(FIXTURE_PATH), '--expand-size', '25', '--describe-only'])

    captured = capsys.readouterr()
    assert '"expanded_to": 25' in captured.out
    assert '"transaction_nodes": 25' in captured.out


def test_prepare_ibm_training_frame_keeps_positive_rows(tmp_path: Path) -> None:
    path = tmp_path / 'ibm_sample.csv'
    pd.DataFrame(
        [
            {
                'Timestamp': '2022/09/01 00:20',
                'From Bank': '010',
                'Account': 'A1',
                'To Bank': '011',
                'Account.1': 'B1',
                'Amount Received': 10.0,
                'Receiving Currency': 'US Dollar',
                'Amount Paid': 10.0,
                'Payment Currency': 'US Dollar',
                'Payment Format': 'ACH',
                'Is Laundering': 1,
            },
            {
                'Timestamp': '2022/09/01 00:21',
                'From Bank': '010',
                'Account': 'A1',
                'To Bank': '012',
                'Account.1': 'B2',
                'Amount Received': 5.0,
                'Receiving Currency': 'US Dollar',
                'Amount Paid': 5.0,
                'Payment Currency': 'US Dollar',
                'Payment Format': 'ACH',
                'Is Laundering': 0,
            },
            {
                'Timestamp': '2022/09/01 00:22',
                'From Bank': '013',
                'Account': 'A3',
                'To Bank': '014',
                'Account.1': 'B4',
                'Amount Received': 7.0,
                'Receiving Currency': 'US Dollar',
                'Amount Paid': 7.0,
                'Payment Currency': 'US Dollar',
                'Payment Format': 'ACH',
                'Is Laundering': 0,
            },
        ],
    ).to_csv(path, index=False)

    selected, stats = prepare_ibm_training_frame(str(path), sample_size=2, chunksize=2)

    assert len(selected) == 2
    assert stats.selected_positive_rows == 1
    assert int(pd.to_numeric(selected['Is Laundering']).sum()) == 1


def test_prepare_ibm_training_frame_caps_positive_only_sample(tmp_path: Path) -> None:
    path = tmp_path / 'ibm_positive_heavy.csv'
    pd.DataFrame(
        [
            {
                'Timestamp': f'2022/09/01 00:0{i}',
                'From Bank': 'B1',
                'Account': f'A{i}',
                'To Bank': 'B2',
                'Account.1': f'C{i}',
                'Amount Received': 10 + i,
                'Receiving Currency': 'USD',
                'Amount Paid': 10 + i,
                'Payment Currency': 'USD',
                'Payment Format': 'WIRE',
                'Is Laundering': 1,
            }
            for i in range(4)
        ]
        + [
            {
                'Timestamp': f'2022/09/01 01:0{i}',
                'From Bank': 'B3',
                'Account': f'D{i}',
                'To Bank': 'B4',
                'Account.1': f'E{i}',
                'Amount Received': 20 + i,
                'Receiving Currency': 'USD',
                'Amount Paid': 20 + i,
                'Payment Currency': 'USD',
                'Payment Format': 'WIRE',
                'Is Laundering': 0,
            }
            for i in range(4)
        ],
    ).to_csv(path, index=False)

    selected, stats = prepare_ibm_training_frame(str(path), sample_size=4, chunksize=2)

    assert len(selected) == 4
    assert 0 < stats.selected_positive_rows < len(selected)
    assert stats.selected_negative_rows > 0


def test_numpy_gcn_training_smoke() -> None:
    normalized = read_ibm_transactions(FIXTURE_PATH.read_bytes(), FIXTURE_PATH.name)
    dataset = build_transaction_graph_dataset(normalized, time_window_seconds=2 * 60 * 60)

    metrics = train_numpy_gcn(dataset, epochs=5, hidden_dim=4, seed=7)

    assert metrics.status == 'trained'
    assert metrics.model == 'residual_numpy_two_layer_gcn'
    assert metrics.transaction_nodes == 10
    assert metrics.class_balance == {'negative': 7, 'positive': 3}
    assert 'majority_class' in metrics.baselines
    assert 'feature_logistic_regression' in metrics.baselines
    assert metrics.train_size > 0
    assert metrics.test_size > 0
    assert 0.0 <= metrics.accuracy <= 1.0
    assert 0.0 <= metrics.f1 <= 1.0


def test_numpy_gcn_training_temporal_split_smoke() -> None:
    normalized = read_ibm_transactions(FIXTURE_PATH.read_bytes(), FIXTURE_PATH.name)
    dataset = build_transaction_graph_dataset(normalized, time_window_seconds=2 * 60 * 60)

    metrics = train_numpy_gcn(
        dataset,
        epochs=5,
        hidden_dim=4,
        seed=7,
        split_mode='temporal',
    )

    assert metrics.status == 'trained'
    assert metrics.train_size > 0
    assert metrics.validation_size > 0
    assert metrics.test_size > 0


def test_numpy_gcn_training_temporal_stratified_split_smoke() -> None:
    normalized = read_ibm_transactions(FIXTURE_PATH.read_bytes(), FIXTURE_PATH.name)
    dataset = build_transaction_graph_dataset(normalized, time_window_seconds=2 * 60 * 60)

    metrics = train_numpy_gcn(
        dataset,
        epochs=5,
        hidden_dim=4,
        seed=7,
        split_mode='temporal_stratified',
    )

    assert metrics.status == 'trained'
    assert metrics.train_size > 0
    assert metrics.validation_size > 0
    assert metrics.test_size > 0


def test_gnn_baseline_writes_metrics(tmp_path: Path) -> None:
    output = tmp_path / 'gnn_metrics.json'
    report = tmp_path / 'GNN_EXPERIMENT_REPORT.md'
    model_output = tmp_path / 'gnn_model.npz'
    predictions_output = tmp_path / 'predictions.csv'

    main([
        '--input',
        str(FIXTURE_PATH),
        '--expand-size',
        '25',
        '--epochs',
        '5',
        '--hidden-dim',
        '4',
        '--model-output',
        str(model_output),
        '--predictions-output',
        str(predictions_output),
        '--metrics-output',
        str(output),
        '--report-output',
        str(report),
    ])

    assert output.exists()
    assert report.exists()
    assert model_output.exists()
    assert predictions_output.exists()
    assert '"model": "residual_numpy_two_layer_gcn"' in output.read_text(encoding='utf-8')
    assert '"expanded_to": 25' in output.read_text(encoding='utf-8')
    assert 'GNN Experiment Report' in report.read_text(encoding='utf-8')


def test_numpy_gcn_model_roundtrip_predict() -> None:
    normalized = read_ibm_transactions(FIXTURE_PATH.read_bytes(), FIXTURE_PATH.name)
    dataset = build_transaction_graph_dataset(normalized, time_window_seconds=2 * 60 * 60)

    model, _ = fit_numpy_gcn(dataset, epochs=5, hidden_dim=4, seed=7, time_window_seconds=7200)
    predictions = predict_numpy_gcn(model, dataset)

    assert len(predictions.positive_scores) == dataset.num_nodes
    assert len(predictions.predictions) == dataset.num_nodes
    assert predictions.evaluation is not None
    assert 0.0 <= predictions.decision_threshold <= 1.0


def test_numpy_gcn_manifest_contains_training_context() -> None:
    normalized = read_ibm_transactions(FIXTURE_PATH.read_bytes(), FIXTURE_PATH.name)
    dataset = build_transaction_graph_dataset(normalized, time_window_seconds=2 * 60 * 60)

    model, metrics = fit_numpy_gcn(dataset, epochs=5, hidden_dim=4, seed=7, time_window_seconds=7200)
    manifest = build_numpy_gcn_manifest(
        model,
        metrics=metrics,
        input_path=str(FIXTURE_PATH),
        input_format='ibm',
    )

    assert manifest['model'] == 'residual_numpy_two_layer_gcn'
    assert manifest['feature_count'] == len(dataset.feature_names)
    assert manifest['input_format'] == 'ibm'
    assert manifest['training']['seed'] == 7


def test_gnn_baseline_predict_from_saved_model(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    model_output = tmp_path / 'gnn_model.npz'
    metrics_output = tmp_path / 'train_metrics.json'
    predictions_output = tmp_path / 'predict.csv'

    main([
        '--input',
        str(FIXTURE_PATH),
        '--expand-size',
        '25',
        '--epochs',
        '5',
        '--hidden-dim',
        '4',
        '--model-output',
        str(model_output),
        '--metrics-output',
        str(metrics_output),
    ])

    main([
        '--input',
        str(FIXTURE_PATH),
        '--model-input',
        str(model_output),
        '--predictions-output',
        str(predictions_output),
    ])

    captured = capsys.readouterr()
    assert '"predicted_positive_count"' in captured.out
    assert predictions_output.exists()
    csv_text = predictions_output.read_text(encoding='utf-8')
    assert 'transaction_id,predicted_label,positive_score,actual_label' in csv_text
    loaded_model = load_numpy_gcn_model(model_output)
    assert loaded_model.model == 'residual_numpy_two_layer_gcn'


def test_gnn_experiment_writes_best_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / 'experiment'
    summary_output = tmp_path / 'summary.json'
    report_output = tmp_path / 'report.md'

    gnn_experiment_main([
        '--input',
        str(FIXTURE_PATH),
        '--expand-size',
        '25',
        '--epochs',
        '5',
        '--hidden-dim',
        '4',
        '--seeds',
        '7,8',
        '--output-dir',
        str(output_dir),
        '--summary-output',
        str(summary_output),
        '--report-output',
        str(report_output),
    ])

    assert (output_dir / 'best_model.npz').exists()
    assert (output_dir / 'best_model.manifest.json').exists()
    assert (output_dir / 'best_metrics.json').exists()
    assert summary_output.exists()
    assert report_output.exists()
    summary_text = summary_output.read_text(encoding='utf-8')
    assert '"best_seed"' in summary_text
    assert '"run_count": 2' in summary_text


def test_gnn_calibration_writes_threshold_outputs(tmp_path: Path) -> None:
    model_output = tmp_path / 'gnn_model.npz'
    table_output = tmp_path / 'thresholds.csv'
    summary_output = tmp_path / 'threshold_summary.json'
    report_output = tmp_path / 'threshold_report.md'

    main([
        '--input',
        str(FIXTURE_PATH),
        '--expand-size',
        '25',
        '--epochs',
        '5',
        '--hidden-dim',
        '4',
        '--model-output',
        str(model_output),
    ])

    gnn_calibration_main([
        '--input',
        str(FIXTURE_PATH),
        '--expand-size',
        '25',
        '--model-input',
        str(model_output),
        '--min-threshold',
        '0.2',
        '--max-threshold',
        '0.8',
        '--threshold-step',
        '0.2',
        '--table-output',
        str(table_output),
        '--summary-output',
        str(summary_output),
        '--report-output',
        str(report_output),
    ])

    assert table_output.exists()
    assert summary_output.exists()
    assert report_output.exists()
    table_text = table_output.read_text(encoding='utf-8')
    assert 'threshold,accuracy,precision,recall,f1,roc_auc,pr_auc,predicted_positive_count' in table_text
    summary_text = summary_output.read_text(encoding='utf-8')
    assert '"best_f1_threshold"' in summary_text


def test_gnn_compare_reads_multi_seed_summaries(tmp_path: Path) -> None:
    left_dir = tmp_path / 'left_experiment'
    right_dir = tmp_path / 'right_experiment'
    left_summary = tmp_path / 'left_summary.json'
    right_summary = tmp_path / 'right_summary.json'
    output = tmp_path / 'comparison.json'
    report = tmp_path / 'comparison.md'

    gnn_experiment_main([
        '--input',
        str(FIXTURE_PATH),
        '--expand-size',
        '25',
        '--epochs',
        '5',
        '--hidden-dim',
        '4',
        '--seeds',
        '7,8',
        '--output-dir',
        str(left_dir),
        '--summary-output',
        str(left_summary),
    ])
    gnn_experiment_main([
        '--input',
        str(FIXTURE_PATH),
        '--expand-size',
        '30',
        '--epochs',
        '5',
        '--hidden-dim',
        '4',
        '--seeds',
        '9,10',
        '--output-dir',
        str(right_dir),
        '--summary-output',
        str(right_summary),
    ])

    gnn_compare_main([
        '--left-summary',
        str(left_summary),
        '--right-summary',
        str(right_summary),
        '--output',
        str(output),
        '--report-output',
        str(report),
    ])

    assert output.exists()
    assert report.exists()
    comparison_text = output.read_text(encoding='utf-8')
    assert '"left"' in comparison_text
    assert '"right"' in comparison_text


def test_gnn_leaderboard_reads_multiple_summaries(tmp_path: Path) -> None:
    left_dir = tmp_path / 'leader_left'
    right_dir = tmp_path / 'leader_right'
    left_summary = tmp_path / 'leader_left_summary.json'
    right_summary = tmp_path / 'leader_right_summary.json'
    output = tmp_path / 'leaderboard.json'
    report = tmp_path / 'leaderboard.md'

    gnn_experiment_main([
        '--input',
        str(FIXTURE_PATH),
        '--expand-size',
        '25',
        '--epochs',
        '5',
        '--hidden-dim',
        '4',
        '--seeds',
        '7,8',
        '--output-dir',
        str(left_dir),
        '--summary-output',
        str(left_summary),
    ])
    gnn_experiment_main([
        '--input',
        str(FIXTURE_PATH),
        '--expand-size',
        '30',
        '--epochs',
        '5',
        '--hidden-dim',
        '4',
        '--seeds',
        '9,10',
        '--output-dir',
        str(right_dir),
        '--summary-output',
        str(right_summary),
    ])

    gnn_leaderboard_main([
        '--entry',
        'left',
        str(left_summary),
        '--entry',
        'right',
        str(right_summary),
        '--sort-metric',
        'f1',
        '--output',
        str(output),
        '--report-output',
        str(report),
    ])

    assert output.exists()
    assert report.exists()
    leaderboard_text = output.read_text(encoding='utf-8')
    assert '"leader"' in leaderboard_text
    assert '"row_count": 2' in leaderboard_text


def test_prepare_realistic_ibm_dataset_keeps_ibm_schema() -> None:
    base_df = pd.read_csv(FIXTURE_PATH)

    prepared, stats = prepare_realistic_ibm_dataset(
        base_df,
        positive_cycle_groups=2,
        positive_fanout_groups=2,
        positive_transit_groups=2,
        benign_fanout_groups=1,
        benign_transit_groups=1,
    )

    assert len(prepared) > len(base_df)
    assert prepared.columns.tolist() == base_df.columns.tolist()
    assert stats.positive_rows > 0
    normalized = read_ibm_transactions(
        prepared.to_csv(index=False).encode('utf-8'),
        'prepared_realistic.csv',
    )
    assert len(normalized) == len(prepared)
    assert normalized['is_laundering'].sum() == stats.positive_rows


def test_prepare_realistic_ibm_cli_writes_dataset(tmp_path: Path) -> None:
    output = tmp_path / 'realistic_ibm.csv'
    stats_output = tmp_path / 'realistic_ibm_stats.json'

    prepare_realistic_ibm_main([
        '--input',
        str(FIXTURE_PATH),
        '--output',
        str(output),
        '--stats-output',
        str(stats_output),
        '--positive-cycle-groups',
        '1',
        '--positive-fanout-groups',
        '1',
        '--positive-transit-groups',
        '1',
        '--benign-fanout-groups',
        '1',
        '--benign-transit-groups',
        '1',
    ])

    assert output.exists()
    assert stats_output.exists()
    assert '"positive_rows"' in stats_output.read_text(encoding='utf-8')


def test_normalize_amlsim_transactions() -> None:
    df = pd.DataFrame(
        [
            {
                'TX_ID': 1,
                'SENDER_ACCOUNT_ID': 10,
                'RECEIVER_ACCOUNT_ID': 20,
                'TX_TYPE': 'TRANSFER',
                'TX_AMOUNT': 12.5,
                'TIMESTAMP': 3,
                'IS_FRAUD': True,
            },
        ],
    )

    normalized = normalize_amlsim_transactions(df)

    assert normalized.loc[0, 'transaction_id'] == '1'
    assert normalized.loc[0, 'sender_id'] == '10'
    assert normalized.loc[0, 'receiver_id'] == '20'
    assert normalized.loc[0, 'amount'] == 12.5
    assert normalized.loc[0, 'is_laundering'] == 1


def test_prepare_amlsim_training_frame_keeps_all_fraud() -> None:
    df = pd.DataFrame(
        [
            {
                'TX_ID': 1,
                'SENDER_ACCOUNT_ID': 10,
                'RECEIVER_ACCOUNT_ID': 20,
                'TX_TYPE': 'TRANSFER',
                'TX_AMOUNT': 12.5,
                'TIMESTAMP': 0,
                'IS_FRAUD': True,
            },
            {
                'TX_ID': 2,
                'SENDER_ACCOUNT_ID': 10,
                'RECEIVER_ACCOUNT_ID': 21,
                'TX_TYPE': 'TRANSFER',
                'TX_AMOUNT': 9.5,
                'TIMESTAMP': 0,
                'IS_FRAUD': False,
            },
            {
                'TX_ID': 3,
                'SENDER_ACCOUNT_ID': 30,
                'RECEIVER_ACCOUNT_ID': 40,
                'TX_TYPE': 'TRANSFER',
                'TX_AMOUNT': 8.5,
                'TIMESTAMP': 1,
                'IS_FRAUD': False,
            },
        ],
    )

    selected, stats = prepare_amlsim_training_frame(df, sample_size=2)

    assert len(selected) == 2
    assert stats.selected_positive_rows == 1
    assert selected['IS_FRAUD'].astype(str).str.lower().isin(['true']).any()


def test_gnn_baseline_describe_amlsim(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    path = tmp_path / 'amlsim_transactions.csv'
    pd.DataFrame(
        [
            {
                'TX_ID': 1,
                'SENDER_ACCOUNT_ID': 10,
                'RECEIVER_ACCOUNT_ID': 20,
                'TX_TYPE': 'TRANSFER',
                'TX_AMOUNT': 12.5,
                'TIMESTAMP': 0,
                'IS_FRAUD': True,
            },
            {
                'TX_ID': 2,
                'SENDER_ACCOUNT_ID': 20,
                'RECEIVER_ACCOUNT_ID': 30,
                'TX_TYPE': 'TRANSFER',
                'TX_AMOUNT': 12.0,
                'TIMESTAMP': 0,
                'IS_FRAUD': False,
            },
            {
                'TX_ID': 3,
                'SENDER_ACCOUNT_ID': 30,
                'RECEIVER_ACCOUNT_ID': 40,
                'TX_TYPE': 'TRANSFER',
                'TX_AMOUNT': 11.5,
                'TIMESTAMP': 1,
                'IS_FRAUD': False,
            },
        ],
    ).to_csv(path, index=False)

    main([
        '--input',
        str(path),
        '--input-format',
        'amlsim',
        '--sample-size',
        '3',
        '--time-window-seconds',
        '3600',
        '--describe-only',
    ])

    captured = capsys.readouterr()
    assert '"sampled_to": 3' in captured.out
    assert '"transaction_nodes": 3' in captured.out
