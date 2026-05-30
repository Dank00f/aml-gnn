from dataclasses import dataclass

import pandas as pd

__all__ = ['IbmSampleStats', 'prepare_ibm_training_frame']


IBM_REQUIRED_COLUMNS = [
    'Timestamp',
    'From Bank',
    'Account',
    'To Bank',
    'Account.1',
    'Amount Received',
    'Receiving Currency',
    'Amount Paid',
    'Payment Currency',
    'Payment Format',
    'Is Laundering',
]


@dataclass(frozen=True)
class IbmSampleStats:
    """Sampling summary for large IBM CSV files used in offline GNN training."""

    total_rows: int
    selected_rows: int
    selected_positive_rows: int
    selected_negative_rows: int
    context_negative_rows: int
    random_negative_rows: int
    positive_account_count: int

    def to_dict(self) -> dict[str, int]:
        """Return JSON-serializable sampling statistics."""
        return {
            'total_rows': self.total_rows,
            'selected_rows': self.selected_rows,
            'selected_positive_rows': self.selected_positive_rows,
            'selected_negative_rows': self.selected_negative_rows,
            'context_negative_rows': self.context_negative_rows,
            'random_negative_rows': self.random_negative_rows,
            'positive_account_count': self.positive_account_count,
        }


def prepare_ibm_training_frame(
    path: str,
    *,
    sample_size: int,
    chunksize: int = 100_000,
    seed: int = 42,
) -> tuple[pd.DataFrame, IbmSampleStats]:
    """Sample an IBM CSV in chunks while preserving both classes when possible."""
    if sample_size <= 0:
        raise ValueError('sample_size must be positive')

    total_rows = 0
    positive_chunks: list[pd.DataFrame] = []
    positive_accounts: set[str] = set()

    for chunk in pd.read_csv(path, chunksize=chunksize):
        _validate_columns(chunk)
        total_rows += len(chunk)
        labels = pd.to_numeric(chunk['Is Laundering'], errors='coerce').fillna(0).astype(int)
        positive = chunk[labels == 1].copy()
        if positive.empty:
            continue
        positive_chunks.append(positive)
        positive_accounts.update(_account_ids(positive, 'From Bank', 'Account'))
        positive_accounts.update(_account_ids(positive, 'To Bank', 'Account.1'))

    if not positive_chunks:
        raise ValueError('IBM sample does not contain laundering rows')

    positive_df = pd.concat(positive_chunks, ignore_index=True)
    positive_selected = _select_positive_rows(positive_df, sample_size=sample_size, seed=seed)
    negative_budget = max(0, sample_size - len(positive_selected))

    context_collected, random_collected = _collect_negative_samples(
        path=path,
        chunksize=chunksize,
        seed=seed,
        positive_accounts=positive_accounts,
        negative_budget=negative_budget,
    )

    selected = pd.concat(
        [positive_selected, *context_collected, *random_collected],
        ignore_index=True,
    )
    selected = selected.sample(frac=1.0, random_state=seed).reset_index(drop=True)

    stats = IbmSampleStats(
        total_rows=total_rows,
        selected_rows=len(selected),
        selected_positive_rows=len(positive_selected),
        selected_negative_rows=len(selected) - len(positive_selected),
        context_negative_rows=sum(len(frame) for frame in context_collected),
        random_negative_rows=sum(len(frame) for frame in random_collected),
        positive_account_count=len(positive_accounts),
    )
    return selected, stats


def _validate_columns(df: pd.DataFrame) -> None:
    missing = [column for column in IBM_REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f'Missing IBM columns: {", ".join(missing)}')


def _account_ids(df: pd.DataFrame, bank_column: str, account_column: str) -> pd.Series:
    return (
        df[bank_column].astype(str).str.strip()
        + ':'
        + df[account_column].astype(str).str.strip()
    )


def _collect_negative_samples(
    *,
    path: str,
    chunksize: int,
    seed: int,
    positive_accounts: set[str],
    negative_budget: int,
) -> tuple[list[pd.DataFrame], list[pd.DataFrame]]:
    context_collected: list[pd.DataFrame] = []
    random_collected: list[pd.DataFrame] = []
    context_count = 0
    random_count = 0

    for chunk in pd.read_csv(path, chunksize=chunksize):
        labels = pd.to_numeric(chunk['Is Laundering'], errors='coerce').fillna(0).astype(int)
        negative = chunk[labels == 0].copy()
        if negative.empty:
            continue

        context_negative, context_mask = _context_negative_rows(negative, positive_accounts)
        if not context_negative.empty and context_count < negative_budget:
            remaining = negative_budget - context_count
            sampled_context = _cap_sample(context_negative, remaining, seed)
            context_collected.append(sampled_context)
            context_count += len(sampled_context)

        if context_count >= negative_budget:
            continue

        remaining = negative_budget - context_count - random_count
        if remaining <= 0:
            continue

        random_pool = negative[~context_mask].copy()
        if random_pool.empty:
            continue
        random_sample = _cap_sample(random_pool, remaining, seed)
        random_collected.append(random_sample)
        random_count += len(random_sample)

    return context_collected, random_collected


def _select_positive_rows(
    positive_df: pd.DataFrame,
    *,
    sample_size: int,
    seed: int,
) -> pd.DataFrame:
    if len(positive_df) < sample_size:
        return positive_df
    positive_limit = max(1, sample_size // 2)
    return _cap_sample(positive_df, positive_limit, seed)


def _context_negative_rows(
    negative: pd.DataFrame,
    positive_accounts: set[str],
) -> tuple[pd.DataFrame, pd.Series]:
    from_ids = _account_ids(negative, 'From Bank', 'Account')
    to_ids = _account_ids(negative, 'To Bank', 'Account.1')
    context_mask = from_ids.isin(positive_accounts) | to_ids.isin(positive_accounts)
    return negative[context_mask].copy(), context_mask


def _cap_sample(df: pd.DataFrame, limit: int, seed: int) -> pd.DataFrame:
    if len(df) <= limit:
        return df
    return df.sample(n=limit, random_state=seed)
