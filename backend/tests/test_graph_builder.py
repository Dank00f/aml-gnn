import pandas as pd

from src.graph.builder import GraphBuilder
from src.graph.ibm import normalize_ibm_transactions
from src.graph.scoring import apply_alert_scores
from src.shared.schemas import ColumnMapping


def test_build_graph_from_normalized_transactions(ibm_df: pd.DataFrame) -> None:
    normalized = normalize_ibm_transactions(ibm_df)
    graph = GraphBuilder().build_from_normalized_transactions(normalized)

    assert graph.number_of_nodes() == 3
    assert graph.number_of_edges() == 2
    assert 'B1:A1' in graph
    assert 'B2:A2' in graph

    edge = graph.get_edge_data('B1:A1', 'B2:A2')['tx_0']
    assert edge['transaction_id'] == 'tx_0'
    assert edge['amount'] == 1000.0
    assert edge['payment_currency'] == 'USD'
    assert edge['is_laundering'] == 1


def test_is_laundering_label_does_not_create_risk_score(ibm_df: pd.DataFrame) -> None:
    normalized = normalize_ibm_transactions(ibm_df)
    graph = GraphBuilder().build_from_normalized_transactions(normalized)
    node_scores, edge_scores = apply_alert_scores(graph, [])

    assert set(node_scores.values()) == {0.0}
    assert set(edge_scores.values()) == {0.0}


def test_mapped_csv_preserves_parallel_transactions() -> None:
    csv_bytes = (
        'sender,receiver,amount,ts\n'
        'A,B,100,2024-01-01T00:00:00\n'
        'A,B,200,2024-01-01T00:10:00\n'
    ).encode()

    graph = GraphBuilder().build_from_csv(
        csv_bytes,
        ColumnMapping(
            sender_id='sender',
            receiver_id='receiver',
            amount_paid='amount',
            timestamp='ts',
        ),
    )

    assert graph.number_of_edges('A', 'B') == 2
    edge_data = graph.get_edge_data('A', 'B')
    assert set(edge_data) == {'tx_0', 'tx_1'}
    assert {data['amount'] for data in edge_data.values()} == {100.0, 200.0}
