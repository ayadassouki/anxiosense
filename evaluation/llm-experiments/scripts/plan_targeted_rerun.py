#!/usr/bin/env python3
"""
plan_targeted_rerun.py — find INFRASTRUCTURE failures and emit targeted rerun commands.

    cd ~/anxiosense/evaluation/llm-experiments
    python3 scripts/plan_targeted_rerun.py outputs/stage_c_defaults

READ-ONLY. Prints a plan. Never edits, deletes or reruns anything.

WHAT IT WILL RERUN
  Only failures where NO usable model output exists — the request never produced
  an answer:
    HTTP 5xx / 4xx   (incl. MASTRA_VECTOR_LIBSQL_QUERY_FAILED storage outages)
    Request timed out
  These are missing data. Re-collecting them recovers an observation that the
  experiment was entitled to and lost to an outage.

WHAT IT WILL *NOT* RERUN — AND WHY THIS MATTERS
  Model-behaviour failures, where the model DID answer but the answer was
  unusable:
    out-of-vocabulary predicted emotion
    emotion payload unreadable (fail_unparseable / fail_truncated)
    refusals, prompt echoes, commentary instead of JSON

  These are RESULTS, not errors. Re-rolling them until they parse would delete
  the model's failure modes from the record and report accuracy conditional on
  the model cooperating — which overstates it. For a screening tool, refusal and
  non-adherence rates are findings worth reporting, and they differ sharply
  between models (Llama 4 Scout: 91 OOV; Mistral Small 4: 3).

  It is worse at non-zero temperature. Gemma 4 31B's published default is
  temperature 1.0, so a re-roll returns a different sample. Selectively
  re-rolling only the rows you disliked is a garden-of-forking-paths problem,
  not a data-quality fix.

  The script therefore refuses to put model failures in a rerun command. It
  reports them so you can quote the rates in your limitations section.

THE APPEND TRAP
  ResultStore APPENDS, and --resume treats an existing failed record as
  "completed" (src/result_store.py:_load_completed). So a targeted rerun into an
  existing JSONL produces DUPLICATE sample_ids, which audit_pilot.py check 4
  flags. Every emitted plan therefore moves the cell aside first.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

# Failure classes that represent MISSING DATA (safe to re-collect).
INFRA = "infrastructure"
# Failure classes that represent MODEL BEHAVIOUR (must NOT be re-collected).
MODEL = "model-behaviour"

DEFAULT_THRESHOLD = 5


def classify(reason: str) -> tuple[str, str] | tuple[None, None]:
    """(category, subtype) for a failure_reason, or (None, None) if not a failure."""
    r = (reason or "").strip()
    if not r:
        return (None, None)
    if r.startswith("HTTP 504") and "LIBSQL" in r.upper():
        return (INFRA, "storage outage (libSQL)")
    if r.startswith("HTTP 4") or r.startswith("HTTP 5"):
        return (INFRA, "provider/gateway error")
    if "timed out" in r:
        return (INFRA, "timeout")
    if r.startswith("out-of-vocabulary"):
        return (MODEL, "out-of-vocabulary emotion")
    if "unreadable" in r:
        return (MODEL, "unparseable/truncated payload")
    return (MODEL, "other")


def parse_cell(stem: str) -> tuple[str, str, str, int] | None:
    """dreaddit_mistralai_mistral-small-2603_zero-shot-cot_run2 -> parts."""
    try:
        dataset, rest = stem.split("_", 1)
        rest, run_part = rest.rsplit("_run", 1)
        run = int(run_part)
        for strat in ("zero-shot-cot", "one-shot-cot", "zero-shot"):
            if rest.endswith("_" + strat):
                slug = rest[: -(len(strat) + 1)]
                # slug is the model id with '/' and ':' replaced by '_'
                return dataset, slug, strat, run
    except (ValueError, IndexError):
        pass
    return None


def model_id_for(slug: str, seen: dict[str, str]) -> str:
    """Recover the real model id from a record we already read."""
    return seen.get(slug, slug)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base", nargs="?", default="outputs/stage_c_defaults",
                    help="output directory containing raw/")
    ap.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD,
                    help=f"emit a rerun plan when a cell has >= this many "
                         f"infrastructure failures (default {DEFAULT_THRESHOLD})")
    ap.add_argument("--ids-dir", default="outputs/stage_c_final/sample",
                    help="--sample-ids-file value used by the original run")
    ap.add_argument("--any", action="store_true",
                    help="emit a plan for ANY cell with >=1 infrastructure failure "
                         "(overrides --threshold)")
    args = ap.parse_args()

    raw = Path(args.base) / "raw"
    files = sorted(raw.glob("*.jsonl"))
    if not files:
        print(f"no JSONL under {raw}")
        return 1

    threshold = 1 if args.any else args.threshold

    slug_to_model: dict[str, str] = {}
    cells: list[dict] = []
    totals = collections.Counter()
    subtypes: dict[str, collections.Counter] = {INFRA: collections.Counter(),
                                                MODEL: collections.Counter()}
    dup_cells: list[tuple[str, dict]] = []

    for f in files:
        stem = f.stem
        recs = [json.loads(l) for l in f.open()]
        ids = [d["sample_id"] for d in recs]
        dupes = {k: v for k, v in collections.Counter(ids).items() if v > 1}
        if dupes:
            dup_cells.append((stem, dupes))

        infra_ids, model_ids = [], []
        for d in recs:
            slug_to_model.setdefault(
                str(d.get("model_id", "")).replace("/", "_").replace(":", "_"),
                str(d.get("model_id", "")))
            cat, sub = classify(d.get("failure_reason"))
            if cat is None:
                continue
            totals[cat] += 1
            subtypes[cat][sub] += 1
            (infra_ids if cat == INFRA else model_ids).append(d["sample_id"])

        cells.append({"stem": stem, "n": len(recs), "infra": infra_ids,
                      "model": model_ids, "dupes": dupes})

    # ── summary ──────────────────────────────────────────────────────────────
    print("=" * 78)
    print(f"SCANNED  {len(files)} cells, {sum(c['n'] for c in cells)} rows, under {args.base}")
    print("=" * 78)
    print(f"\nINFRASTRUCTURE failures (missing data — re-collectable): {totals[INFRA]}")
    for k, v in subtypes[INFRA].most_common():
        print(f"    {v:>5}  {k}")
    print(f"\nMODEL-BEHAVIOUR failures (results — NOT re-collectable): {totals[MODEL]}")
    for k, v in subtypes[MODEL].most_common():
        print(f"    {v:>5}  {k}")
    print("\n  Model-behaviour rows are excluded from primary metrics by the harness")
    print("  (include_in_primary_metrics=False). Report their rate; do not re-roll them.")

    # ── per-cell ─────────────────────────────────────────────────────────────
    affected = [c for c in cells if len(c["infra"]) >= threshold or c["dupes"]]
    print("\n" + "=" * 78)
    print(f"CELLS NEEDING ACTION (infra >= {threshold}, or duplicate sample_ids)")
    print("=" * 78)
    if not affected:
        print("\n  None. Every cell is below the threshold and free of duplicates.")
        worst = max((len(c["infra"]) for c in cells), default=0)
        print(f"  Worst cell has {worst} infrastructure failure(s).")
        print("\n  No rerun required.")
        return 0

    for c in affected:
        parsed = parse_cell(c["stem"])
        print(f"\n  {c['stem']}")
        print(f"     rows={c['n']}  infra={len(c['infra'])}  model-behaviour={len(c['model'])}"
              + (f"  DUPLICATES={c['dupes']}" if c["dupes"] else ""))
        if not parsed:
            print("     !! could not parse cell name — handle manually")
            continue
        dataset, slug, strat, run = parsed
        model = model_id_for(slug, slug_to_model)

        if c["dupes"] or len(c["infra"]) > 25:
            why = "duplicate sample_ids" if c["dupes"] else "too many rows lost to re-collect piecemeal"
            print(f"     ACTION: full cell rerun ({why})")
            print(f"       cd ~/anxiosense/evaluation/llm-experiments")
            print(f"       mkdir -p {args.base}/rerun_backup")
            print(f"       mv {args.base}/raw/{c['stem']}.* {args.base}/rerun_backup/")
            print(f"       python3 scripts/run_experiments.py \\")
            print(f"         --dataset {dataset} --model {model} --split test \\")
            print(f"         --sample-ids-file {args.ids_dir} \\")
            print(f"         --strategy {strat} --runs 1 --run-start {run} \\")
            print(f"         --output-dir {args.base} --confirm-paid --max-cost-usd 0.50")
        else:
            ids = ",".join(sorted(set(c["infra"])))
            print(f"     ACTION: targeted rerun of {len(set(c['infra']))} id(s)")
            print(f"     NOTE: the cell must be moved aside first — ResultStore appends and")
            print(f"           --resume counts a failed record as completed, so a plain")
            print(f"           targeted rerun would duplicate sample_ids.")
            print(f"       cd ~/anxiosense/evaluation/llm-experiments")
            print(f"       mkdir -p {args.base}/rerun_backup")
            print(f"       cp {args.base}/raw/{c['stem']}.jsonl {args.base}/rerun_backup/")
            print(f"       python3 scripts/run_experiments.py \\")
            print(f"         --dataset {dataset} --model {model} --split test \\")
            print(f"         --sample-ids-file {args.ids_dir} \\")
            print(f"         --strategy {strat} --runs 1 --run-start {run} \\")
            print(f"         --only-ids {ids} \\")
            print(f"         --resume \\")
            print(f"         --output-dir {args.base} --confirm-paid --max-cost-usd 0.20")
            print(f"     THEN de-duplicate, keeping the LAST record per sample_id:")
            print(f"       python3 scripts/plan_targeted_rerun.py --dedupe-help")

    print("\n" + "=" * 78)
    print("AFTER ANY RERUN")
    print("=" * 78)
    print("  1. Confirm the log's 'Exported NNN records' line reads exactly 100.")
    print("  2. python3 scripts/audit_pilot.py " + args.base)
    print("  3. Re-run this script — infrastructure counts should have dropped and")
    print("     model-behaviour counts should be UNCHANGED. If model-behaviour counts")
    print("     moved, you re-rolled results, which is what this script exists to prevent.")
    return 0


if __name__ == "__main__":
    if "--dedupe-help" in sys.argv:
        print(__doc__)
        print("""
De-duplication after a targeted rerun
-------------------------------------
A targeted rerun appends new records alongside the old failed ones. Keep the
LAST record for each sample_id (the fresh one) and write to a NEW file — never
edit in place:

    python3 - <<'PY'
    import json, collections
    src = 'outputs/stage_c_defaults/raw/<cell>.jsonl'
    recs = [json.loads(l) for l in open(src)]
    last = {}
    for d in recs:                      # later records overwrite earlier ones
        last[d['sample_id']] = d
    out = src.replace('.jsonl', '.dedup.jsonl')
    with open(out, 'w') as fh:
        for d in last.values():
            fh.write(json.dumps(d, ensure_ascii=False) + '\\n')
    print(len(recs), '->', len(last), 'written to', out)
    PY

Then review the .dedup.jsonl, and only when satisfied move it into place and
re-export the CSV. Record in your methodology that the cell was partially
re-collected, with the date and the reason (outage), exactly as you did for the
2026-08-04 storage incident.
""")
        sys.exit(0)
    sys.exit(main())
