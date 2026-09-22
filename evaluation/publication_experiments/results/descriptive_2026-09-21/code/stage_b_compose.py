"""Stage B: compose the authoritative 150-cell grid from Stage A parsed files,
validate it, freeze a manifest, and (only if validation passes) compute metrics with
the repository's own cell_metrics / aggregate_cells. Writes only to the results dir."""
import json, os, sys, csv, hashlib, collections, datetime
A = os.path.expanduser("~/mnt/anxiosense")
sys.path.insert(0, os.path.join(A, "evaluation/publication_experiments"))
from runner.metrics import cell_metrics, aggregate_cells, MetricPolicy, METRIC_POLICY_VERSION
from runner.parse import PARSER_VERSION
OUT = os.path.join(A, "evaluation/publication_experiments/results/descriptive_2026-09-21")
MAN = os.path.join(A, "evaluation/publication_experiments/manifests")

GEMMA_REPLACED_CELL = "dreaddit|google/gemma-4-31b-it|one-shot-cot|run5"
COMPOSITION = {
 ("dreaddit",   "qwen/qwen3.5-27b"):             [("pub_001_dreaddit_qwen", None)],
 ("dreaddit",   "mistralai/mistral-small-2603"): [("pub_002_dreaddit_mistral", None)],
 ("dreaddit",   "meta-llama/llama-4-scout"):     [("pub_003_dreaddit_llama", None)],
 ("dreaddit",   "microsoft/phi-4"):              [("pub_005_dreaddit_phi", None)],
 ("dreaddit",   "google/gemma-4-31b-it"):        [("pub_011_dreaddit_gemma_coreweave", {"exclude_cells": [GEMMA_REPLACED_CELL]}),
                                                  ("pub_013_dreaddit_gemma_coreweave_osc_run5", {"include_cells": [GEMMA_REPLACED_CELL]})],
 ("goemotions", "qwen/qwen3.5-27b"):             [("pub_007_goemotions715_qwen", None)],
 ("goemotions", "mistralai/mistral-small-2603"): [("pub_006_goemotions715_mistral", None)],
 ("goemotions", "meta-llama/llama-4-scout"):     [("pub_009_goemotions715_llama", None)],
 ("goemotions", "microsoft/phi-4"):              [("pub_008_goemotions715_phi", None)],
 ("goemotions", "google/gemma-4-31b-it"):        [("pub_012_goemotions715_gemma_coreweave", None)],
}
EXPECTED_PIN = {"qwen/qwen3.5-27b": "Alibaba", "mistralai/mistral-small-2603": "Mistral",
                "meta-llama/llama-4-scout": "DeepInfra", "microsoft/phi-4": "DeepInfra",
                "google/gemma-4-31b-it": "CoreWeave"}
MANIFESTS = {"dreaddit": "official_dreaddit_test.json", "goemotions": "goemotions_715_subset_2026-09-09.json"}
LABELS = {"dreaddit": [0, 1], "goemotions": ["anxiety", "fear", "sadness", "frustration", "non_distress"]}
STRATS = ["zero-shot", "zero-shot-cot", "one-shot-cot"]; RUNS = [1, 2, 3, 4, 5]

def fsha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

man = {d: json.load(open(os.path.join(MAN, f))) for d, f in MANIFESTS.items()}
problems = []
def fail(msg):
    problems.append(msg)

# ---- compose ----
cells = collections.defaultdict(list); cell_source = {}
source_summ = {}
for (ds, model), sources in COMPOSITION.items():
    for run_name, rule in sources:
        source_summ[run_name] = json.load(open(os.path.join(OUT, "source_parse_summaries", run_name + ".json")))
        for line in open(os.path.join(OUT, "parsed", run_name + ".jsonl"), encoding="utf-8"):
            r = json.loads(line)
            if r["dataset"] != ds or r["model"] != model:
                fail("record from %s has unexpected dataset/model %s|%s" % (run_name, r["dataset"], r["model"])); continue
            if rule and "exclude_cells" in rule and r["cell_id"] in rule["exclude_cells"]: continue
            if rule and "include_cells" in rule and r["cell_id"] not in rule["include_cells"]: continue
            cells[r["cell_id"]].append(r)
            prev = cell_source.setdefault(r["cell_id"], run_name)
            if prev != run_name: fail("cell %s drawn from two sources: %s and %s" % (r["cell_id"], prev, run_name))

# ---- validate ----
expected_cells = ["%s|%s|%s|run%d" % (ds, m, s, n) for (ds, m) in COMPOSITION for s in STRATS for n in RUNS]
if sorted(cells) != sorted(expected_cells):
    fail("cell set mismatch: missing=%s extra=%s" % (sorted(set(expected_cells) - set(cells))[:5], sorted(set(cells) - set(expected_cells))[:5]))
