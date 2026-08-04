#!/usr/bin/env python3
"""
audit_pilot.py — accept/reject a Stage C pilot cell against the approved configuration.

Run AFTER the pilot cell finishes:

    cd ~/anxiosense/evaluation/llm-experiments
    python3 scripts/audit_pilot.py outputs/stage_c_defaults

Performs every gate in one pass and prints a single verdict. Read-only.

CHECKS
  1  Corruption            no payload missing a required key; no unbalanced JSON key
  2  Provider column       upstream_provider populated on every row, single value,
                           and equal to the pin recorded for that cell's model
  3  Decoding provenance   provider defaults in force — temperature / max_tokens /
                           seed NOT sent, and the provenance block records that
  4  Completeness          every frozen sample id present exactly once, no duplicates
  5  Failure profile       failure counts and their composition (OOV vs unparseable)
  6  Pipeline health       quality flags, provider errors, latency

Exit 0 = acceptable as the production configuration. 1 = not acceptable.

METHODOLOGY 2026-08-04
  This script previously gated on temperature == 0.0 and max_tokens == 4096. That
  freeze is superseded: each model now uses its own provider default, which means
  the parameters are OMITTED from the request rather than set to a value. The
  expected pin is per-model, read from each cell's metadata, not a global constant.
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

# Fallback only — the authoritative pin for a cell is metadata.decoding.pin_provider,
# written by run_experiments.py. This table is used when that field is absent
# (e.g. a cell collected before the provenance block existed).
FALLBACK_PIN = {
    "meta-llama/llama-4-scout":     "DeepInfra",
    "mistralai/mistral-small-2603": "Mistral",
    "google/gemma-4-31b-it":        "DeepInfra",
    "deepseek/deepseek-v4-flash":   "DeepInfra",
    "microsoft/phi-4":              "DeepInfra",
}

# Models whose pinned provider exposes more than one endpoint. For these the cell
# metadata MUST record an enforced precision filter, otherwise the run could have
# been served at a different quantisation and nothing in the response would show it.
REQUIRES_QUANT_FILTER = {
    "google/gemma-4-31b-it": "fp4",
}

# Parameters that MUST NOT have been sent under the provider-default methodology.
MUST_BE_UNSENT = ("temperature_sent", "max_tokens_sent", "seed_sent")

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


def load_metas(meta_dir: str) -> dict:
    """stem -> parsed metadata, for every *_meta.json under meta_dir."""
    out = {}
    for mp in sorted(glob.glob(os.path.join(meta_dir, "*_meta.json"))):
        stem = os.path.basename(mp)[: -len("_meta.json")]
        try:
            out[stem] = json.load(open(mp))
        except Exception as exc:                                  # noqa: BLE001
            fails.append(f"{os.path.basename(mp)}: unreadable ({exc})")
    return out


def expected_pin_for(meta):
    """The upstream provider this cell should have been served by, or None."""
    if meta:
        dec = meta.get("decoding") or {}
        pin = dec.get("pin_provider")
        if pin:
            return str(pin)
        model = meta.get("model")
        if model in FALLBACK_PIN:
            return FALLBACK_PIN[model]
    return None


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "outputs/stage_c_defaults"
    raw_dir = os.path.join(base, "raw")
    meta_dir = os.path.join(base, "metadata")

    csvs = sorted(glob.glob(os.path.join(raw_dir, "*.csv")))
    if not csvs:
        print(f"no CSVs under {raw_dir} — did the pilot write somewhere else?")
        return 1

    metas = load_metas(meta_dir)

    print(f"auditing {len(csvs)} cell(s) under {base}")
    rows: list[dict] = []
    per_cell: dict[str, list[dict]] = {}
    for p in csvs:
        rs = list(csv.DictReader(open(p)))
        print(f"  {os.path.basename(p)}  n={len(rs)}")
        per_cell[os.path.basename(p)] = rs
        rows += rs

    # -- 1. corruption -------------------------------------------------------
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

    # -- 2. provider column, checked per cell against that cell's pin --------
    head("2. UPSTREAM PROVIDER COLUMN")
    if rows and "upstream_provider" not in rows[0]:
        fails.append("upstream_provider column is absent — the server is running stale code")
        print("  COLUMN ABSENT. Restart the Mastra and Express servers and re-run the pilot.")
    else:
        for cell, rs in per_cell.items():
            meta = metas.get(cell[:-4])
            want = expected_pin_for(meta)
            vals = collections.Counter(r.get("upstream_provider") or "<empty>" for r in rs)
            allv = collections.Counter(r.get("upstream_providers_all") or "<empty>" for r in rs)
            print(f"  {cell[:52]:52s} expected={want or '<unknown>'}")
            print(f"      upstream_provider      : {dict(vals)}")
            print(f"      upstream_providers_all : {dict(allv)}")

            empty = vals.get("<empty>", 0)
            if empty:
                fails.append(f"{cell}: {empty} row(s) have an empty upstream_provider")
            if any("MIXED" in str(k) for k in vals):
                fails.append(f"{cell}: at least one assessment hit more than one upstream (MIXED)")
            if want is None:
                warns.append(f"{cell}: no pin recorded in metadata — cannot verify the upstream")
            else:
                off = {k: v for k, v in vals.items() if k not in ("<empty>", want)}
                if off:
                    fails.append(f"{cell}: rows served by an unexpected upstream: {off}")

    # -- 3. decoding provenance ---------------------------------------------
    head("3. DECODING PROVENANCE (provider defaults)")
    if not metas:
        fails.append("no metadata files found")
        print(f"  none under {meta_dir}")
    for stem, m in metas.items():
        dec = m.get("decoding") or {}
        mode = dec.get("mode")
        sent = {k: dec.get(k) for k in MUST_BE_UNSENT}
        unsent_ok = all(v is None for v in sent.values())
        mode_ok = (mode == "provider_default")
        # A legacy frozen-temperature cell is a hard fail here, not a warning:
        # mixing the two methodologies in one output directory is exactly what
        # this gate exists to prevent.
        legacy = ("temperature" in dec and "temperature_sent" not in dec)
        ok = mode_ok and unsent_ok and not legacy
        print(f"  {stem[:52]:52s} mode={mode} sent={sent} {'OK' if ok else 'MISMATCH'}")
        if legacy:
            fails.append(f"{stem}: legacy frozen-decoding metadata "
                         f"(temperature={dec.get('temperature')}) — that cell belongs in "
                         f"outputs/stage_c_v2/, not here")
        elif not mode_ok:
            fails.append(f"{stem}: decoding.mode is {mode!r}, expected 'provider_default'")
        elif not unsent_ok:
            bad = {k: v for k, v in sent.items() if v is not None}
            fails.append(f"{stem}: a decoding parameter was sent: {bad}")
        doc = dec.get("temperature_documented")
        if doc is not None:
            print(f"      documented provider default temperature = {doc} "
                  f"(source: {dec.get('temperature_source')})")

        # Precision. Only a hard requirement for models with >1 endpoint at the pin.
        model_id = m.get("model")
        pin_q = dec.get("pin_quantization")
        obs_q = dec.get("observed_quantization")
        print(f"      quantization: pinned={pin_q!r} enforced={dec.get('quantization_enforced')} "
              f"observed={obs_q!r}")
        need = REQUIRES_QUANT_FILTER.get(model_id)
        if need and pin_q != need:
            fails.append(
                f"{stem}: {model_id} is served by multiple endpoints at its pinned provider "
                f"and requires quantization={need!r}, but metadata records {pin_q!r} — the cell "
                f"may have been served at another precision, and the response cannot reveal it")

    # -- 4. completeness -----------------------------------------------------
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

        m = metas.get(cell[:-4])
        if m:
            expected = set(map(str, m.get("sample_ids") or []))
            missing = expected - set(ids)
            print(f"    frozen set {len(expected)} ids "
                  f"sha={str(m.get('sample_ids_sha256'))[:16]}… missing={len(missing)}")
            if missing:
                fails.append(f"{cell}: {len(missing)} frozen sample id(s) produced no row")

    # -- 5. failure profile --------------------------------------------------
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

    # -- 6. pipeline health --------------------------------------------------
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

    # -- verdict -------------------------------------------------------------
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
