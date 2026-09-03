#!/usr/bin/env python3
"""Post-run verification report for a smoke/benchmark run.

    python3 evaluation/publication_experiments/smoke_report.py <run_dir>

Read-only. Reports exactly what a reviewer needs to trust the run before scaling.
"""
from __future__ import annotations
import json, statistics as st, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from runner.rescore import rescore                     # noqa: E402
from runner.metrics import cell_metrics, MetricPolicy  # noqa: E402
from runner.manifest import load_manifest              # noqa: E402
from runner._reuse import REPO_ROOT                    # noqa: E402

RAW_FIELDS = ["emotion_agent_raw", "symptom_agent_raw", "context_agent_raw",
              "referral_agent_raw", "final_report"]


def human(n: float) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024: return f"{n:,.1f} {u}"
        n /= 1024
    return f"{n:,.1f} TB"


def main(run_dir: str) -> int:
    rd = Path(run_dir)
    if not rd.exists():
        print(f"run directory not found: {rd}"); return 1
    exp = json.loads((rd / "experiment.json").read_text())
    attempts = [json.loads(l) for l in (rd / "raw" / "attempts.jsonl").read_text().splitlines() if l.strip()]
    index = [json.loads(l) for l in (rd / "raw" / "index.jsonl").read_text().splitlines() if l.strip()]

    print("=" * 78)
    print(f"RUN DIRECTORY   {rd}")
    print("=" * 78)

    print("\n-- FILES CREATED " + "-" * 60)
    total = 0
    for p in sorted(rd.rglob("*")):
        if p.is_file():
            sz = p.stat().st_size; total += sz
            print(f"   {str(p.relative_to(rd)):46s} {human(sz):>12s}")
    print(f"   {'TOTAL':46s} {human(total):>12s}")

    print("\n-- PROVENANCE " + "-" * 63)
    print(f"   experiment_id   {exp['experiment_id']}")
    print(f"   git_commit      {exp['git_commit'][:12]} {'(dirty tree)' if exp['git_dirty'] else '(clean)'}")
    print(f"   config_sha256   {exp['config_sha256'][:16]}")
    print(f"   prompt_set      {exp['prompt_inventory']['prompt_set_sha256'][:16]}")
    for n, ds in exp["datasets"].items():
        print(f"   dataset {n:11s} manifest={ds['manifest_sha256'][:12]} "
              f"n={ds['n_dispatchable']} baseline={ds['majority_baseline']}")

    print("\n-- VOLUME " + "-" * 67)
    print(f"   assessments (terminal records)   {len(index)}")
    print(f"   API/model calls (attempts)       {len(attempts)}")
    print(f"   retries beyond first attempt     {len(attempts) - len(index)}")
    raw_size = (rd / 'raw' / 'attempts.jsonl').stat().st_size
    print(f"   raw/attempts.jsonl               {human(raw_size)}")
    if index:
        print(f"   raw bytes per assessment         {human(raw_size / len(index))}")

    print("\n-- RAW AGENT OUTPUTS POPULATED " + "-" * 46)
    ok = [a for a in attempts if a["outcome_class"] == "OK"]
    for f in RAW_FIELDS:
        n = sum(1 for a in ok if a["raw"].get(f))
        lens = [len(a["raw"][f]) for a in ok if a["raw"].get(f)]
        med = f"{st.median(lens):,.0f} chars" if lens else "-"
        flag = "OK " if (ok and n == len(ok)) else "!! "
        print(f"   {flag}{f:22s} {n}/{len(ok)} populated   median {med}")
    print(f"   mastra_run_id present            {sum(1 for a in ok if a.get('mastra_run_id'))}/{len(ok)}")

    print("\n-- MODEL / PROVIDER: REQUESTED vs ACTUAL " + "-" * 36)
    pairs = Counter((a["model_requested"], a.get("model_actual"),
                     a.get("provider_actual"), a.get("upstream_provider")) for a in attempts)
    for (req, act, prov, up), n in pairs.items():
        if act is None:
            match = "no response (transport failure)"
        else:
            match = "MATCH" if str(act).endswith(req) else "MISMATCH"
        print(f"   requested={req}  actual={act}  provider={prov}  upstream={up}  n={n}  [{match}]")
    print(f"   model_mismatch flagged           {sum(1 for a in attempts if a.get('model_mismatch'))}")
    print(f"   strategy requested/actual        "
          f"{Counter((a['strategy'], a.get('strategy_actual')) for a in attempts).most_common()}")

    print("\n-- OUTCOMES " + "-" * 65)
    print(f"   transport outcomes (per attempt) {dict(Counter(a['outcome_class'] for a in attempts))}")
    print(f"   final outcomes (per assessment)  {dict(Counter(i['final_outcome_class'] for i in index))}")
    multi = [i for i in index if i["attempt_count"] > 1]
    print(f"   assessments needing a retry      {len(multi)}")
    for i in multi[:5]:
        print(f"      {i['sample_id']}: " +
              " -> ".join(f"{h['outcome']}({h.get('http_status')})" for h in i["retry_history"]))

    print("\n-- PREDICTIONS (re-derived from raw, no model call) " + "-" * 25)
    print("   rescore:", json.dumps(rescore(rd)["parse_status_counts"]))
    recs = [json.loads(l) for l in (rd / "parsed" / "records.jsonl").read_text().splitlines() if l.strip()]
    ds_name = exp["grid"]["datasets"][0]
    man = load_manifest(REPO_ROOT / exp["datasets"][ds_name]["manifest_path"])
    labels = [0, 1] if ds_name == "dreaddit" else ["anxiety", "fear", "sadness", "frustration", "non_distress"]
    m = cell_metrics(recs, labels=labels, majority_baseline=man["majority_baseline"],
                     policy=MetricPolicy())
    for k, v in m["buckets"].items():
        print(f"   {k:34s} {v}")
    dis = [r for r in recs if r.get("cross_check", {}).get("agrees_with_server") is False]
    print(f"   {'derived vs server disagreement':34s} {len(dis)}")

    print("\n-- TIMING AND COST " + "-" * 58)
    lat = sorted(a["latency_ms"] for a in attempts if a.get("latency_ms"))
    if lat:
        print(f"   client latency  mean {st.mean(lat):,.0f} ms   median {st.median(lat):,.0f} ms   "
              f"p95 {lat[min(int(.95*len(lat)), len(lat)-1)]:,.0f} ms   max {lat[-1]:,.0f} ms")
    srv = [a["server_latency_ms"] for a in attempts if a.get("server_latency_ms")]
    if srv:
        print(f"   server latency  median {st.median(srv):,.0f} ms")
    tin = [a["token_usage"]["input_tokens"] for a in attempts
           if isinstance(a.get("token_usage"), dict) and a["token_usage"].get("input_tokens")]
    tout = [a["token_usage"]["output_tokens"] for a in attempts
            if isinstance(a.get("token_usage"), dict) and a["token_usage"].get("output_tokens")]
    if tin:
        print(f"   tokens/assessment  in {st.mean(tin):,.0f}  out {st.mean(tout):,.0f}   "
              f"TOTAL in {sum(tin):,}  out {sum(tout):,}")

    print("\n-- PROJECTION FOR ONE FULL CELL " + "-" * 45)
    if lat and index:
        per = st.mean(lat) / 1000 + float(exp["server"]["request_delay_seconds"])
        n_cell = exp["datasets"][ds_name]["n_dispatchable"]
        secs = per * n_cell
        print(f"   measured seconds per assessment  {per:,.1f} s  (mean latency + configured delay)")
        print(f"   items in one cell ({ds_name})     {n_cell}")
        print(f"   ONE CELL, sequential             {secs/60:,.1f} min  ({secs/3600:,.2f} h)")
        if tin:
            print(f"   tokens for one cell (est.)       in {st.mean(tin)*n_cell:,.0f}  out {st.mean(tout)*n_cell:,.0f}")
        print(f"   NOTE: single-cell projection only. Do NOT extrapolate to the full grid")
        print(f"         until a larger benchmark measures retry rate and provider variance.")
    print()
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__); raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