seen = set(); per_cell_val = {}
for cid in expected_cells:
    recs = cells.get(cid, []); ds, model, strat, runl = cid.split("|")
    M = man[ds]; ids = set(M["included_sample_ids"]); exp_n = len(ids)
    sids = [r["sample_id"] for r in recs]
    if len(recs) != exp_n: fail("%s: %d records, expected %d" % (cid, len(recs), exp_n))
    if len(set(sids)) != len(sids): fail("%s: duplicate sample ids" % cid)
    if set(sids) != ids: fail("%s: sample set != manifest (missing %d, extra %d)" % (cid, len(ids - set(sids)), len(set(sids) - ids)))
    for r in recs:
        key = (r["dataset"], r["model"], r["strategy"], r["run"], r["sample_id"])
        if key in seen: fail("duplicate authoritative key %s" % (key,))
        seen.add(key)
        if r["final_outcome_class"] not in ("OK", "SAFETY_INTERCEPT"):
            fail("%s %s final_outcome_class=%s" % (cid, r["sample_id"], r["final_outcome_class"]))
        if r["ground_truth"] != M["ground_truth"].get(r["sample_id"]): fail("%s %s ground truth != manifest" % (cid, r["sample_id"]))
        if r["text_sha256"] != M["text_sha256"].get(r["sample_id"]): fail("%s %s text_sha256 != manifest" % (cid, r["sample_id"]))
        if r["dataset_manifest_sha256"] != M["manifest_sha256"]: fail("%s manifest sha mismatch" % cid)
        if r.get("model_mismatch"): fail("%s %s model_mismatch" % (cid, r["sample_id"]))
        if r.get("provider_mismatch"): fail("%s %s provider_mismatch" % (cid, r["sample_id"]))
        if r["final_outcome_class"] == "OK":
            if r["model_actual"] != "openrouter/" + model: fail("%s %s model_actual=%s" % (cid, r["sample_id"], r["model_actual"]))
            if r["upstream_provider"] != EXPECTED_PIN[model] or r["upstream_providers_all"] != [EXPECTED_PIN[model]]:
                fail("%s %s provider=%s all=%s" % (cid, r["sample_id"], r["upstream_provider"], r["upstream_providers_all"]))
        else:
            if r["parse_status"] != "safety_intercept" or r["upstream_providers_all"] not in ([], None):
                fail("%s %s safety record not clean" % (cid, r["sample_id"]))
    per_cell_val[cid] = {
        "source_run": cell_source.get(cid), "n": len(recs), "expected_n": exp_n,
        "final_outcomes": dict(collections.Counter(r["final_outcome_class"] for r in recs)),
        "parse_status": dict(collections.Counter(r["parse_status"] for r in recs)),
        "safety_ids": sorted(r["sample_id"] for r in recs if r["final_outcome_class"] == "SAFETY_INTERCEPT"),
        "providers_ok": dict(collections.Counter(r["upstream_provider"] for r in recs if r["final_outcome_class"] == "OK")),
        "records_sha256": hashlib.sha256("\n".join(sorted("%s|%s" % (r["sample_id"], r["terminal_attempt_uuid"]) for r in recs)).encode()).hexdigest(),
    }

# safety-set consistency within dataset (report, not a failure)
safety_sets = collections.defaultdict(set)
for cid, v in per_cell_val.items(): safety_sets[cid.split("|")[0]].add(tuple(v["safety_ids"]))

now = datetime.datetime.now(datetime.timezone.utc).isoformat()
frozen = {
  "frozen_utc": now, "purpose": "Authoritative 150-cell publication grid (descriptive scoring input)",
  "parser_version": PARSER_VERSION, "metric_policy_version": METRIC_POLICY_VERSION,
  "composition_rule": {"%s|%s" % k: [{"source_run": s, "rule": r} for s, r in v] for k, v in COMPOSITION.items()},
  "gemma_dreaddit_note": "pub_011 supplies 14 cells; its cell %s is EXCLUDED and replaced by all 715 records of pub_013. pub_011 raw data untouched." % GEMMA_REPLACED_CELL,
  "manifests": {d: {"file": MANIFESTS[d], "manifest_sha256": man[d]["manifest_sha256"],
                    "file_sha256": fsha(os.path.join(MAN, MANIFESTS[d])), "n_scorable": man[d]["n_scorable"],
                    "majority_baseline": man[d]["majority_baseline"]} for d in man},
  "sources": source_summ,
  "cells": per_cell_val,
  "totals": {"cells": len(cells), "records": sum(len(v) for v in cells.values())},
  "safety_intercept_policy": "SAFETY_INTERCEPT terminal records are kept in the grid, reported per cell, and excluded from model attribution by MetricPolicy.exclude_safety_intercept_from_model_attribution=True.",
  "safety_set_identical_across_cells": {d: len(s) == 1 for d, s in safety_sets.items()},
  "validation": {"passed": not problems, "n_problems": len(problems), "problems": problems[:200]},
}
json.dump(frozen, open(os.path.join(OUT, "frozen_grid_manifest.json"), "w"), indent=2, sort_keys=True)
print("cells:", len(cells), "| records:", frozen["totals"]["records"])
print("validation passed:", not problems, "| problems:", len(problems))
for p in problems[:25]: print("  PROBLEM:", p)
print("safety set identical across cells:", frozen["safety_set_identical_across_cells"])
if problems:
    print("STOPPING before scoring."); sys.exit(2)

