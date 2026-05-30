import math
from dataclasses import dataclass

import pandas as pd

__all__ = ['TransactionGraphDataset', 'build_transaction_graph_dataset']


@dataclass(frozen=True)
class TransactionGraphDataset:
    """Transaction-node graph dataset for offline GNN experiments."""

    node_ids: list[str]
    feature_names: list[str]
    features: list[list[float]]
    labels: list[int]
    edge_index: list[tuple[int, int]]

    @property
    def num_nodes(self) -> int:
        """Return number of transaction nodes."""
        return len(self.node_ids)

    @property
    def num_edges(self) -> int:
        """Return number of transaction-graph edges."""
        return len(self.edge_index)


def _category_maps(df: pd.DataFrame, columns: list[str]) -> dict[str, dict[str, int]]:
    maps: dict[str, dict[str, int]] = {}
    for column in columns:
        if column not in df.columns:
            maps[column] = {}
            continue
        values = sorted({str(v) for v in df[column].dropna().tolist()})
        maps[column] = {value: index + 1 for index, value in enumerate(values)}
    return maps


def _timestamp_seconds(value: object) -> int:
    parsed = pd.to_datetime(str(value), errors='coerce')
    if pd.isna(parsed):
        raise ValueError(f'Invalid transaction timestamp: {value}')
    return int(parsed.timestamp())


def build_transaction_graph_dataset(
    df: pd.DataFrame,
    time_window_seconds: int = 24 * 60 * 60,
    edge_mode: str = 'shared_account',
) -> TransactionGraphDataset:
    """Build a transaction-node graph dataset from normalized transaction rows."""
    required = {'transaction_id', 'timestamp', 'sender_id', 'receiver_id', 'amount'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f'Missing normalized columns: {", ".join(sorted(missing))}')
    if edge_mode not in {'shared_account', 'money_flow', 'hybrid'}:
        raise ValueError('edge_mode must be one of: shared_account, money_flow, hybrid')

    rows = df.copy()
    rows['_timestamp_seconds'] = rows['timestamp'].map(_timestamp_seconds)
    rows = rows.sort_values(['_timestamp_seconds', 'transaction_id']).reset_index(drop=True)
    edge_index = _transaction_edges(rows, time_window_seconds, edge_mode=edge_mode)

    category_columns = ['payment_currency', 'receiving_currency', 'payment_format']
    categories = _category_maps(rows, category_columns)

    sender_out = rows.groupby('sender_id').size().to_dict()
    receiver_in = rows.groupby('receiver_id').size().to_dict()
    sender_in = rows.groupby('receiver_id').size().to_dict()
    receiver_out = rows.groupby('sender_id').size().to_dict()
    sender_out_amount = rows.groupby('sender_id')['amount'].sum().to_dict()
    receiver_in_amount = rows.groupby('receiver_id')['amount'].sum().to_dict()
    sender_unique_receivers = rows.groupby('sender_id')['receiver_id'].nunique().to_dict()
    receiver_unique_senders = rows.groupby('receiver_id')['sender_id'].nunique().to_dict()
    tx_graph_out = _tx_graph_degree(edge_index, direction='out')
    tx_graph_in = _tx_graph_degree(edge_index, direction='in')

    node_ids: list[str] = []
    features: list[list[float]] = []
    labels: list[int] = []

    for row_index, (_, row) in enumerate(rows.iterrows()):
        amount = float(row['amount'])
        amount_received = (
            float(row['amount_received'])
            if 'amount_received' in rows.columns and pd.notna(row.get('amount_received'))
            else amount
        )
        amount_ratio = amount_received / amount if amount else 0.0
        hour = pd.to_datetime(row['timestamp']).hour

        node_ids.append(str(row['transaction_id']))
        features.append([
            amount,
            math.log1p(max(0.0, amount)),
            amount_received,
            amount_ratio,
            float(categories['payment_currency'].get(str(row.get('payment_currency')), 0)),
            float(categories['receiving_currency'].get(str(row.get('receiving_currency')), 0)),
            float(categories['payment_format'].get(str(row.get('payment_format')), 0)),
            float(hour),
            float(sender_out.get(row['sender_id'], 0)),
            float(receiver_in.get(row['receiver_id'], 0)),
            float(sender_in.get(row['sender_id'], 0)),
            float(receiver_out.get(row['receiver_id'], 0)),
            float(sender_out_amount.get(row['sender_id'], 0.0)),
            float(receiver_in_amount.get(row['receiver_id'], 0.0)),
            float(sender_unique_receivers.get(row['sender_id'], 0)),
            float(receiver_unique_senders.get(row['receiver_id'], 0)),
            float(tx_graph_out.get(row_index, 0)),
            float(tx_graph_in.get(row_index, 0)),
        ])
        labels.append(int(row.get('is_laundering', 0) or 0))

    return TransactionGraphDataset(
        node_ids=node_ids,
        feature_names=[
            'amount',
            'amount_log1p',
            'amount_received',
            'amount_received_to_paid_ratio',
            'payment_currency_code',
            'receiving_currency_code',
            'payment_format_code',
            'hour',
            'sender_out_count',
            'receiver_in_count',
            'sender_in_count',
            'receiver_out_count',
            'sender_out_amount_sum',
            'receiver_in_amount_sum',
            'sender_unique_receivers',
            'receiver_unique_senders',
            'tx_graph_out_degree',
            'tx_graph_in_degree',
        ],
        features=features,
        labels=labels,
        edge_index=edge_index,
    )


