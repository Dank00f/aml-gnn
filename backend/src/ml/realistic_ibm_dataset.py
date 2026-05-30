# ruff: noqa: C901

from dataclasses import dataclass

import pandas as pd

from src.graph.ibm import IBM_REQUIRED_COLUMNS, normalize_ibm_transactions

__all__ = ['RealisticIbmDatasetStats', 'prepare_realistic_ibm_dataset']


@dataclass(frozen=True)
class RealisticIbmDatasetStats:
    """Summary for a derived IBM-format dataset used in GNN experiments."""

    total_rows: int
    positive_rows: int
    negative_rows: int
    injected_positive_rows: int
    injected_benign_rows: int

    def to_dict(self) -> dict[str, int]:
        """Return JSON-serializable dataset statistics."""
        return {
            'total_rows': self.total_rows,
            'positive_rows': self.positive_rows,
            'negative_rows': self.negative_rows,
            'injected_positive_rows': self.injected_positive_rows,
            'injected_benign_rows': self.injected_benign_rows,
        }


def prepare_realistic_ibm_dataset(
    base_df: pd.DataFrame,
    *,
    seed: int = 42,
    positive_cycle_groups: int = 30,
    positive_fanout_groups: int = 35,
    positive_transit_groups: int = 35,
    benign_fanout_groups: int = 30,
    benign_transit_groups: int = 30,
) -> tuple[pd.DataFrame, RealisticIbmDatasetStats]:  # noqa: C901
    """Build a harder IBM-format dataset from real background rows plus injected patterns."""
    _validate_base_df(base_df)

    shuffled = (
        base_df[IBM_REQUIRED_COLUMNS]
        .sample(frac=1.0, random_state=seed)
        .reset_index(drop=True)
        .copy()
    )
    shuffled['Is Laundering'] = 0

    sampled_contexts = shuffled.to_dict(orient='records')
    timestamps = pd.to_datetime(shuffled['Timestamp'], errors='coerce', format='mixed')
    if bool(timestamps.isna().any()):
        raise ValueError('Base IBM dataset contains invalid timestamps')

    next_account = 1
    injected_rows: list[dict[str, object]] = []
    injected_positive_rows = 0
    injected_benign_rows = 0

    def new_account(prefix: str) -> str:
        nonlocal next_account
        value = f'{prefix}{next_account:07d}'
        next_account += 1
        return value

    def base_context(index: int) -> dict[str, object]:
        return sampled_contexts[index % len(sampled_contexts)]

    def context_amount(context: dict[str, object]) -> float:
        return float(str(context['Amount Paid']))

    def fmt_time(value: pd.Timestamp) -> str:
        return value.strftime('%Y/%m/%d %H:%M')

    def make_row(
        *,
        timestamp: pd.Timestamp,
        from_bank: object,
        account: str,
        to_bank: object,
        account_1: str,
        amount_paid: float,
        amount_received: float,
        receiving_currency: str,
        payment_currency: str,
        payment_format: str,
        is_laundering: int,
    ) -> dict[str, object]:
        return {
            'Timestamp': fmt_time(timestamp),
            'From Bank': str(from_bank),
            'Account': account,
            'To Bank': str(to_bank),
            'Account.1': account_1,
            'Amount Received': round(amount_received, 2),
            'Receiving Currency': receiving_currency,
            'Amount Paid': round(amount_paid, 2),
            'Payment Currency': payment_currency,
            'Payment Format': payment_format,
            'Is Laundering': is_laundering,
        }

    def add_positive_cycles() -> None:
        nonlocal injected_positive_rows
        for group in range(positive_cycle_groups):
            context = base_context(group)
            base_time = timestamps.iloc[group % len(timestamps)] + pd.Timedelta(days=45 + group)
            accounts = [new_account('LC'), new_account('LC'), new_account('LC')]
            banks = [context['From Bank'], context['To Bank'], context['From Bank']]
            paid = context_amount(context)
            values = [paid, round(paid * 0.98, 2), round(paid * 0.96, 2)]
            for offset, (src, dst, from_bank, to_bank, amount) in enumerate(
                [
                    (accounts[0], accounts[1], banks[0], banks[1], values[0]),
                    (accounts[1], accounts[2], banks[1], banks[2], values[1]),
                    (accounts[2], accounts[0], banks[2], banks[0], values[2]),
                ],
            ):
                injected_rows.append(
                    make_row(
                        timestamp=base_time + pd.Timedelta(minutes=offset * 8),
                        from_bank=from_bank,
                        account=src,
                        to_bank=to_bank,
                        account_1=dst,
                        amount_paid=amount,
                        amount_received=amount,
                        receiving_currency=str(context['Receiving Currency']),
                        payment_currency=str(context['Payment Currency']),
                        payment_format=str(context['Payment Format']),
                        is_laundering=1,
                    ),
                )
                injected_positive_rows += 1

    def add_positive_fanout() -> None:
        nonlocal injected_positive_rows
        for group in range(positive_fanout_groups):
            context = base_context(100 + group)
            base_time = timestamps.iloc[(100 + group) % len(timestamps)] + pd.Timedelta(
                days=90 + group,
            )
            source = new_account('LF')
            base_amount = context_amount(context)
            for offset in range(5):
                target = new_account('RF')
                amount = round(base_amount * (1 + (offset - 2) * 0.008), 2)
                injected_rows.append(
                    make_row(
                        timestamp=base_time + pd.Timedelta(minutes=offset * 4),
                        from_bank=context['From Bank'],
                        account=source,
                        to_bank=context['To Bank'],
                        account_1=target,
                        amount_paid=amount,
                        amount_received=amount,
                        receiving_currency=str(context['Receiving Currency']),
                        payment_currency=str(context['Payment Currency']),
                        payment_format=str(context['Payment Format']),
                        is_laundering=1,
                    ),
                )
                injected_positive_rows += 1

    def add_positive_transit() -> None:
        nonlocal injected_positive_rows
        for group in range(positive_transit_groups):
            context = base_context(200 + group)
            base_time = timestamps.iloc[(200 + group) % len(timestamps)] + pd.Timedelta(
                days=135 + group,
            )
            hub = new_account('LT')
            origin_a = new_account('OT')
            origin_b = new_account('OT')
            target_a = new_account('TT')
            target_b = new_account('TT')
            paid = context_amount(context)
            rows = [
                (origin_a, hub, context['From Bank'], context['To Bank'], paid * 0.99, 0),
                (origin_b, hub, context['To Bank'], context['To Bank'], paid * 1.01, 6),
                (hub, target_a, context['To Bank'], context['From Bank'], paid * 0.985, 16),
                (hub, target_b, context['To Bank'], context['From Bank'], paid * 0.975, 24),
            ]
            for src, dst, from_bank, to_bank, amount, minutes in rows:
                injected_rows.append(
                    make_row(
                        timestamp=base_time + pd.Timedelta(minutes=minutes),
                        from_bank=from_bank,
                        account=src,
                        to_bank=to_bank,
                        account_1=dst,
                        amount_paid=amount,
                        amount_received=amount,
                        receiving_currency=str(context['Receiving Currency']),
                        payment_currency=str(context['Payment Currency']),
                        payment_format=str(context['Payment Format']),
                        is_laundering=1,
                    ),
                )
                injected_positive_rows += 1

    def add_benign_fanout() -> None:
        nonlocal injected_benign_rows
        for group in range(benign_fanout_groups):
            context = base_context(300 + group)
            base_time = timestamps.iloc[(300 + group) % len(timestamps)] + pd.Timedelta(
                days=180 + group,
            )
            source = new_account('BF')
            base_amount = context_amount(context)
            for offset in range(5):
                target = new_account('PF')
                amount = round(base_amount * (0.65 + offset * 0.12), 2)
                injected_rows.append(
                    make_row(
                        timestamp=base_time + pd.Timedelta(minutes=offset * 90),
                        from_bank=context['From Bank'],
                        account=source,
                        to_bank=context['To Bank'],
                        account_1=target,
                        amount_paid=amount,
                        amount_received=amount,
                        receiving_currency=str(context['Receiving Currency']),
                        payment_currency=str(context['Payment Currency']),
                        payment_format=str(context['Payment Format']),
                        is_laundering=0,
                    ),
                )
                injected_benign_rows += 1

    def add_benign_transit() -> None:
        nonlocal injected_benign_rows
        for group in range(benign_transit_groups):
            context = base_context(400 + group)
            base_time = timestamps.iloc[(400 + group) % len(timestamps)] + pd.Timedelta(
                days=225 + group,
            )
            hub = new_account('BT')
            origin_a = new_account('ST')
            origin_b = new_account('ST')
            target_a = new_account('UT')
            target_b = new_account('UT')
            paid = context_amount(context)
            rows = [
                (origin_a, hub, context['From Bank'], context['To Bank'], paid * 0.94, 0),
                (origin_b, hub, context['From Bank'], context['To Bank'], paid * 1.03, 8 * 60),
                (hub, target_a, context['To Bank'], context['From Bank'], paid * 0.97, 24 * 60),
                (hub, target_b, context['To Bank'], context['From Bank'], paid * 1.01, 36 * 60),
            ]
            for src, dst, from_bank, to_bank, amount, minutes in rows:
                injected_rows.append(
                    make_row(
                        timestamp=base_time + pd.Timedelta(minutes=minutes),
                        from_bank=from_bank,
                        account=src,
                        to_bank=to_bank,
                        account_1=dst,
                        amount_paid=amount,
                        amount_received=amount,
                        receiving_currency=str(context['Receiving Currency']),
                        payment_currency=str(context['Payment Currency']),
                        payment_format=str(context['Payment Format']),
                        is_laundering=0,
                    ),
                )
                injected_benign_rows += 1

    add_positive_cycles()
    add_positive_fanout()
    add_positive_transit()
    add_benign_fanout()
    add_benign_transit()

    combined = pd.concat(
        [shuffled, pd.DataFrame(injected_rows, columns=IBM_REQUIRED_COLUMNS)],
        ignore_index=True,
    )
    combined = combined.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    normalize_ibm_transactions(combined)

    positives = int(pd.to_numeric(combined['Is Laundering'], errors='coerce').fillna(0).sum())
    stats = RealisticIbmDatasetStats(
        total_rows=len(combined),
        positive_rows=positives,
        negative_rows=len(combined) - positives,
        injected_positive_rows=injected_positive_rows,
        injected_benign_rows=injected_benign_rows,
    )
    return combined, stats


def _validate_base_df(df: pd.DataFrame) -> None:
    missing = [column for column in IBM_REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f'Base IBM dataset is missing columns: {", ".join(missing)}')
