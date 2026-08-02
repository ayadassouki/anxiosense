#!/usr/bin/env python3
"""
scripts/inspect_datasets.py

Print a summary of each configured dataset to verify it is ready for experiments.
No API keys required.

Usage:
    cd /path/to/anxiosense
    python evaluation/llm-experiments/scripts/inspect_datasets.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from collections import Counter

# Make src/ importable
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "evaluation" / "llm-experiments"))

from src.dataset_loader import load_dataset, validate_schema
from src.label_mapping import map_dreaddit_label, parse_goemotions_label


CONFIG_PATH = REPO_ROOT / "evaluation" / "llm-experiments" / "config" / "experiment_config.yaml"


def main() -> None:
    import yaml

    with CONFIG_PATH.open() as fh:
        raw = yaml.safe_load(fh)

    for name, ds_cfg in raw["datasets"].items():
        path = REPO_ROOT / ds_cfg["path"]
        print(f"\n{'='*60}")
        print(f"Dataset: {name}")
        print(f"Path:    {path}")
        print(f"Exists:  {path.exists()}")

        if not path.exists():
            print("  SKIPPED — file not found")
            continue

        df = load_dataset(path)
        print(f"Rows:    {len(df)}")
        print(f"Columns: {list(df.columns)}")

        text_col = ds_cfg["text_column"]
        label_col = ds_cfg["label_column"]

        try:
            validate_schema(df, [text_col, label_col])
            print(f"Schema:  OK (text='{text_col}', label='{label_col}')")
        except Exception as exc:
            print(f"Schema:  FAIL — {exc}")
            continue

        # Split distribution
        split_col = ds_cfg.get("split_column")
        if split_col and split_col in df.columns:
            splits = df[split_col].value_counts().to_dict()
            print(f"Splits:  {splits}")

        # Label distribution
        if name == "dreaddit":
            labels = Counter(map_dreaddit_label(v) for v in df[label_col])
            print(f"Labels:  {dict(sorted(labels.items()))}")
            print(f"  0 = no stress, 1 = stress")
        elif name == "goemotions":
            raw_emotions = [parse_goemotions_label(v) for v in df[label_col]]
            emotion_counts = Counter(e for e in raw_emotions if e is not None)
            print("Labels (top 10):")
            for emotion, count in emotion_counts.most_common(10):
                print(f"  {emotion:<20} {count:>6}")

        # Text length stats
        import statistics
        lengths = df[text_col].fillna("").apply(len).tolist()
        if lengths:
            print(f"Text len (chars): min={min(lengths)}, "
                  f"median={int(statistics.median(lengths))}, max={max(lengths)}")


if __name__ == "__main__":
    main()
