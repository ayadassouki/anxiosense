#!/usr/bin/env python3
"""
scripts/reanalyze_stage_c.py

OFFLINE re-analysis of Stage C raw outputs. Makes ZERO API calls and never
modifies the original raw JSONL files.

WHAT THIS FIXES
───────────────
Stage C reported 35/300 GoEmotions predictions parsed. That number was an
artefact of the analysis layer, not the model. Two defects (documented in
src/emotion_payload.py) caused it:

  1. Valid {"emotions": []} predictions — which map to the "non_distress" class
     and account for 71% of the test sample's ground truth — were recorded as
     parse failures.
  2. Chain-of-thought responses that wrapped their JSON in prose or markdown
     fences were rejected by a strict json.loads() call, even though two of the
     three strategies under test are explicitly chain-of-thought.

This script re-derives every GoEmotions prediction from the stored payloads
using the robust tri-state parser, writes corrected records to a NEW directory,
and emits a full per-record audit so every change is traceable.

Dreaddit records are passed through unchanged: they read `referralLevel`, a
short enum in the structured report, which was unaffected by either defect.

OUTPUTS (under <stage_dir>/)
    reparsed/primary/*.jsonl      corrected records, strict vocabulary
    reparsed/sensitivity/*.jsonl  corrected records, out-of-vocab mapped
    reanalysis/reparse_audit.csv  per-record before/after with parse status
    reanalysis/reparse_summary.csv  per-cell counts by parse status
    reanalysis/rerun_manifest.csv  sample_ids that are unrecoverable offline
    reanalysis/reanalysis_report.md  human-readable diagnosis

TWO ANALYSIS VARIANTS
─────────────────────
The Emotion Agent occasionally returned emotions outside its declared 7-word
vocabulary (e.g. "worried", "happiness"). These are contract violations, and
how to count them is a research judgement, so both readings are produced:

  primary      — out-of-vocab predictions are INVALID. They are excluded from
                 precision/recall and counted toward the failure rate. This is
                 the conservative reading: the agent broke its own output
                 contract, and any mapping is post-hoc researcher inference.

  sensitivity  — out-of-vocab predictions are mapped to the nearest eval class
                 via OOV_SENSITIVITY_MAP below. Report this alongside the
                 primary table to show the conclusion is robust to the choice.

Usage:
    python evaluation/llm-experiments/scripts/reanalyze_stage_c.py
    python evaluation/llm-experiments/scripts/reanalyze_stage_c.py --stage-dir <path>
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "evaluation" / "llm-experiments"))

from src.emotion_payload import OK_STATUSES, extract_emotion_payload, primary_emotion
from src.label_mapping import ANXIOSENSE_TO_EVAL_CLASS

DEFAULT_STAGE_DIR = (
    REPO_ROOT / "evaluation" / "llm-experiments" / "outputs" / "stage_c"
)

# Out-of-vocabulary predictions → nearest eval class. Used ONLY by the
# sensitivity variant. Each entry is a defensible semantic neighbour, but every
# one of them is researcher inference rather than model output, which is exactly
# why the primary analysis excludes them.
OOV_SENSITIVITY_MAP = {
    "worried":    "anxiety",       # direct synonym of the agent's own "anxiety"
    "concern":    "anxiety",       # the pipeline's own concern-pattern language
    "exhaustion": "anxiety",       # burnout/stress family; "stress" → anxiety
    "happiness":  "non_distress",  # positive affect
    "nostalgia":  "non_distress",  # non-distress affect
    "surprise":   "non_distress",  # neutral-valence affect
}


def eval_class_for(emotion, oov_map):
    """
    Map a predicted emotion to the 5-class eval space.

    Returns (eval_class, note). eval_class is None when the emotion is out of
    vocabulary and the active variant does not map it.
    """
    if emotion is None:
        return "non_distress", "empty_emotions_list"
    if emotion in ANXIOSENSE_TO_EVAL_CLASS:
        return ANXIOSENSE_TO_EVAL_CLASS[emotion], "in_vocabulary"
    if oov_map and emotion in oov_map:
        return oov_map[emotion], "out_of_vocab_mapped"
    return None, "out_of_vocab_unmapped"


def main() -> None:
    ap = argparse.ArgumentParser(description="Offline re-analysis of Stage C outputs")
    ap.add_argument("--stage-dir", default=str(DEFAULT_STAGE_DIR))
    args = ap.parse_args()

    stage_dir = Path(args.stage_dir)
    raw_dir = stage_dir / "raw"
    if not raw_dir.is_dir():
        sys.exit(f"ERROR: raw directory not found: {raw_dir}")

    out_primary = stage_dir / "reparsed" / "primary"
    out_sens = stage_dir / "reparsed" / "sensitivity"
    out_report = stage_dir / "reanalysis"
    for d in (out_primary, out_sens, out_report):
        d.mkdir(parents=True, exist_ok=True)

    audit_rows = []
    status_by_cell = defaultdict(Counter)
    rerun_rows = []
    files = sorted(raw_dir.glob("*.jsonl"))
    if not files:
        sys.exit(f"ERROR: no .jsonl files in {raw_dir}")

    print(f"Re-analysing {len(files)} raw files from {raw_dir}\n")

    for path in files:
        records = [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]
        prim_out, sens_out = [], []

        for rec in records:
            dataset = rec.get("dataset")
            cell = (dataset, rec.get("strategy"))

            # Dreaddit is unaffected — pass through untouched.
            if dataset != "goemotions":
                prim_out.append(dict(rec))
                sens_out.append(dict(rec))
                status_by_cell[cell]["passthrough_dreaddit"] += 1
                continue

            old_label = rec.get("label")

            # An HTTP/provider error means no payload ever arrived. Preserve the
            # original failure; it is a genuine failure, not a parsing artefact.
            if rec.get("api_error"):
                status = "fail_api_error"
                emotions = None
            else:
                status, emotions = extract_emotion_payload(rec.get("emotion_agent_raw"))

            emotion = primary_emotion(emotions) if status in OK_STATUSES else None
            status_by_cell[cell][status] += 1

            variants = {}
            for name, oov in (("primary", None), ("sensitivity", OOV_SENSITIVITY_MAP)):
                if status not in OK_STATUSES:
                    variants[name] = (None, f"parse_failure:{status}")
                else:
                    cls, note = eval_class_for(emotion, oov)
                    variants[name] = (
                        (cls, None) if cls is not None
                        else (None, f"out_of_vocab:{emotion}")
                    )

            for name, bucket in (("primary", prim_out), ("sensitivity", sens_out)):
                label, failure = variants[name]
                new = dict(rec)
                new["label"] = label
                new["failure_reason"] = failure
                new["reparse_status"] = status
                new["reparse_variant"] = name
                new["predicted_emotion_raw"] = emotion
                new["include_in_primary_metrics"] = label is not None
                new["exclusion_reason"] = failure
                bucket.append(new)

            audit_rows.append({
                "sample_id":        rec.get("sample_id"),
                "dataset":          dataset,
                "strategy":         rec.get("strategy"),
                "ground_truth":     rec.get("ground_truth"),
                "old_label":        old_label,
                "reparse_status":   status,
                "predicted_emotion": emotion,
                "primary_label":     variants["primary"][0],
                "sensitivity_label": variants["sensitivity"][0],
                "recovered":        old_label is None and variants["primary"][0] is not None,
                "raw_len":          len(rec.get("emotion_agent_raw") or ""),
            })

            if status not in OK_STATUSES:
                rerun_rows.append({
                    "sample_id":    rec.get("sample_id"),
                    "dataset":      dataset,
                    "strategy":     rec.get("strategy"),
                    "ground_truth": rec.get("ground_truth"),
                    "reason":       status,
                    "raw_len":      len(rec.get("emotion_agent_raw") or ""),
                    "note":         "unrecoverable offline — payload never fully persisted"
                                    if status == "fail_truncated" else
                                    "genuine invalid model output or transport loss",
                })

        for bucket, outdir in ((prim_out, out_primary), (sens_out, out_sens)):
            with (outdir / path.name).open("w", encoding="utf-8") as fh:
                for r in bucket:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    def write_csv(path, rows, fields=None):
        if not rows:
            return
        fields = fields or list(rows[0].keys())
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)

    write_csv(out_report / "reparse_audit.csv", audit_rows)
    write_csv(out_report / "rerun_manifest.csv", rerun_rows)

    summary_rows = []
    for (dataset, strategy), counter in sorted(status_by_cell.items()):
        if dataset != "goemotions":
            continue
        total = sum(counter.values())
        ok = sum(v for k, v in counter.items() if k in OK_STATUSES)
        row = {"dataset": dataset, "strategy": strategy, "n_total": total,
               "n_parsed_after_fix": ok, "n_failed_after_fix": total - ok,
               "parse_rate": round(ok / total, 4) if total else 0.0}
        row.update({k: counter.get(k, 0) for k in sorted(counter)})
        summary_rows.append(row)

    all_keys = sorted({k for r in summary_rows for k in r})
    lead = ["dataset", "strategy", "n_total", "n_parsed_after_fix",
            "n_failed_after_fix", "parse_rate"]
    write_csv(out_report / "reparse_summary.csv", summary_rows,
              lead + [k for k in all_keys if k not in lead])

    recovered = sum(1 for r in audit_rows if r["recovered"])
    print(f"  GoEmotions records examined : {len(audit_rows)}")
    print(f"  Newly recovered predictions : {recovered}")
    print(f"  Still unrecoverable         : {len(rerun_rows)}")
    print(f"\n  Corrected records → {out_primary}")
    print(f"                      {out_sens}")
    print(f"  Audit + manifest  → {out_report}")


if __name__ == "__main__":
    main()
