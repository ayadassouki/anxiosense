#!/usr/bin/env python3
"""
audit_pilot.py — accept/reject a Stage C pilot cell against the frozen configuration.

Run AFTER the pilot cell finishes:

    cd ~/anxiosense/evaluation/llm-experiments
    python3 scripts/audit_pilot.py outputs/stage_c_pilot

Performs every gate in one pass and prints a single verdict. Read-only.

CHECKS
  1  Corruption            no payload missing a required key; no unbalanced JSON key
  2  Provider column       upstream_provider populated on every row, single value, pinned
  3  Decoding recorded     temperature / max_tokens present in the cell metadata and frozen
  4  Completeness          every frozen sample id present exactly once, no duplicates
  5  Failure profile       failure counts and their composition (OOV vs unparseable)
  6  Pipeline health       quality flags, provider errors, latency

Exit 0 = acceptable as the production configuration. 1 = not acceptable.
"""
from __future__ import annotations

import csv
import glob
import json
import os
import re
import sys
import collections

csv.field_size_limit(10 ** 7)

EXPECTED_PROVIDER = "DeepInfra"
EXPECTED_TEMPERATURE = 0.0
EXPECTED_MAX_TOKENS = 4096
REQUIRED_KEYS = ['"emotions"', '"emotional_intensity"', '"evidence_from_text"']

fails: list[str] = []
warns: list[str] = []


def head(n: str) -> None:
    print("\n" + "=" * 74)
    print(n)
    print("=" * 74)


