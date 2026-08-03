#!/usr/bin/env python3
"""
Merge targeted re-collection results into a copy of a raw results directory.

DESIGN CONSTRAINT — the original raw directory is NEVER written to.
This script reads <original-dir>, reads <rerun-dir>, and writes a NEW
<output-dir>. It refuses to run if the output path resolves inside the
original path.

HOW UNAFFECTED RECORDS ARE PRESERVED
Records that are not being replaced are copied as their VERBATIM ORIGINAL
LINE — the raw text is passed through untouched, never parsed-and-reserialised.
This is a stronger guarantee than re-dumping equal JSON: key order, spacing,
unicode escaping and float formatting cannot drift. Every unaffected line is
SHA-256 checked before and after, and the run aborts if any hash differs.

WHAT MAY BE REPLACED
Only (sample_id, strategy) pairs listed in the manifest AND present in the
rerun directory. A rerun record for a sample not in the manifest is reported
and skipped, so an over-broad rerun cannot silently overwrite good data.

PROVENANCE
Replaced records gain:
    record_origin        "rerun"
    superseded_reason    the manifest reason the original failed
    superseded_run_file  the file the original came from
    merged_at_utc        merge timestamp
Original (kept) records are untouched and carry no extra fields.

Usage
-----
  python scripts/merge_rerun.py \
      --original-dir outputs/stage_c/raw \
      --rerun-dir    outputs/stage_c/rerun/raw \
      --manifest     outputs/stage_c/reanalysis/rerun_manifest.csv \
      --output-dir   outputs/stage_c/merged/raw
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

REPO_ROOT = Path(__file__).resolve().parents[3]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_cell(filename: str) -> Optional[Tuple[str, str, str, int]]:
    """
    Split '<dataset>_<model_slug>_<strategy>_run<N>.jsonl' into parts.

    Strategy names contain hyphens, model slugs contain underscores, so parse
    from the known ends inward rather than by naive split.
    """
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
    # Strategy is the trailing token(s); model slug is everything before it.
    for strat in ("zero-shot-cot", "one-shot-cot", "few-shot-cot",
                  "zero-shot", "one-shot", "few-shot"):
        if rest.endswith("_" + strat):
            model_slug = rest[: -(len(strat) + 1)]
            return dataset, model_slug, strat, run
    model_slug, _, strat = rest.rpartition("_")
    return dataset, model_slug, strat, run


def _load_lines(path: Path) -> List[Tuple[str, dict]]:
    """Return [(verbatim_line, parsed_record)] preserving file order."""
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--original-dir", required=True)
    ap.add_argument("--rerun-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--manifest", required=True,
                    help="CSV with sample_id, strategy, reason columns.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Report what would change; write nothing.")
    args = ap.parse_args()

    original = Path(args.original_dir).resolve()
    rerun = Path(args.rerun_dir).resolve()
    output = Path(args.output_dir).resolve()

    # ── Guard: never write into the originals ──────────────────────────────
    if output == original or original in output.parents:
        print(f"REFUSING: --output-dir ({output}) is inside --original-dir "
              f"({original}). The originals must stay untouched.")
        sys.exit(1)
    if not original.is_dir():
        print(f"Original dir not found: {original}"); sys.exit(1)
    if not rerun.is_dir():
        print(f"Rerun dir not found: {rerun}"); sys.exit(1)

    # ── Manifest: the allow-list of replaceable records ────────────────────
    allowed: Dict[Tuple[str, str], str] = {}
    with Path(args.manifest).open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            allowed[(r["sample_id"].strip(), r["strategy"].strip())] = \
                r.get("reason", "").strip()
    print(f"Manifest: {len(allowed)} replaceable (sample_id, strategy) pairs\n")

    # ── Index rerun records by (sample_id, strategy) ───────────────────────
    rerun_idx: Dict[Tuple[str, str], dict] = {}
    rerun_dupes: List[Tuple[str, str]] = []
    for f in sorted(rerun.glob("*.jsonl")):
        parsed = _parse_cell(f.name)
        if not parsed:
            continue
        _, _, strat, _ = parsed
        for _, rec in _load_lines(f):
            key = (str(rec.get("sample_id", "")), strat)
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
              f"these will be IGNORED, not merged:")
        for k in unexpected[:10]:
            print(f"      {k[0]}  {k[1]}")

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
        # (position, original_line) for every record we did NOT replace.
        kept_positions: List[Tuple[int, str]] = []
        n_repl = n_keep = 0

        for verbatim, rec in lines:
            sid = str(rec.get("sample_id", ""))
            key = (sid, strat)
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
                # VERBATIM passthrough — original bytes, never re-serialised.
                kept_positions.append((len(out_lines), verbatim))
                out_lines.append(verbatim)
                n_keep += 1
                if replacement is not None:
                    audit.append({
                        "file": src.name, "sample_id": sid, "strategy": strat,
                        "run": run, "action": "rerun_ignored_not_in_manifest",
                        "reason": "", "original_sha256": _sha(verbatim)[:16],
                    })

        # ── Verify every kept line is byte-identical, by position ──────────
        # Positional rather than set-based: catches reordering as well as
        # mutation, and is unaffected by duplicate identical lines.
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

    # Carry metadata across unchanged so the merged dir is self-describing.
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
        for sid, st in missing[:40]:
            print(f"    {sid}  {st}  ({allowed[(sid, st)]})")

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
