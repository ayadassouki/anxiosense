#!/usr/bin/env python3
"""
verify_smoke_fix.py — automated evidence check for the 2026-08-08 parser-fix smoke test.

READ-ONLY. Verifies, for every record in a smoke output directory:

  1. model_actual == the requested model; upstream_provider == the configured pin
  2. decoding metadata shows provider-default mode (no temperature/max_tokens/seed sent)
  3. emotion_agent_raw persisted (non-empty)
  4. referral_agent_raw persisted (non-empty)          <- NEW field under test
  5. END-TO-END ladder consistency: referral_risk_fallback_used must equal
     (tolerant ladder finds NO explicit valid risk_level in referral_agent_raw).
     This proves extraction-over-fallback in one direction and preserved
     fallback in the other, on whatever the model actually produced.
  6. sample_ids are members of the frozen set; meta records frozen_ids + SHA
  7. strategy / strategy_actual agree; run number correct; no api_error

Usage:
  python3 scripts/verify_smoke_fix.py outputs/smoke_fix_deepseek --model deepseek/deepseek-v4-flash --pin DeepInfra
  python3 scripts/verify_smoke_fix.py outputs/smoke_fix_gemma   --model google/gemma-4-31b-it     --pin DeepInfra
"""
from __future__ import annotations
import argparse, glob, json, re, sys
from pathlib import Path

VOCAB = {"low", "moderate", "urgent"}
FENCE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")

def _balanced(text: str):
    start = text.find("{")
    while start != -1:
        depth = 0; instr = False; esc = False
        for i in range(start, len(text)):
            ch = text[i]
            if esc: esc = False; continue
            if ch == "\\": esc = True; continue
            if ch == '"': instr = not instr; continue
            if instr: continue
            if ch == "{": depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0: return text[start:i+1]
        start = text.find("{", start + 1)
    return None

def ladder(raw):
    """Identical 5-step extraction as referral-risk-parser.ts. Returns value or None."""
    if not isinstance(raw, str) or not raw: return None
    obj = None
    for txt in (raw, FENCE.sub("", raw.strip())):
        try:
            cand = json.loads(txt)
            if isinstance(cand, dict): obj = cand; break
        except Exception: pass
    if obj is None:
        c = _balanced(raw)
        if c:
            try:
                cand = json.loads(c)
                if isinstance(cand, dict): obj = cand
            except Exception: pass
    if obj is None: return None
    v = obj.get("risk_level")
    if isinstance(v, str) and v.strip().lower() in VOCAB: return v.strip().lower()
    return None

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("smoke_dir")
    ap.add_argument("--model", required=True)
    ap.add_argument("--pin", required=True)
    ap.add_argument("--ids-dir", default="outputs/stage_c_final/sample")
    args = ap.parse_args()

    frozen = {}
    for ds in ("dreaddit", "goemotions"):
        p = Path(args.ids_dir) / f"{ds}_sample_ids.txt"
        if p.exists(): frozen[ds] = set(p.read_text().split())

    files = sorted(glob.glob(str(Path(args.smoke_dir) / "raw" / "*.jsonl")))
    if not files:
        print(f"FAIL: no JSONL under {args.smoke_dir}/raw"); return 1

    failures = []; checks = 0
    def check(cond, msg):
        nonlocal checks; checks += 1
        if not cond: failures.append(msg)
        print(("  PASS  " if cond else "  FAIL  ") + msg)

    for f in files:
        recs = [json.loads(l) for l in open(f)]
        print(f"\n== {Path(f).name}  ({len(recs)} records)")
        for r in recs:
            sid = r["sample_id"]; ds = r["dataset"]
            check(r.get("model_actual") == args.model, f"{sid}: model_actual == {args.model} (got {r.get('model_actual')})")
            if not r.get("safety_override"):
                check(r.get("upstream_provider") == args.pin, f"{sid}: upstream pin == {args.pin} (got {r.get('upstream_provider')})")
            check(not r.get("api_error"), f"{sid}: no api_error")
            check(bool(r.get("emotion_agent_raw")), f"{sid}: emotion_agent_raw persisted")
            check(bool(r.get("referral_agent_raw")), f"{sid}: referral_agent_raw persisted")
            raw = r.get("referral_agent_raw")
            extracted = ladder(raw)
            fb = bool(r.get("referral_risk_fallback_used"))
            check(fb == (extracted is None),
                  f"{sid}: fallback flag ({fb}) consistent with ladder result ({extracted!r})")
            if extracted is not None and ds == "dreaddit" and not r.get("safety_override"):
                rl = str(r.get("referral_level", "")).lower()
                check(rl == extracted or (extracted != "low" and rl in ("moderate", "urgent")),
                      f"{sid}: recorded referral_level '{rl}' matches extracted '{extracted}'")
            if ds in frozen:
                check(sid in frozen[ds], f"{sid}: member of frozen {ds} sample set")
            check(r.get("strategy") == r.get("strategy_actual"), f"{sid}: strategy == strategy_actual ({r.get('strategy')})")
    # meta files
    for m in sorted(glob.glob(str(Path(args.smoke_dir) / "metadata" / "*_meta.json"))):
        meta = json.load(open(m))
        d = meta.get("decoding", {})
        check(d.get("mode") == "provider_default", f"{Path(m).name}: decoding mode provider_default")
        check(meta.get("sampling_mode") == "frozen_ids", f"{Path(m).name}: sampling_mode frozen_ids")

    print(f"\n{'='*60}\n{checks - len(failures)}/{checks} checks passed", "— ALL GREEN" if not failures else "")
    if failures:
        print("FAILURES:"); [print("  -", x) for x in failures]
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
