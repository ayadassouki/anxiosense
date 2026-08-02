#!/usr/bin/env python3
"""
scripts/compute_metrics.py

Load all raw JSONL files from outputs/raw/ and compute:
    1. Per-run metrics CSV        → outputs/metrics/per_run_metrics.csv
    2. Aggregated summary CSV     → outputs/metrics/summary_table.csv
    3. Confusion matrices (JSON)  → outputs/metrics/confusion_{dataset}_{model}_{strategy}.json

Handles both binary (Dreaddit) and multiclass (GoEmotions) tasks.
Skips records where label or ground_truth is None.

Usage:
    cd /path/to/anxiosense
    python evaluation/llm-experiments/scripts/compute_metrics.py
    python evaluation/llm-experiments/scripts/compute_metrics.py --raw-dir /custom/path
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "evaluation" / "llm-experiments"))

from src.config import load_config, resolve_path
from src.metrics import (
    aggregate_runs,
    compute_failure_rate,
    compute_latency_stats,
    compute_metrics,
)
from src.label_mapping import EVAL_CLASSES
from src.result_store import load_raw_results

CONFIG_PATH = REPO_ROOT / "evaluation" / "llm-experiments" / "config" / "experiment_config.yaml"


def _autodetect_raw_dir(base_output: Path) -> Path:
    """
    Locate the raw-results directory when none was given explicitly.

    Prefers the flat <output_dir>/raw layout, then falls back to the most
    recently written <output_dir>/stage_*/raw. Returns <output_dir>/raw when
    nothing matches so the caller reports a sensible path in its error message.
    """
    flat = base_output / "raw"
    if any(flat.glob("*.jsonl")):
        return flat

    staged = [
        d for d in base_output.glob("stage_*/raw")
        if d.is_dir() and any(d.glob("*.jsonl"))
    ]
    if staged:
        newest = max(
            staged,
            key=lambda d: max(p.stat().st_mtime for p in d.glob("*.jsonl")),
        )
        print(f"[auto-detect] No results in {flat}; using {newest}")
        return newest

    return flat


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute metrics from raw experiment results")
    parser.add_argument("--raw-dir", default=None, help="Directory containing raw JSONL files")
    parser.add_argument("--output-dir", default=None, help="Override output directory")
    parser.add_argument(
        "--stage", default=None,
        help="Stage subdirectory under the output dir, e.g. 'stage_c'. "
             "Resolves to <output_dir>/<stage>/raw and writes to <output_dir>/<stage>/metrics.",
    )
    args = parser.parse_args()

    cfg = load_config(CONFIG_PATH)
    base_output = Path(args.output_dir) if args.output_dir else resolve_path(REPO_ROOT, cfg.output_dir)

    # BUGFIX: previously this was hard-wired to <output_dir>/raw, so a staged run
    # (outputs/stage_c/raw) was silently invisible and the script exited claiming
    # no records existed. Results now resolve in this order:
    #   1. explicit --raw-dir
    #   2. --stage <name>            → <output_dir>/<name>/raw
    #   3. <output_dir>/raw          if it contains .jsonl files
    #   4. the most recent <output_dir>/stage_*/raw containing .jsonl files
    if args.raw_dir:
        raw_dir = Path(args.raw_dir)
    elif args.stage:
        raw_dir = base_output / args.stage / "raw"
    else:
        raw_dir = _autodetect_raw_dir(base_output)

    # Keep metrics beside the results they describe rather than in a shared dir,
    # so re-analysing one stage cannot overwrite another stage's metrics.
    if raw_dir.name == "raw" and raw_dir.parent != base_output:
        metrics_dir = raw_dir.parent / "metrics"
    else:
        metrics_dir = base_output / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading raw results from: {raw_dir}")
    records = load_raw_results(raw_dir)

    if not records:
        print(f"No records found under {raw_dir}.")
        available = sorted(
            p.parent for p in base_output.glob("**/raw/*.jsonl")
        )
        if available:
            print("\nDirectories that DO contain raw results:")
            for d in sorted(set(available)):
                print(f"  {d}")
            print("\nRe-run with --stage <name> or --raw-dir <path>.")
        else:
            print("Run run_experiments.py first.")
        sys.exit(1)

    print(f"Loaded {len(records)} records.")

    # Group by (dataset, model_id, strategy, run)
    groups: dict = defaultdict(list)
    for r in records:
        key = (
            r.get("dataset", "unknown"),
            r.get("model_id", "unknown"),
            r.get("strategy", "unknown"),
            r.get("run", 0),
        )
        groups[key].append(r)

    # Per-run metrics
    per_run_rows = []
    cm_data: dict = defaultdict(list)  # (dataset, model_id, strategy) → list of CMs

    for (dataset, model_id, strategy, run), run_records in sorted(groups.items()):
        # Filter to evaluable records
        evaluable = [
            r for r in run_records
            if r.get("label") is not None and r.get("ground_truth") is not None
        ]

        failure_rate = compute_failure_rate(run_records)
        latencies = [r["latency_ms"] for r in run_records if r.get("latency_ms") is not None]
        lat_stats = compute_latency_stats(latencies)

        if evaluable:
            y_true = [r["ground_truth"] for r in evaluable]
            y_pred = [r["label"] for r in evaluable]

            # Determine average type and the fixed class space.
            # Passing an explicit label space keeps confusion matrices the same
            # shape and orientation across every cell, so they can be compared
            # strategy-to-strategy and a class with zero support is still shown.
            unique_true = set(y_true)
            if unique_true <= {0, 1}:
                avg, class_space = "binary", [0, 1]
            else:
                avg, class_space = "macro", list(EVAL_CLASSES)

            m = compute_metrics(y_true, y_pred, average=avg, labels=class_space)
            cm_key = (dataset, model_id, strategy)
            cm_data[cm_key].append({
                "run": run,
                "confusion_matrix": m["confusion_matrix"],
                "labels": m["confusion_labels"],
                "per_class_f1": m["per_class_f1"],
                "n_evaluable": len(evaluable),
            })
        else:
            m = {
                "accuracy": None, "precision": None, "recall": None,
                "f1": None, "macro_f1": None, "n_samples": 0,
                "per_class_f1": {},
            }

        row = {
            "dataset":       dataset,
            "model_id":      model_id,
            "strategy":      strategy,
            "run":           run,
            "n_total":       len(run_records),
            "n_evaluable":   len(evaluable),
            "failure_rate":  round(failure_rate, 4),
            "accuracy":      round(m["accuracy"], 4) if m["accuracy"] is not None else None,
            "precision":     round(m["precision"], 4) if m["precision"] is not None else None,
            "recall":        round(m["recall"], 4)    if m["recall"] is not None else None,
            "f1":            round(m["f1"], 4)         if m["f1"] is not None else None,
            "macro_f1":      round(m["macro_f1"], 4)  if m["macro_f1"] is not None else None,
            "latency_median_ms": round(lat_stats["median"], 1),
            "latency_p95_ms":   round(lat_stats["p95"], 1),
            "per_class_f1":     json.dumps(m.get("per_class_f1", {}), sort_keys=True),
        }
        per_run_rows.append(row)

    # Write per-run CSV
    per_run_path = metrics_dir / "per_run_metrics.csv"
    if per_run_rows:
        fieldnames = list(per_run_rows[0].keys())
        with per_run_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(per_run_rows)
        print(f"Per-run metrics → {per_run_path}")

    # Write confusion matrix JSONs
    for (dataset, model_id, strategy), cm_list in cm_data.items():
        model_slug = model_id.replace("/", "_").replace(":", "_")
        cm_path = metrics_dir / f"confusion_{dataset}_{model_slug}_{strategy}.json"
        with cm_path.open("w", encoding="utf-8") as fh:
            json.dump(cm_list, fh, indent=2)

    print(f"Confusion matrices → {metrics_dir}/confusion_*.json")

    # Aggregate across runs
    # Group per-run rows by (dataset, model_id, strategy)
    cell_groups: dict = defaultdict(list)
    for row in per_run_rows:
        cell_key = (row["dataset"], row["model_id"], row["strategy"])
        cell_groups[cell_key].append(row)

    summary_rows = []
    for (dataset, model_id, strategy), cell_rows in sorted(cell_groups.items()):
        numeric_metrics = [
            {k: v for k, v in r.items() if isinstance(v, (int, float)) and v is not None}
            for r in cell_rows
        ]
        agg = aggregate_runs(numeric_metrics)
        summary_rows.append({
            "dataset":          dataset,
            "model_id":         model_id,
            "strategy":         strategy,
            "n_runs":           len(cell_rows),
            "median_accuracy":  round(agg.get("median_accuracy", 0), 4),
            "median_precision": round(agg.get("median_precision", 0), 4),
            "median_recall":    round(agg.get("median_recall", 0), 4),
            "median_macro_f1":  round(agg.get("median_macro_f1", 0), 4),
            "median_latency_ms":round(agg.get("median_latency_median_ms", 0), 1),
            "median_failure_rate": round(agg.get("median_failure_rate", 0), 4),
        })

    summary_path = metrics_dir / "summary_table.csv"
    if summary_rows:
        fieldnames = list(summary_rows[0].keys())
        with summary_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary_rows)
        print(f"Summary table → {summary_path}")

    print(f"\nDone. {len(per_run_rows)} per-run rows, {len(summary_rows)} summary rows.")


if __name__ == "__main__":
    main()
