#!/usr/bin/env python3
"""
Build the frozen Stage C evaluation sample (deterministic, reproducible).

Produces the exact sample-ID lists used by ALL five runs and ALL three
prompting strategies. The sample is generated once, checksummed, and then
consumed by run_experiments.py via --sample-ids-file, so the evaluation set
cannot drift between runs.

TWO PREPROCESSING DECISIONS ARE APPLIED HERE
--------------------------------------------
1. MINIMUM-LENGTH EXCLUSION (both datasets)
   The AnxioSense server rejects any assessment whose text fails
       text.trim().length < 10
   (server/src/routes/workflow.ts:476). Rows failing this precondition can
   never yield a model prediction, so they are excluded at PREPROCESSING time
   rather than dispatched and recorded as model failures.

   This is applied as an A PRIORI RULE over the whole split, not as a list of
   IDs observed to have failed. Anyone re-deriving the sample from the rule
   reproduces it exactly, independent of sampling seed.

2. ANXIETY ENRICHMENT (goemotions only)
   The GoEmotions test split contains only 16 rows mapping to the `anxiety`
   eval class (0.61%, all from `nervousness`). Proportional stratification at
   n=100 yields anxiety n=1, which cannot support a per-class F1 estimate.
   Because every run uses the same fixed sample set, repeating the run five
   times does not add anxiety samples — it re-evaluates the same single row.

   The sample therefore takes ALL surviving anxiety rows and fills the
   remainder proportionally. The resulting class balance is deliberately NOT
   representative of the source distribution; see the caveat written into
   SAMPLE_MANIFEST.json and the exclusion doc.

   Dreaddit is a binary task and is sampled proportionally with no enrichment.

DETERMINISM
-----------
Given the same input CSVs, seed, and target size, this script produces
byte-identical output. The proportional fill uses the project's existing
sample_dataset(); the enrichment step is a pure set operation. Output IDs are
sorted, so ordering is stable regardless of pandas version.

Usage
-----
  python scripts/build_stage_c_sample.py \
      --output-dir evaluation/llm-experiments/outputs/stage_c_final/sample \
      --sample-size 100 --sample-seed 100
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_config, resolve_path            # noqa: E402
from src.dataset_loader import sample_dataset               # noqa: E402
from src.label_mapping import map_dreaddit_label, map_goemotions_label  # noqa: E402

CONFIG_PATH = REPO_ROOT / "evaluation" / "llm-experiments" / "config" / "experiment_config.yaml"

# server/src/routes/workflow.ts:476 — text.trim().length < 10 is rejected (HTTP 400)
SERVER_MIN_CHARS = 10
SERVER_RULE_SOURCE = "server/src/routes/workflow.ts:476"

# Eval class to enrich, and the dataset it applies to.
ENRICH_DATASET = "goemotions"
ENRICH_CLASS = "anxiety"


def _sha256_of_ids(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def _eval_class(row: pd.Series, dataset: str):
    if dataset == "goemotions":
        return map_goemotions_label(row["emotion_names"])
    return map_dreaddit_label(row["label"])


def build(dataset: str, ds_cfg, size: int, seed: int, split: str) -> dict:
    path = resolve_path(REPO_ROOT, ds_cfg.path)
    df = pd.read_csv(path)
    n_total = len(df)

    if "sample_id" not in df.columns:
        df["sample_id"] = [f"{dataset}_{i:05d}" for i in range(len(df))]

    # ── 1. split filter ────────────────────────────────────────────────────
    df = df[df[ds_cfg.split_column] == split].reset_index(drop=True)
    n_split = len(df)

    # ── 2. minimum-length exclusion (a priori rule) ────────────────────────
    trimmed_len = df[ds_cfg.text_column].astype(str).str.strip().str.len()
    too_short = df[trimmed_len < SERVER_MIN_CHARS]
    excluded_ids = sorted(too_short["sample_id"].astype(str))
    excluded_detail = [
        {
            "sample_id": str(r["sample_id"]),
            "trimmed_len": int(str(r[ds_cfg.text_column]).strip().__len__()),
            "text": str(r[ds_cfg.text_column]),
            "eval_class": _eval_class(r, dataset),
        }
        for _, r in too_short.iterrows()
    ]
    pool = df[trimmed_len >= SERVER_MIN_CHARS].reset_index(drop=True)
    n_pool = len(pool)

    pool = pool.copy()
    pool["_eval"] = [_eval_class(r, dataset) for _, r in pool.iterrows()]

    # ── 3. sample ──────────────────────────────────────────────────────────
    enrichment = None
    if dataset == ENRICH_DATASET:
        enrich_rows = pool[pool["_eval"] == ENRICH_CLASS]
        rest = pool[pool["_eval"] != ENRICH_CLASS].reset_index(drop=True)
        fill_n = size - len(enrich_rows)
        if fill_n < 0:
            print(f"  ! {ENRICH_CLASS} rows ({len(enrich_rows)}) exceed target "
                  f"size ({size}); truncating deterministically.")
            enrich_rows = enrich_rows.sort_values("sample_id").head(size)
            fill_n = 0
        filled = sample_dataset(
            rest, n=fill_n, random_state=seed,
            stratify_col=ds_cfg.label_column,
        ) if fill_n else rest.head(0)
        sampled = pd.concat([enrich_rows, filled], ignore_index=True)
        enrichment = {
            "enriched_class": ENRICH_CLASS,
            "enriched_rows_taken": int(len(enrich_rows)),
            "proportional_fill": int(len(filled)),
            "note": (
                f"All surviving '{ENRICH_CLASS}' rows were taken deliberately; "
                f"the remaining {len(filled)} were drawn proportionally "
                f"(stratified on '{ds_cfg.label_column}', seed={seed}). "
                "Class balance is intentionally NOT representative of the "
                "source split."
            ),
        }
    else:
        sampled = sample_dataset(
            pool, n=size, random_state=seed,
            stratify_col=ds_cfg.label_column,
        )

    sampled = sampled.sort_values("sample_id").reset_index(drop=True)
    ids = [str(s) for s in sampled["sample_id"]]

    if len(ids) != size:
        print(f"  ! {dataset}: produced {len(ids)} ids, expected {size}")

    # ── 4. distributions ───────────────────────────────────────────────────
    eval_dist = Counter(sampled["_eval"])
    raw_dist = Counter(sampled[ds_cfg.label_column].astype(str))
    pool_eval_dist = Counter(pool["_eval"])

    tl = sampled[ds_cfg.text_column].astype(str).str.strip().str.len()
    assert tl.min() >= SERVER_MIN_CHARS, "min-length rule violated in final sample"

    return {
        "dataset": dataset,
        "split": split,
        "sample_seed": seed,
        "target_size": size,
        "actual_size": len(ids),
        "counts": {
            "rows_in_file": n_total,
            "rows_in_split": n_split,
            "excluded_min_length": len(excluded_ids),
            "eligible_pool": n_pool,
        },
        "min_length_rule": {
            "min_chars": SERVER_MIN_CHARS,
            "predicate": "len(text.strip()) >= 10",
            "source": SERVER_RULE_SOURCE,
            "text_column": ds_cfg.text_column,
            "excluded_ids": excluded_ids,
            "excluded_detail": excluded_detail,
        },
        "enrichment": enrichment,
        "eval_class_distribution": {k: int(v) for k, v in sorted(eval_dist.items())},
        "raw_label_distribution": {k: int(v) for k, v in sorted(raw_dist.items())},
        "eligible_pool_eval_distribution": {
            k: int(v) for k, v in sorted(pool_eval_dist.items())
        },
        "text_len_min": int(tl.min()),
        "text_len_median": int(tl.median()),
        "sample_ids": ids,
        "sample_ids_sha256": _sha256_of_ids(ids),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--sample-size", type=int, default=100)
    ap.add_argument("--sample-seed", type=int, default=100)
    ap.add_argument("--split", default="test")
    ap.add_argument("--dataset", default=None, help="Limit to one dataset.")
    args = ap.parse_args()

    cfg = load_config(CONFIG_PATH)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    datasets = ({args.dataset: cfg.datasets[args.dataset]}
                if args.dataset else cfg.datasets)

    manifest = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/build_stage_c_sample.py",
        "sample_seed": args.sample_seed,
        "sample_size": args.sample_size,
        "split": args.split,
        "server_min_chars": SERVER_MIN_CHARS,
        "server_rule_source": SERVER_RULE_SOURCE,
        "datasets": {},
    }

    for name, ds_cfg in datasets.items():
        print(f"\n=== {name} ===")
        info = build(name, ds_cfg, args.sample_size, args.sample_seed, args.split)
        c = info["counts"]
        print(f"  rows in split      : {c['rows_in_split']}")
        print(f"  excluded (<{SERVER_MIN_CHARS} chars): {c['excluded_min_length']}")
        print(f"  eligible pool      : {c['eligible_pool']}")
        if info["enrichment"]:
            e = info["enrichment"]
            print(f"  enriched '{e['enriched_class']}' : "
                  f"{e['enriched_rows_taken']} taken + {e['proportional_fill']} fill")
        print(f"  final sample       : {info['actual_size']}")
        print(f"  eval classes       : {info['eval_class_distribution']}")
        print(f"  min text length    : {info['text_len_min']} chars")
        print(f"  sha256             : {info['sample_ids_sha256'][:16]}...")

        ids_path = out / f"{name}_sample_ids.txt"
        ids_path.write_text("\n".join(info["sample_ids"]) + "\n", encoding="utf-8")
        print(f"  -> {ids_path.name}")

        excl_path = out / f"{name}_excluded_min_length.csv"
        with excl_path.open("w", encoding="utf-8", newline="") as fh:
            import csv as _csv
            w = _csv.DictWriter(
                fh, fieldnames=["sample_id", "trimmed_len", "eval_class", "text"])
            w.writeheader()
            w.writerows(info["min_length_rule"]["excluded_detail"])
        print(f"  -> {excl_path.name}")

        manifest["datasets"][name] = info

    man_path = out / "SAMPLE_MANIFEST.json"
    man_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    print(f"\nManifest -> {man_path}")


if __name__ == "__main__":
    main()
