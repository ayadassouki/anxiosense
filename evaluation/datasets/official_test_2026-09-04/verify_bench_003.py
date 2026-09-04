#!/usr/bin/env python3
"""Ten acceptance checks for bench_003 against the official Dreaddit 715 manifest.

Read-only. Verifies the run directory and re-verifies that nothing historical
moved. Usage:

    python3 evaluation/datasets/official_test_2026-09-04/verify_bench_003.py \
        evaluation/publication_experiments/runs/bench_003_official_dreaddit_qwen
"""
from __future__ import annotations
import ast, hashlib, json, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT / "evaluation" / "publication_experiments"))
from runner.manifest import load_manifest, verify_manifest  # noqa: E402

# bench_003 ran under MANIFEST_SCHEMA_VERSION 1.0.0, whose Dreaddit manifest
# self-hash was d764a885f746e8eb...  Schema 1.1.0 added unscorable_samples and
# related keys, which participate in manifest_sha256, so the same 715-row scope
# now hashes a9ea5d554ff1b14a...  The SCOPE is byte-identical: same 715 ids,
# same ground truth, same baseline 0.516084. Both are accepted here.
EXPECT_MANIFEST_SHA_V1_0_0 = "d764a885f746e8eb2798f6a9bfe0302bf9d5c019e47d95a4af749232e10b4e6a"
EXPECT_MANIFEST_SHA = "a9ea5d554ff1b14a8853ef26a2dfccf563e85a6f027d6ad68cb01a7f3ba8e56b"
ACCEPTED_MANIFEST_SHAS = {EXPECT_MANIFEST_SHA, EXPECT_MANIFEST_SHA_V1_0_0}
EXPECT_MANIFEST = "evaluation/publication_experiments/manifests/official_dreaddit_test.json"
EXPECT_MODEL = "qwen/qwen3.5-27b"
EXPECT_PIN = "Alibaba"
EXPECT_STRATEGIES = {"zero-shot", "zero-shot-cot", "one-shot-cot"}
EXPECT_N = 12
RAW_AGENTS = ["emotion_agent_raw", "symptom_agent_raw", "context_agent_raw",
              "referral_agent_raw", "final_report"]
BASELINE = HERE / "_historical_baseline.json"

res: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    res.append((name, bool(ok), detail))