def unbalanced_keys(text: str) -> list[str]:
    """A JSON key is always "name": — a dropped token that eats the opening quote
    leaves name": with nothing in front. Prose cannot produce that shape."""
    hits = set()
    for m in re.finditer(r'([A-Za-z_][A-Za-z_0-9]*)"\s*:', text):
        if m.start(1) == 0 or text[m.start(1) - 1] != '"':
            hits.add(m.group(0).strip()[:40])
    return sorted(hits)


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "outputs/stage_c_pilot"
    raw_dir = os.path.join(base, "raw")
    meta_dir = os.path.join(base, "metadata")

    csvs = sorted(glob.glob(os.path.join(raw_dir, "*.csv")))
    if not csvs:
        print(f"no CSVs under {raw_dir} — did the pilot write somewhere else?")
        return 1

    print(f"auditing {len(csvs)} cell(s) under {base}")
    rows: list[dict] = []
    per_cell: dict[str, list[dict]] = {}
    for p in csvs:
        rs = list(csv.DictReader(open(p)))
        print(f"  {os.path.basename(p)}  n={len(rs)}")
        per_cell[os.path.basename(p)] = rs
        rows += rs

    # ── 1. corruption ────────────────────────────────────────────────────────
    head("1. CORRUPTION")
    corrupt = []
    for r in rows:
        raw = r.get("emotion_agent_raw") or ""
        if not raw.strip():
            continue
        missing = [k for k in REQUIRED_KEYS if k not in raw]
        unbal = unbalanced_keys(raw)
        if missing or unbal:
            corrupt.append((r["sample_id"], missing, unbal, raw[:110]))
    print(f"  rows with a payload : {sum(1 for r in rows if (r.get('emotion_agent_raw') or '').strip())}")
    print(f"  corrupted           : {len(corrupt)}")
    for sid, miss, unbal, snippet in corrupt[:10]:
        print(f"    {sid}  missing={miss} unbalanced={unbal}\n      {snippet!r}")
    if corrupt:
        fails.append(f"{len(corrupt)} corrupted payload(s)")

    # ── 2. provider column ───────────────────────────────────────────────────
    head("2. UPSTREAM PROVIDER COLUMN")
    if "upstream_provider" not in (rows[0] if rows else {}):
        fails.append("upstream_provider column is absent — the server is running stale code")
        print("  COLUMN ABSENT. Restart the Mastra and Express servers and re-run the pilot.")
    else:
        vals = collections.Counter(r.get("upstream_provider") or "<empty>" for r in rows)
        allv = collections.Counter(r.get("upstream_providers_all") or "<empty>" for r in rows)
        print(f"  upstream_provider      : {dict(vals)}")
        print(f"  upstream_providers_all : {dict(allv)}")
        empty = vals.get("<empty>", 0)
        if empty:
            fails.append(f"{empty} row(s) have an empty upstream_provider")
        off = {k: v for k, v in vals.items() if k not in ("<empty>", EXPECTED_PROVIDER)}
        if off:
            fails.append(f"rows served by an unexpected upstream: {off}")
        if any("MIXED" in str(k) for k in vals):
            fails.append("at least one assessment hit more than one upstream (MIXED)")

    # ── 3. decoding parameters recorded ──────────────────────────────────────
    head("3. DECODING PARAMETERS IN METADATA")
    metas = sorted(glob.glob(os.path.join(meta_dir, "*_meta.json")))
    if not metas:
        fails.append("no metadata files found")
        print(f"  none under {meta_dir}")
    for mp in metas:
        m = json.load(open(mp))
        dec = m.get("decoding") or {}
        ok = (dec.get("temperature") == EXPECTED_TEMPERATURE
              and dec.get("max_tokens") == EXPECTED_MAX_TOKENS)
        print(f"  {os.path.basename(mp)[:56]:56s} decoding={dec} {'OK' if ok else 'MISMATCH'}")
        if not ok:
            fails.append(f"{os.path.basename(mp)}: decoding block missing or not frozen values")

    # ── 4. completeness ──────────────────────────────────────────────────────
    head("4. COMPLETENESS")
    # Duplicates are only meaningful WITHIN a cell — the same sample_id legitimately
    # appears once per (strategy, run), so a multi-cell directory would false-alarm.
    for cell, rs in per_cell.items():
        ids = [r["sample_id"] for r in rs]
        dupes = {k: v for k, v in collections.Counter(ids).items() if v > 1}
        print(f"  {cell[:52]:52s} rows={len(rs):>4} unique={len(set(ids)):>4} "
              f"dupes={len(dupes)}")
        if dupes:
            fails.append(f"{cell}: duplicate sample ids {list(dupes)[:5]}")

        stem = cell[:-4]
        mp = os.path.join(meta_dir, stem + "_meta.json")
        if os.path.exists(mp):
            m = json.load(open(mp))
            expected = set(map(str, m.get("sample_ids") or []))
            missing = expected - set(ids)
            print(f"    frozen set {len(expected)} ids "
                  f"sha={str(m.get('sample_ids_sha256'))[:16]}… missing={len(missing)}")
            if missing:
                fails.append(f"{cell}: {len(missing)} frozen sample id(s) produced no row")

    # ── 5. failure profile ───────────────────────────────────────────────────
    head("5. FAILURE PROFILE")
    reasons = collections.Counter(
        (r.get("failure_reason") or "").split(":")[0].strip()
        for r in rows if (r.get("failure_reason") or "").strip())
    n_fail = sum(reasons.values())
    print(f"  failures       : {n_fail}/{len(rows)} = {100*n_fail/max(len(rows),1):.1f}%")
    for k, v in reasons.most_common():
        print(f"     {v:>3}  {k}")
    unparseable = sum(v for k, v in reasons.items() if "unparseable" in k or "truncated" in k)
    if unparseable:
        warns.append(f"{unparseable} unparseable/truncated payload(s) — expected 0 under the fix")

    # ── 6. pipeline health ───────────────────────────────────────────────────
    head("6. PIPELINE HEALTH")
    def count_true(col: str) -> int:
        return sum(1 for r in rows if str(r.get(col, "")).strip().lower() in ("true", "1"))
    for col in ("is_provider_error", "agent_json_parse_failed", "fallback_claim_injected",
                "referral_risk_fallback_used", "recommendation_rejected", "safety_override"):
        n = count_true(col)
        print(f"  {col:30s} {n}")
        if col == "is_provider_error" and n:
            warns.append(f"{n} provider error(s) — allow_fallbacks:false makes outages hard-fail")
        if col == "agent_json_parse_failed" and n:
            warns.append(f"{n} row(s) with agent_json_parse_failed")
    lats = [float(r["latency_ms"]) for r in rows if (r.get("latency_ms") or "").strip()]
    if lats:
        lats.sort()
        print(f"  latency ms     : median {lats[len(lats)//2]:.0f}  "
              f"p95 {lats[int(len(lats)*0.95)]:.0f}  max {lats[-1]:.0f}")
        print(f"  projected full run (600 assessments): "
              f"{lats[len(lats)//2]*600/1000/60:.0f} min at the median")

    # ── verdict ──────────────────────────────────────────────────────────────
    head("VERDICT")
    if fails:
        print("  NOT ACCEPTABLE as the production configuration:")
        for f in fails:
            print(f"    FAIL  {f}")
    else:
        print("  ACCEPTABLE as the production configuration.")
    for w in warns:
        print(f"    WARN  {w}")
    if not fails and not warns:
        print("    no warnings")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
