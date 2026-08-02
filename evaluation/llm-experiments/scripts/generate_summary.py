#!/usr/bin/env python3
"""
scripts/generate_summary.py

Load outputs/metrics/summary_table.csv and print a formatted 15-row
summary table (5 models × 3 strategies per dataset), plus export CSV.

Columns:
    LLM | Strategy | Med. Accuracy | Med. Precision | Med. Recall | Med. F1 (macro) | Med. Latency (ms)

Usage:
    cd /path/to/anxiosense
    python evaluation/llm-experiments/scripts/generate_summary.py
    python evaluation/llm-experiments/scripts/generate_summary.py --dataset dreaddit
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "evaluation" / "llm-experiments"))

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

from src.config import load_config, resolve_path

CONFIG_PATH = REPO_ROOT / "evaluation" / "llm-experiments" / "config" / "experiment_config.yaml"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate formatted summary table")
    parser.add_argument("--dataset", default=None, help="Filter to one dataset")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    cfg = load_config(CONFIG_PATH)
    base_output = Path(args.output_dir) if args.output_dir else resolve_path(REPO_ROOT, cfg.output_dir)
    summary_path = base_output / "metrics" / "summary_table.csv"
    per_run_path = base_output / "metrics" / "per_run_metrics.csv"

    if not summary_path.exists():
        print(f"Summary table not found: {summary_path}")
        print("Run compute_metrics.py first.")
        sys.exit(1)

    with summary_path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    # Attach coverage (n evaluated / n attempted) from the per-run file.
    # A headline metric computed over a small surviving subset is misleading
    # without it, so coverage sits in the same table rather than a separate file.
    coverage = {}
    if per_run_path.exists():
        with per_run_path.open(encoding="utf-8") as fh:
            for pr in csv.DictReader(fh):
                key = (pr["dataset"], pr["model_id"], pr["strategy"])
                agg = coverage.setdefault(key, [0, 0])
                agg[0] += int(pr["n_evaluable"]); agg[1] += int(pr["n_total"])

    if args.dataset:
        rows = [r for r in rows if r["dataset"] == args.dataset]

    if not rows:
        print("No rows to display.")
        sys.exit(0)

    # Build model name lookup from config
    model_names = {m.id: m.name for m in cfg.models}

    # Strategy display names
    strategy_labels = {
        "zero-shot":     "Zero-shot",
        "zero-shot-cot": "Zero-shot + CoT",
        "one-shot-cot":  "One-shot + CoT",
    }

    datasets = sorted(set(r["dataset"] for r in rows))
    for ds in datasets:
        ds_rows = [r for r in rows if r["dataset"] == ds]
        print(f"\n{'='*70}")
        print(f"Dataset: {ds.upper()}")
        print(f"{'='*70}")

        table_rows = []
        for r in ds_rows:
            model_name = model_names.get(r["model_id"], r["model_id"])
            strategy   = strategy_labels.get(r["strategy"], r["strategy"])
            n_eval, n_tot = coverage.get(
                (r["dataset"], r["model_id"], r["strategy"]), (0, 0)
            )
            table_rows.append([
                model_name,
                strategy,
                f"{n_eval}/{n_tot}",
                f"{float(r['median_failure_rate']):.2f}",
                f"{float(r['median_accuracy']):.3f}",
                f"{float(r['median_precision']):.3f}",
                f"{float(r['median_recall']):.3f}",
                f"{float(r['median_macro_f1']):.3f}",
                f"{float(r['median_latency_ms']):.0f}",
            ])

        headers = [
            "LLM",
            "Strategy",
            "N eval/total",
            "Fail rate",
            "Med. Accuracy",
            "Med. Precision",
            "Med. Recall",
            "Med. F1 (macro)",
            "Med. Latency (ms)",
        ]

        if HAS_TABULATE:
            print(tabulate(table_rows, headers=headers, tablefmt="pipe"))
        else:
            # Basic fallback
            header_line = " | ".join(headers)
            print(header_line)
            print("-" * len(header_line))
            for tr in table_rows:
                print(" | ".join(tr))

    # Export formatted text
    out_path = base_output / "metrics" / "final_summary.txt"
    with out_path.open("w", encoding="utf-8") as fh:
        for ds in datasets:
            ds_rows = [r for r in rows if r["dataset"] == ds]
            fh.write(f"\nDataset: {ds.upper()}\n")
            table_rows = []
            for r in ds_rows:
                model_name = model_names.get(r["model_id"], r["model_id"])
                strategy   = strategy_labels.get(r["strategy"], r["strategy"])
                n_eval, n_tot = coverage.get(
                    (r["dataset"], r["model_id"], r["strategy"]), (0, 0)
                )
                table_rows.append([
                    model_name, strategy,
                    f"{n_eval}/{n_tot}",
                    f"{float(r['median_failure_rate']):.2f}",
                    f"{float(r['median_accuracy']):.3f}",
                    f"{float(r['median_precision']):.3f}",
                    f"{float(r['median_recall']):.3f}",
                    f"{float(r['median_macro_f1']):.3f}",
                    f"{float(r['median_latency_ms']):.0f}",
                ])
            if HAS_TABULATE:
                fh.write(tabulate(table_rows, headers=headers, tablefmt="pipe") + "\n")
            else:
                for tr in table_rows:
                    fh.write(" | ".join(tr) + "\n")

    print(f"\nFormatted summary saved to: {out_path}")


if __name__ == "__main__":
    main()
