from dataclasses import dataclass

import pandas as pd

__all__ = [
    'AmlsimSampleStats',
    'normalize_amlsim_transactions',
    'prepare_amlsim_training_frame',
]

AMLSIM_REQUIRED_COLUMNS = [
    'TX_ID',
    'SENDER_ACCOUNT_ID',
    'RECEIVER_ACCOUNT_ID',
    'TX_TYPE',
    'TX_AMOUNT',
    'TIMESTAMP',
    'IS_FRAUD',
]


@dataclass(frozen=True)
class AmlsimSampleStats:
    """Sampling summary for AMLSim transactions used in offline GNN training."""

    total_rows: int
    selected_rows: int
    selected_positive_rows: int
    selected_negative_rows: int
    fraud_account_count: int
    context_negative_rows: int
    random_negative_rows: int

    def to_dict(self) -> dict[str, int]:
        """Return JSON-serializable stats."""
        return {
            'total_rows': self.total_rows,
            'selected_rows': self.selected_rows,
            'selected_positive_rows': self.selected_positive_rows,
            'selected_negative_rows': self.selected_negative_rows,
            'fraud_account_count': self.fraud_account_count,
            'context_negative_rows': self.context_negative_rows,
            'random_negative_rows': self.random_negative_rows,
        }


def normalize_amlsim_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize AMLSim `transactions.csv` rows into the transaction schema used by GNN."""
    missing = [column for column in AMLSIM_REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f'Missing AMLSim columns: {", ".join(missing)}')

    timestamp_steps = pd.to_numeric(df['TIMESTAMP'], errors='coerce')
    if bool(timestamp_steps.isna().any()):
        raise ValueError('AMLSim TIMESTAMP contains invalid values')

    amounts = pd.to_numeric(df['TX_AMOUNT'], errors='coerce')
    if bool(amounts.isna().any()):
        raise ValueError('AMLSim TX_AMOUNT contains invalid values')

    labels = df['IS_FRAUD'].map(_parse_bool_label)
    timestamps = pd.Timestamp('2024-01-01T00:00:00') + pd.to_timedelta(
        timestamp_steps.astype(int),
        unit='h',
    )

    return pd.DataFrame(
        {
            'transaction_id': df['TX_ID'].astype(str),
            'timestamp': timestamps,
            'sender_id': df['SENDER_ACCOUNT_ID'].astype(str).str.strip(),
            'receiver_id': df['RECEIVER_ACCOUNT_ID'].astype(str).str.strip(),
            'amount': amounts.astype(float),
            'amount_received': amounts.astype(float),
            'payment_format': df['TX_TYPE'].astype(str).str.strip(),
            'payment_currency': 'UNKNOWN',
            'receiving_currency': 'UNKNOWN',
            'is_laundering': labels,
        },
    )


def prepare_amlsim_training_frame(
    df: pd.DataFrame,
    *,
    sample_size: int,
    seed: int = 42,
) -> tuple[pd.DataFrame, AmlsimSampleStats]:
    """Select a manageable AMLSim subset while preserving all fraud transactions."""
    if sample_size <= 0:
        raise ValueError('sample_size must be positive')
    missing = [column for column in AMLSIM_REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f'Missing AMLSim columns: {", ".join(missing)}')

    rows = df.copy()
    rows['_is_fraud'] = rows['IS_FRAUD'].map(_parse_bool_label)

    positive = rows[rows['_is_fraud'] == 1].copy()
    negative = rows[rows['_is_fraud'] == 0].copy()
    if positive.empty:
        raise ValueError('AMLSim sample does not contain fraud rows')

    fraud_accounts = set(positive['SENDER_ACCOUNT_ID'].astype(str)) | set(
        positive['RECEIVER_ACCOUNT_ID'].astype(str),
    )
    context_negative = negative[
        negative['SENDER_ACCOUNT_ID'].astype(str).isin(fraud_accounts)
        | negative['RECEIVER_ACCOUNT_ID'].astype(str).isin(fraud_accounts)
    ].copy()
    context_negative = context_negative.drop_duplicates(subset=['TX_ID'])

    selected_size = max(sample_size, len(positive))
    negative_budget = max(0, selected_size - len(positive))
    context_take = min(len(context_negative), negative_budget)
    sampled_context = context_negative.sample(n=context_take, random_state=seed)

    remaining_budget = negative_budget - context_take
    remaining_negative = negative[~negative['TX_ID'].isin(sampled_context['TX_ID'])].copy()
    sampled_random = (
        remaining_negative.sample(
            n=min(len(remaining_negative), remaining_budget),
            random_state=seed,
        )
        if remaining_budget > 0
        else remaining_negative.head(0).copy()
    )

    selected = pd.concat([positive, sampled_context, sampled_random], ignore_index=True)
    selected = selected.drop(columns=['_is_fraud']).sample(frac=1.0, random_state=seed).reset_index(
        drop=True,
    )

    stats = AmlsimSampleStats(
        total_rows=len(df),
        selected_rows=len(selected),
        selected_positive_rows=len(positive),
        selected_negative_rows=len(selected) - len(positive),
        fraud_account_count=len(fraud_accounts),
        context_negative_rows=len(sampled_context),
        random_negative_rows=len(sampled_random),
    )
    return selected, stats


def _parse_bool_label(value: object) -> int:
    lowered = str(value).strip().lower()
    if lowered in {'1', 'true', 't', 'yes'}:
        return 1
    if lowered in {'0', 'false', 'f', 'no'}:
        return 0
    raise ValueError(f'Invalid AMLSim boolean label: {value}')
