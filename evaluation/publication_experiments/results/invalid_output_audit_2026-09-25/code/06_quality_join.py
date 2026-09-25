"""Stage 6 - analysis-ready join of invalid-output behaviour to the frozen quality metrics.

Association only. This file exists so the quality/performance question can be tested LATER;
it asserts no relationship and performs no significance test.
"""
import json, os, csv, collections

REPO = os.environ["REPO"]; OUT = os.environ["OUT"]
TAB = f"{REPO}/evaluation/publication_experiments/results/rq1_rq3_tables"
rows = [json.loads(l) for l in open(f"{OUT}/invalid_outputs_row_level.jsonl", encoding="utf-8")]

inv = collections.Counter((r["dataset"], r["model_short"], r["strategy"]) for r in rows)
uniq = collections.defaultdict(set)
cat = collections.defaultdict(collections.Counter)
for r in rows:
    k = (r["dataset"], r["model_short"], r["strategy"])
    uniq[k].add(r["sample_id"]); cat[k][r["primary_failure_category"]] += 1

lat = {}
for r in csv.DictReader(open(f"{TAB}/04_latency_results.csv", encoding="utf-8")):
    lat[(r["dataset"], r["model"], r["strategy"])] = r["client_latency_mean_s"]

ATT = {"dreaddit": 3495, "goemotions": 3110}
out = []
for ds, f in [("dreaddit", "02_dreaddit_results.csv"), ("goemotions", "03_goemotions_results.csv")]:
    for r in csv.DictReader(open(f"{TAB}/{f}", encoding="utf-8")):
        k = (ds, r["model"], r["prompt_strategy"])
        n = inv.get(k, 0)
        top = cat[k].most_common(1)
        out.append({
            "dataset": ds, "model": r["model"], "strategy": r["prompt_strategy"],
            "invalid_records_5runs": n,
            "invalid_rate": round(n / ATT[ds], 6),
            "unique_samples_affected": len(uniq[k]),
            "records_per_affected_sample": round(n / len(uniq[k]), 3) if uniq[k] else 0,
            "dominant_failure_category": top[0][0] if top else "",
            "dominant_category_share": round(top[0][1] / n, 3) if n else "",
            "evaluability_mean": r["evaluability_mean"],
            "accuracy_conditional_mean": r["conditional_accuracy_mean"],
            "accuracy_effective_mean": r["effective_accuracy_mean"],
            "accuracy_gap_cond_minus_eff": round(float(r["conditional_accuracy_mean"]) - float(r["effective_accuracy_mean"]), 6),
            "macro_f1_mean": r["macro_f1_mean"],
            "macro_f1_sd": r["macro_f1_sd"],
            "client_latency_mean_s": lat.get(k, ""),
            "majority_baseline": 0.516084 if ds == "dreaddit" else 0.781701,
        })
cols = list(out[0].keys())
with open(f"{OUT}/cell_level_invalid_vs_quality.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
    for r in out: w.writerow(r)
print("rows:", len(out))
for r in sorted(out, key=lambda x: -x["invalid_rate"])[:8]:
    print("  %-11s %-16s %-14s inv=%-4d rate=%.4f uniq=%-4d eval=%.4f cond=%.4f eff=%.4f gap=%.4f"
          % (r["dataset"], r["model"], r["strategy"], r["invalid_records_5runs"], r["invalid_rate"],
             r["unique_samples_affected"], float(r["evaluability_mean"]),
             float(r["accuracy_conditional_mean"]), float(r["accuracy_effective_mean"]),
             r["accuracy_gap_cond_minus_eff"]))