def jl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def main(run_dir: str) -> int:
    rd = Path(run_dir)
    if not rd.is_absolute():
        rd = REPO_ROOT / rd
    if not rd.exists():
        print(f"run directory not found: {rd}")
        return 2

    exp = json.loads((rd / "experiment.json").read_text())
    att = jl(rd / "raw" / "attempts.jsonl")
    idx = jl(rd / "raw" / "index.jsonl")
    parsed = jl(rd / "parsed" / "records.jsonl") if (rd / "parsed" / "records.jsonl").exists() else []
    man = load_manifest(REPO_ROOT / EXPECT_MANIFEST)

    # 1 ── correct manifest
    mp = exp["datasets"]["dreaddit"]["manifest_path"]
    check("1  uses official_dreaddit_test.json", mp == EXPECT_MANIFEST, mp)

    # 2 ── manifest SHA, in the frozen block AND on every attempt
    ms = exp["datasets"]["dreaddit"]["manifest_sha256"]
    att_ms = {a.get("dataset_manifest_sha256") for a in att}
    check("2  manifest_sha256 matches an accepted schema version",
          ms in ACCEPTED_MANIFEST_SHAS and att_ms <= ACCEPTED_MANIFEST_SHAS,
          f"frozen={ms[:16]}… "
          f"({'schema 1.0.0' if ms == EXPECT_MANIFEST_SHA_V1_0_0 else 'schema 1.1.0'})")
    check("2b manifest still verifies on disk",
          not verify_manifest(man), str(verify_manifest(man) or "no problems"))
    check("2c manifest scope unchanged across the schema bump (715/715/0, baseline 0.516084)",
          man["n_dispatchable"] == 715 and man["rows_in_split"] == 715
          and man["n_excluded"] == 0 and man["majority_baseline"] == 0.516084
          and man.get("n_unscorable", 0) == 0,
          f"{man['rows_in_split']}/{man['n_dispatchable']}/{man['n_excluded']} "
          f"baseline={man['majority_baseline']}")

    # 3 ── model + provider pinning
    req = {a.get("model_requested") for a in att}
    act = {a.get("model_actual") for a in att}
    mism = [a["sample_id"] for a in att if a.get("model_mismatch")]
    pin = {a.get("pin_provider") for a in att}
    prov_req = {a.get("provider_requested") for a in att}
    prov_act = {a.get("provider_actual") for a in att}
    ups = Counter(a.get("upstream_provider") for a in att)
    ups_all = {tuple(a.get("upstream_providers_all") or []) for a in att}
    check("3  model requested == actual, no mismatch flags",
          req == {EXPECT_MODEL} and mism == [],
          f"requested={req} actual={act} mismatches={len(mism)}")
    check("3b provider pin honoured", pin == {EXPECT_PIN},
          f"pin={pin} provider_requested={prov_req} provider_actual={prov_act}")
    check("3c upstream provider is only the pinned one",
          set(ups) <= {EXPECT_PIN} or all(EXPECT_PIN in str(u) for u in ups if u),
          f"upstream={dict(ups)} all_seen={ups_all}")

    # 4 ── prompt strategy
    st_req = Counter(a.get("strategy") for a in att)
    st_act = {a.get("strategy_actual") for a in att}
    drift = [a["sample_id"] for a in att
             if a.get("strategy_actual") and a["strategy_actual"] != a["strategy"]]
    psh = {a.get("prompt_set_sha256") for a in att}
    check("4  all 3 strategies present, requested == actual",
          set(st_req) == EXPECT_STRATEGIES and not drift,
          f"{dict(st_req)} actual={st_act} drift={len(drift)}")
    check("4b prompt_set_sha256 constant and matches the frozen block",
          len(psh) == 1 and psh == {exp["prompt_inventory"]["prompt_set_sha256"]},
          f"{[s[:16] + '…' for s in psh if s]}")
    check("4c per-attempt prompt_sha256 present",
          all(a.get("prompt_sha256") for a in att),
          f"{sum(1 for a in att if a.get('prompt_sha256'))}/{len(att)}")

    # 5 ── ground truth read from the manifest, never recomputed
    gt = man["ground_truth"]
    bad = [(a["sample_id"], a.get("ground_truth"), gt.get(a["sample_id"]))
           for a in att if a.get("ground_truth") != gt.get(a["sample_id"])]
    oos = [a["sample_id"] for a in att if a["sample_id"] not in gt]
    tsh = [a["sample_id"] for a in att
           if man["text_sha256"].get(a["sample_id"]) != a.get("text_sha256")]
    check("5  ground truth on every attempt equals the manifest",
          not bad and not oos, f"mismatches={len(bad)} out-of-scope={len(oos)} {bad[:2]}")
    check("5b dispatched text hash equals the manifest's",
          not tsh, f"{len(tsh)} mismatch(es) {tsh[:3]}")
    check("5c input_text is the redacted/processed field",
          all(a.get("text_column") == "text_processed" for a in att),
          str({a.get("text_column") for a in att}))

    # 6 ── raw responses preserved
    ok_att = [a for a in att if a.get("outcome_class") == "OK"]
    missing = Counter()
    for a in ok_att:
        raw = a.get("raw") or {}
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                raw = ast.literal_eval(raw)
        for f in RAW_AGENTS:
            if not raw.get(f):
                missing[f] += 1
    check("6  all 5 agent raws preserved on every OK attempt",
          not missing, f"missing={dict(missing)} over {len(ok_att)} OK attempts")
    check("6b response_body + its sha256 stored on every attempt",
          all(a.get("response_body") and a.get("response_body_sha256") for a in att),
          f"{sum(1 for a in att if a.get('response_body_sha256'))}/{len(att)}")
    # run.py:192 hashes result.raw_body_text (the exact HTTP bytes), while
    # response_body stores the PARSED object. The raw text is not persisted, so
    # this hash is a tamper anchor, not something re-derivable from the run dir.
    # Check only that it is present and well-formed.
    bad_sha = [a["sample_id"] for a in att
               if not (isinstance(a.get("response_body_sha256"), str)
                       and len(a["response_body_sha256"]) == 64)]
    check("6c response_body_sha256 present and well-formed (64 hex)",
          not bad_sha,
          f"{len(att) - len(bad_sha)}/{len(att)}; note: pins raw HTTP text, which is "
          f"not itself persisted - anchor only, not re-derivable")

    # 7 ── malformed becomes invalid, never a fallback label
    if parsed:
        inval = [p for p in parsed if not p.get("prediction_valid")]
        scored_invalid = [p for p in inval if p.get("include_in_metrics")]
        preds = Counter(p.get("parsed_prediction") for p in parsed)
        fallback = [p for p in inval if p.get("parsed_prediction") not in (None, "", "unparseable")]
        check("7  invalid predictions are never scored",
              not scored_invalid, f"invalid={len(inval)} scored_anyway={len(scored_invalid)}")
        check("7b no fallback label assigned to an invalid prediction",
              not fallback, f"{len(fallback)} {[(p['sample_id'], p.get('parsed_prediction')) for p in fallback][:3]}")
        check("7c parse_status recorded on every record",
              all(p.get("parse_status") for p in parsed),
              str(dict(Counter(p.get("parse_status") for p in parsed))))
        check("7d predictions come from raw, cross_check present",
              all("cross_check" in p for p in parsed),
              str(dict(Counter(str(p.get("cross_check")) for p in parsed))))
        print(f"     prediction distribution: {dict(preds)}")
    else:
        check("7  parsed/records.jsonl present", False, "missing")

    # 8 ── retry / resume
    rq = [a for a in att if a.get("retryable")]
    multi = [r for r in idx if int(r.get("attempt_count", 1)) > 1]
    outcomes = Counter(r.get("final_outcome_class") for r in idx)
    check("8  one terminal record per assessment, no duplicates",
          len(idx) == len({r["assessment_uuid"] for r in idx})
          and len({r["sample_id"] + r["cell_id"] for r in idx}) == len(idx),
          f"{len(idx)} terminal records")
    check("8b every terminal_attempt_uuid exists in attempts.jsonl",
          {r["terminal_attempt_uuid"] for r in idx} <= {a["attempt_uuid"] for a in att},
          "")
    check("8c retry_history present on every assessment",
          all("retry_history" in r for r in idx),
          f"retried={len(multi)} retryable_attempts={len(rq)} outcomes={dict(outcomes)}")

    # 9 ── provenance
    need = ["experiment_id", "runner_version", "record_schema_version", "config_sha256",
            "git_commit", "git_dirty", "git_untracked_count", "models_enabled",
            "models_disabled", "prompt_inventory", "datasets", "grid", "retry_policy", "server"]
    miss = [k for k in need if k not in exp]
    per_att = ["git_commit", "config_sha256", "prompt_set_sha256", "dataset_manifest_sha256",
               "dataset_source_sha256", "runner_version", "schema_version", "timestamp_utc",
               "official_split", "run", "cell_id", "assessment_uuid", "attempt_uuid"]
    att_miss = {k for k in per_att for a in att if not a.get(k)}
    check("9  frozen provenance block complete", not miss, f"missing={miss}")
    check("9b per-attempt provenance complete", not att_miss, f"missing={sorted(att_miss)}")
    check("9c experiment.json commit == manifest-build commit lineage",
          exp["git_commit"] == att[0]["git_commit"], exp["git_commit"][:12])
    check("9d git_dirty false at run time", exp.get("git_dirty") is False,
          f"git_dirty={exp.get('git_dirty')} untracked={exp.get('git_untracked_count')}")

    # 10 ── historical outputs untouched
    if BASELINE.exists():
        base = json.loads(BASELINE.read_text())
        drifted = []
        for k, v in base.items():
            if v is None or k.startswith("_"):   # "_note" etc. are metadata, not paths
                continue
            p = REPO_ROOT / k
            if "listing_sha256" in v:
                entries = []
                for f in sorted(p.rglob("*")):
                    if f.is_file():
                        st = f.stat()
                        entries.append(f"{f.relative_to(REPO_ROOT)}|{st.st_size}|{int(st.st_mtime)}")
                now = hashlib.sha256("\n".join(entries).encode()).hexdigest()
                if now != v["listing_sha256"]:
                    drifted.append(f"{k} (was {v['files']} files, now {len(entries)})")
            else:
                now = hashlib.sha256(p.read_bytes()).hexdigest()
                if now != v["sha256"]:
                    drifted.append(f"{k} content changed")
        check("10 historical outputs, old runs and manifests unchanged",
              not drifted, "; ".join(drifted) or "all match the pre-run baseline")
    else:
        check("10 baseline snapshot present", False, "_historical_baseline.json missing")

    # bonus: scope sanity
    check("A  assessment count == 12 (3 strategies x 4)",
          len(idx) == EXPECT_N, f"{len(idx)} terminal, {len(att)} attempts")
    check("B  all sample_ids are dread_<official id>",
          all(r["sample_id"].startswith("dread_") and r["sample_id"][6:].isdigit()
              and not (r["sample_id"][6:].startswith("0") and len(r["sample_id"][6:]) > 1)
              for r in idx),
          str(sorted({r["sample_id"] for r in idx})[:4]))

    width = max(len(n) for n, _, _ in res)
    print("\n" + "=" * 78)
    for n, ok, d in res:
        print(f"{'PASS' if ok else 'FAIL'}  {n:<{width}}  {d}")
    failed = [n for n, ok, _ in res if not ok]
    print("=" * 78)
    print(f"{len(res) - len(failed)}/{len(res)} checks passed"
          + (f"\nFAILURES: {failed}" if failed else "\nbench_003 PASSES"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1
                          else "evaluation/publication_experiments/runs/bench_003_official_dreaddit_qwen"))