# ---- score (repo definitions only) ----
cm = {}
with open(os.path.join(OUT, "authoritative_records.jsonl"), "w") as f:
    for cid in expected_cells:
        for r in sorted(cells[cid], key=lambda x: x["sample_id"]):
            f.write(json.dumps({k: r[k] for k in ("source_run","cell_id","dataset","model","strategy","run","sample_id",
                "terminal_attempt_uuid","final_outcome_class","ground_truth","parse_status","parsed_prediction",
                "prediction_valid","failure_class","failure_reason","include_in_metrics","upstream_provider")}, sort_keys=True) + "\n")
for cid in expected_cells:
    ds = cid.split("|")[0]
    cm[cid] = cell_metrics(cells[cid], labels=LABELS[ds], majority_baseline=man[ds]["majority_baseline"], policy=MetricPolicy())
    cm[cid]["parse_status_counts"] = per_cell_val[cid]["parse_status"]
    cm[cid]["source_run"] = per_cell_val[cid]["source_run"]
with open(os.path.join(OUT, "cell_metrics.json"), "w") as f: json.dump(cm, f, indent=1, sort_keys=True)
agg = aggregate_cells(cm)
with open(os.path.join(OUT, "aggregate_five_runs.json"), "w") as f: json.dump(agg, f, indent=1, sort_keys=True)

cols = ["dataset","model","strategy","run","source_run","N_total","N_safety_intercept","N_attributable",
        "N_valid","N_model_invalid","N_infra_failed","N_unaccounted","correct","incorrect",
        "accuracy_conditional","accuracy_effective","macro_precision","macro_recall","macro_f1",
        "evaluability","majority_baseline","parse_status_counts"]
rows = []
for cid in expected_cells:
    ds, model, strat, runl = cid.split("|"); m = cm[cid]; b = m["buckets"]; mm = m["metrics"] or {}
    conf = mm.get("confusion_matrix", {}); corr = sum(conf.get(str(c), {}).get(str(c), 0) for c in LABELS[ds])
    rows.append({"dataset": ds, "model": model, "strategy": strat, "run": int(runl[3:]), "source_run": m["source_run"],
        "N_total": b["N_total"], "N_safety_intercept": b["N_safety_intercept"], "N_attributable": b["N_attributable"],
        "N_valid": b["N_successful_valid_predictions"], "N_model_invalid": b["N_model_behavior_invalid"],
        "N_infra_failed": b["N_infrastructure_failed"], "N_unaccounted": b["N_unaccounted"],
        "correct": corr, "incorrect": b["N_successful_valid_predictions"] - corr,
        "accuracy_conditional": mm.get("accuracy_conditional"), "accuracy_effective": mm.get("accuracy_effective"),
        "macro_precision": mm.get("macro_precision"), "macro_recall": mm.get("macro_recall"), "macro_f1": mm.get("macro_f1"),
        "evaluability": m["rates"]["evaluability"], "majority_baseline": m["majority_baseline"],
        "parse_status_counts": json.dumps(m["parse_status_counts"], sort_keys=True)})
with open(os.path.join(OUT, "per_run_results.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)

acols = ["dataset","model","strategy","n_runs","accuracy_conditional_mean","accuracy_conditional_sd",
         "accuracy_effective_mean","accuracy_effective_sd","macro_f1_mean","macro_f1_sd",
         "evaluability_mean","evaluability_sd","sum_N_total","sum_N_safety","sum_N_valid","sum_N_model_invalid","sum_correct"]
arows = []
for key, a in agg.items():
    ds, model, strat = key.split("|"); sub = [r for r in rows if (r["dataset"], r["model"], r["strategy"]) == (ds, model, strat)]
    g = lambda k, s: (a.get(k) or {}).get(s)
    arows.append({"dataset": ds, "model": model, "strategy": strat, "n_runs": a["n_runs"],
        "accuracy_conditional_mean": g("accuracy_conditional","mean"), "accuracy_conditional_sd": g("accuracy_conditional","sd"),
        "accuracy_effective_mean": g("accuracy_effective","mean"), "accuracy_effective_sd": g("accuracy_effective","sd"),
        "macro_f1_mean": g("macro_f1","mean"), "macro_f1_sd": g("macro_f1","sd"),
        "evaluability_mean": g("evaluability","mean"), "evaluability_sd": g("evaluability","sd"),
        "sum_N_total": sum(r["N_total"] for r in sub), "sum_N_safety": sum(r["N_safety_intercept"] for r in sub),
        "sum_N_valid": sum(r["N_valid"] for r in sub), "sum_N_model_invalid": sum(r["N_model_invalid"] for r in sub),
        "sum_correct": sum(r["correct"] for r in sub)})
arows.sort(key=lambda r: (r["dataset"], r["model"], STRATS.index(r["strategy"])))
with open(os.path.join(OUT, "aggregate_results.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=acols); w.writeheader(); w.writerows(arows)
print("SCORED: per_run_results.csv (%d rows), aggregate_results.csv (%d rows)" % (len(rows), len(arows)))
unacc = [r for r in rows if r["N_unaccounted"] != 0]
print("cells with N_unaccounted != 0:", len(unacc))
