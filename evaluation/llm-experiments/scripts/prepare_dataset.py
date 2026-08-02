#!/usr/bin/env python3
"""
scripts/prepare_dataset.py

Sample the dataset to the configured sample_size and save as a CSV.
This creates a stable, reproducible sample used for all experiment runs.

Stratified sampling is applied on the label column to preserve
class distribution.

Usage:
    cd /path/to/anxiosense
    python evaluation/llm-experiments/scripts/prepare_dataset.py --dataset dreaddit
    python evaluation/llm-experiments/scripts/prepare_dataset.py --dataset goemotions
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "evaluation" / "llm-experiments"))

from src.config import load_config, resolve_path
from src.dataset_loader import load_dataset, validate_schema, sample_dataset

CONFIG_PATH = REPO_ROOT / "evaluation" / "llm-experiments" / "config" / "experiment_config.yaml"


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare dataset sample for experiments")
    parser.add_argument(
        "--dataset",
        required=True,
        choices=["dreaddit", "goemotions"],
        help="Dataset to prepare",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Override sample size from config",
    )
    parser.add_argument(
        "--split",
        default=None,
        help="Use only this split (e.g. 'test'). Default: all splits.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sampling (default: 42)",
    )
    args = parser.parse_args()

    cfg = load_config(CONFIG_PATH)
    ds_cfg = cfg.datasets[args.dataset]
    sample_size = args.sample_size or cfg.sample_size

    path = resolve_path(REPO_ROOT, ds_cfg.path)
    df = load_dataset(
        path,
        split=args.split,
        split_column=ds_cfg.split_column,
    )

    validate_schema(df, [ds_cfg.text_column, ds_cfg.label_column])
    print(f"Loaded {len(df)} rows from {path.name}")

    sampled = sample_dataset(
        df,
        n=sample_size,
        random_state=args.seed,
        stratify_col=ds_cfg.label_column,
    )
    print(f"Sampled {len(sampled)} rows (requested {sample_size})")

    # Label distribution
    print("Label distribution in sample:")
    print(sampled[ds_cfg.label_column].value_counts().to_string())

    # Save
    out_dir = REPO_ROOT / cfg.output_dir / "prepared"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.dataset}_sample_{len(sampled)}.csv"
    sampled.to_csv(out_path, index=False)
    print(f"\nSaved to: {out_path}")


if __name__ == "__main__":
    main()
