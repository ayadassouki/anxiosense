#!/usr/bin/env python3
"""
merge_rerun_multirun.py — run-aware variant of merge_rerun.py.

WHY THIS EXISTS
merge_rerun.py keys replacements on (sample_id, strategy) WITHOUT the run
number — documented as safe only when a single run exists (the DeepSeek run-1
case). The Gemma Dreaddit re-dispatch spans 5 runs and 14 of the 54 unique
timed-out ids appear in MORE THAN ONE run, so the run-agnostic key would
splice a run-1 re-collection into run 2..5 files (cross-run contamination).
This variant keys on (sample_id, strategy, run) everywhere. All other
guarantees are inherited unchanged from merge_rerun.py:

  * originals NEVER written; refuses output inside original dir
  * unaffected records passed through as VERBATIM ORIGINAL LINES,
    SHA-256 checked positionally before write
  * manifest is an allow-list; rerun records not in the manifest are ignored
  * provenance fields added to replaced records; audit CSV written
  * --dry-run

MANIFEST FORMAT
CSV with columns: sample_id, strategy, run, reason   (run is new/required)

Usage
-----
  python3 scripts/merge_rerun_multirun.py \
      --original-dir outputs/stage_c_defaults/raw \
      --rerun-dir    outputs/stage_c_defaults_rerun_gemma/raw \
      --manifest     outputs/stage_c_defaults/rerun_plan_gemma/infra_manifest.csv \
      --output-dir   outputs/stage_c_defaults_merged_gemma/raw --dry-run
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_cell(filename: str) -> Optional[Tuple[str, str, str, int]]:
    stem = filename[:-len(".jsonl")] if filename.endswith(".jsonl") else filename
    if "_run" not in stem:
        return None
    head, _, run_part = stem.rpartition("_run")
    try:
        run = int(run_part)
    except ValueError:
        return None
    dataset, _, rest = head.partition("_")
    if not rest:
        return None
    for strat in ("zero-shot-cot", "one-shot-cot", "few-shot-cot",
                  "zero-shot", "one-shot", "few-shot"):
        if rest.endswith("_" + strat):
            model_slug = rest[: -(len(strat) + 1)]
            return dataset, model_slug, strat, run
    model_slug, _, strat = rest.rpartition("_")
    return dataset, model_slug, strat, run


def _load_lines(path: Path) -> List[Tuple[str, dict]]:
    out: List[Tuple[str, dict]] = []
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                out.append((line.rstrip("\n"), json.loads(line)))
            except json.JSONDecodeError as exc:
                print(f"  ! {path.name}:{lineno} unparseable JSON — {exc}")
                sys.exit(1)
    return out


Key = Tuple[str, str, int]  # (sample_id, strategy, run)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--original-dir", required=True)
    ap.add_argument("--rerun-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--manifest", required=True,
                    help="CSV with sample_id, strategy, run, reason columns.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    original = Path(args.original_dir).resolve()
    rerun = Path(args.rerun_dir).resolve()
    output = Path(args.output_dir).resolve()

    if output == original or original in output.parents:
        print(f"REFUSING: --output-dir ({output}) is inside --original-dir "
              f"({original}). The originals must stay untouched.")
        sys.exit(1)
    if not original.is_dir():
        print(f"Original dir not found: {original}"); sys.exit(1)
    if not rerun.is_dir():
        print(f"Rerun dir not found: {rerun}"); sys.exit(1)

    # ── Manifest: allow-list keyed (sample_id, strategy, run) ──────────────
    allowed: Dict[Key, str] = {}
    with Path(args.manifest).open(encoding="utf-8") as fh:
        rdr = csv.DictReader(fh)
        if "run" not in (rdr.fieldnames or []):
            print("REFUSING: manifest has no 'run' column. This script requires "
                  "a run-aware manifest; a run-agnostic one is exactly the "
                  "hazard it exists to prevent.")
            sys.exit(1)
        for r in rdr:
            allowed[(r["sample_id"].strip(), r["strategy"].strip(),
                     int(r["run"]))] = r.get("reason", "").strip()
    print(f"Manifest: {len(allowed)} replaceable (sample_id, strategy, run) triples\n")

    # ── Index rerun records by (sample_id, strategy, run) ──────────────────
    # Run comes from the rerun FILENAME (the harness writes run{N} files when
    # --run-start N is used), cross-checked against the record's own field.
    rerun_idx: Dict[Key, dict] = {}
    rerun_dupes: List[Key] = []
    for f in sorted(rerun.glob("*.jsonl")):
        parsed = _parse_cell(f.name)
        if not parsed:
            continue
        _, _, strat, run = parsed
        for _, rec in _load_lines(f):
            rec_run = rec.get("run")
            if rec_run is not None and int(rec_run) != run:
                print(f"  !! {f.name}: record {rec.get('sample_id')} has "
                      f"run={rec_run} but filename says run{run} — aborting")
                sys.exit(1)
            key = (str(rec.get("sample_id", "")), strat, run)
            if key in rerun_idx:
                rerun_dupes.append(key)
            rerun_idx[key] = rec
    print(f"Rerun dir: {len(rerun_idx)} record(s) indexed")
    if rerun_dupes:
        print(f"  ! {len(rerun_dupes)} duplicate key(s); last occurrence wins: "
              f"{sorted(set(rerun_dupes))[:5]}")

    unexpected = sorted(set(rerun_idx) - set(allowed))
    if unexpected:
        print(f"  ! {len(unexpected)} rerun record(s) NOT in the manifest — "
              f"IGNORED, not merged:")
        for k in unexpected[:10]:
            print(f"      {k[0]}  {k[1]}  run{k[2]}")

    if not args.dry_run:
        output.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    audit: List[dict] = []
    totals = defaultdict(int)

    for src in sorted(original.glob("*.jsonl")):
        parsed = _parse_cell(src.name)
        if not parsed:
            print(f"  ? skipping unrecognised filename: {src.name}")
            continue
        dataset, _, strat, run = parsed
        lines = _load_lines(src)

        out_lines: List[str] = []
        kept_positions: List[Tuple[int, str]] = []
        n_repl = n_keep = 0

        for verbatim, rec in lines:
            sid = str(rec.get("sample_id", ""))
            key = (sid, strat, run)
            replacement = rerun_idx.get(key)

            if replacement is not None and key in allowed:
                new = dict(replacement)
                new["record_origin"] = "rerun"
                new["superseded_reason"] = allowed[key]
                new["superseded_run_file"] = src.name
                new["merged_at_utc"] = now
                out_lines.append(json.dumps(new, ensure_ascii=False))
                n_repl += 1
                audit.append({
                    "file": src.name, "sample_id": sid, "strategy": strat,
                    "run": run, "action": "replaced",
                    "reason": allowed[key],
                    "original_sha256": _sha(verbatim)[:16],
                })
            else:
                kept_positions.append((len(out_lines), verbatim))
                out_lines.append(verbatim)
                n_keep += 1
                if replacement is not None:
                    audit.append({
                        "file": src.name, "sample_id": sid, "strategy": strat,
                        "run": run, "action": "rerun_ignored_not_in_manifest",
                        "reason": "", "original_sha256": _sha(verbatim)[:16],
                    })

        for pos, original_line in kept_positions:
            if _sha(out_lines[pos]) != _sha(original_line):
                print(f"  !! {src.name}: unaffected record at position {pos} "
                      f"was altered — aborting")
                sys.exit(1)

        if len(out_lines) != len(lines):
            print(f"  !! {src.name}: record count changed "
                  f"{len(lines)} → {len(out_lines)} — aborting")
            sys.exit(1)

        flag = "*" if n_repl else " "
        print(f" {flag} {src.name:58s} {len(lines):>4d} records  "
              f"replaced={n_repl:<3d} kept={n_keep}")
        totals["replaced"] += n_repl
        totals["kept"] += n_keep

        if not args.dry_run:
            (output / src.name).write_text(
                "\n".join(out_lines) + "\n", encoding="utf-8")

    meta_src = original.parent / "metadata"
    if meta_src.is_dir() and not args.dry_run:
        meta_dst = output.parent / "metadata"
        meta_dst.mkdir(parents=True, exist_ok=True)
        for m in meta_src.glob("*.json"):
            shutil.copy2(m, meta_dst / m.name)

    print(f"\nTotal: {totals['replaced']} replaced, {totals['kept']} kept verbatim")
    missing = sorted(set(allowed) - set(rerun_idx))
    if missing:
        print(f"\n{len(missing)} manifest record(s) had NO rerun result "
              f"(still unrecovered):")
        for sid, st, rn in missing[:40]:
            print(f"    {sid}  {st}  run{rn}  ({allowed[(sid, st, rn)]})")

    if args.dry_run:
        print("\nDRY RUN — nothing written.")
        return

    audit_path = output.parent / "merge_audit.csv"
    with audit_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "file", "sample_id", "strategy", "run", "action",
            "reason", "original_sha256"])
        w.writeheader()
        w.writerows(audit)
    print(f"\nMerged raw  → {output}")
    print(f"Merge audit → {audit_path}")
    print(f"Originals   → {original}  (NOT modified)")


if __name__ == "__main__":
    main()