def _transaction_edges(
    rows: pd.DataFrame,
    time_window_seconds: int,
    *,
    edge_mode: str,
) -> list[tuple[int, int]]:
    if edge_mode == 'shared_account':
        return _shared_account_edges(rows, time_window_seconds)
    if edge_mode == 'money_flow':
        return _money_flow_edges(rows, time_window_seconds)
    shared_edges = set(_shared_party_edges(rows, time_window_seconds))
    shared_edges.update(_money_flow_edges(rows, time_window_seconds))
    return sorted(shared_edges)


def _shared_account_edges(
    rows: pd.DataFrame,
    time_window_seconds: int,
) -> list[tuple[int, int]]:
    account_to_indices: dict[str, list[int]] = {}
    for row_index, (_, row) in enumerate(rows.iterrows()):
        account_to_indices.setdefault(str(row['sender_id']), []).append(row_index)
        account_to_indices.setdefault(str(row['receiver_id']), []).append(row_index)

    edges: set[tuple[int, int]] = set()
    for indices in account_to_indices.values():
        ordered = sorted(set(indices), key=lambda item: int(rows.loc[item, '_timestamp_seconds']))
        for left_position, source_index in enumerate(ordered):
            source_ts = int(rows.loc[source_index, '_timestamp_seconds'])
            for target_index in ordered[left_position + 1:]:
                dt = int(rows.loc[target_index, '_timestamp_seconds']) - source_ts
                if dt > time_window_seconds:
                    break
                edges.add((source_index, target_index))

    return sorted(edges)


def _shared_party_edges(
    rows: pd.DataFrame,
    time_window_seconds: int,
) -> list[tuple[int, int]]:
    edges: set[tuple[int, int]] = set()
    sender_to_indices = _group_indices(rows, 'sender_id')
    receiver_to_indices = _group_indices(rows, 'receiver_id')

    for mapping in [sender_to_indices, receiver_to_indices]:
        for indices in mapping.values():
            _append_window_edges(rows, indices, time_window_seconds, edges)
    return sorted(edges)


def _money_flow_edges(
    rows: pd.DataFrame,
    time_window_seconds: int,
) -> list[tuple[int, int]]:
    sender_to_indices = _group_indices(rows, 'sender_id')
    receiver_to_indices = _group_indices(rows, 'receiver_id')
    edges: set[tuple[int, int]] = set()

    for account, source_indices in receiver_to_indices.items():
        target_indices = sender_to_indices.get(account)
        if not target_indices:
            continue
        ordered_sources = _ordered_indices(rows, source_indices)
        ordered_targets = _ordered_indices(rows, target_indices)
        right_start = 0

        for source_index in ordered_sources:
            source_ts = int(rows.loc[source_index, '_timestamp_seconds'])
            while (
                right_start < len(ordered_targets)
                and int(rows.loc[ordered_targets[right_start], '_timestamp_seconds']) < source_ts
            ):
                right_start += 1

            for target_index in ordered_targets[right_start:]:
                target_ts = int(rows.loc[target_index, '_timestamp_seconds'])
                dt = target_ts - source_ts
                if dt > time_window_seconds:
                    break
                if source_index != target_index:
                    edges.add((source_index, target_index))

    return sorted(edges)


def _group_indices(rows: pd.DataFrame, column: str) -> dict[str, list[int]]:
    mapping: dict[str, list[int]] = {}
    for row_index, (_, row) in enumerate(rows.iterrows()):
        mapping.setdefault(str(row[column]), []).append(row_index)
    return mapping


def _ordered_indices(rows: pd.DataFrame, indices: list[int]) -> list[int]:
    return sorted(set(indices), key=lambda item: int(rows.loc[item, '_timestamp_seconds']))


def _append_window_edges(
    rows: pd.DataFrame,
    indices: list[int],
    time_window_seconds: int,
    edges: set[tuple[int, int]],
) -> None:
    ordered = _ordered_indices(rows, indices)
    for left_position, source_index in enumerate(ordered):
        source_ts = int(rows.loc[source_index, '_timestamp_seconds'])
        for target_index in ordered[left_position + 1:]:
            dt = int(rows.loc[target_index, '_timestamp_seconds']) - source_ts
            if dt > time_window_seconds:
                break
            edges.add((source_index, target_index))


def _tx_graph_degree(
    edge_index: list[tuple[int, int]],
    *,
    direction: str,
) -> dict[int, int]:
    degree: dict[int, int] = {}
    position = 0 if direction == 'out' else 1
    for edge in edge_index:
        degree[edge[position]] = degree.get(edge[position], 0) + 1
    return degree
