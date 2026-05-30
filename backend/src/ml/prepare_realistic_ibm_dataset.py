import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from src.ml.realistic_ibm_dataset import prepare_realistic_ibm_dataset

__all__ = ['main']


def main(argv: list[str] | None = None) -> None:
    """Generate a derived IBM-format dataset for offline GNN experiments."""
    parser = argparse.ArgumentParser(description='Prepare a realistic IBM-format AML dataset')
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--positive-cycle-groups', type=int, default=30)
    parser.add_argument('--positive-fanout-groups', type=int, default=35)
    parser.add_argument('--positive-transit-groups', type=int, default=35)
    parser.add_argument('--benign-fanout-groups', type=int, default=30)
    parser.add_argument('--benign-transit-groups', type=int, default=30)
    parser.add_argument('--stats-output', type=Path)
    args = parser.parse_args(argv)

    base_df = pd.read_csv(args.input)
    dataset, stats = prepare_realistic_ibm_dataset(
        base_df,
        seed=args.seed,
        positive_cycle_groups=args.positive_cycle_groups,
        positive_fanout_groups=args.positive_fanout_groups,
        positive_transit_groups=args.positive_transit_groups,
        benign_fanout_groups=args.benign_fanout_groups,
        benign_transit_groups=args.benign_transit_groups,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(args.output, index=False)

    payload = {
        'input': str(args.input),
        'output': str(args.output),
        'seed': args.seed,
        **stats.to_dict(),
    }
    if args.stats_output:
        args.stats_output.parent.mkdir(parents=True, exist_ok=True)
        args.stats_output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
