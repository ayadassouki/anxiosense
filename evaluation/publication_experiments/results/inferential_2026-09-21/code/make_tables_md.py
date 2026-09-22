#!/usr/bin/env python3
"""Render human-readable Markdown tables and a numeric summary from the CSVs written by run_inferential.py.
No statistics are computed here beyond counting rows; every number is read from tables/*.csv.
Rounding (presentation only): effects, CIs and metric values to 3 decimals, ROUND_HALF_UP on the exact
decimal expansion of the stored float (repr). p-values to 4 decimals (ROUND_HALF_UP); p < 0.0001 shown as '<0.0001'
(the smallest attainable permutation p is 1/10001 = 0.0000999900...)."""
import csv, json, collections
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
OUT = Path(__file__).resolve().parent.parent; T = OUT / "tables"
def rd(n): return list(csv.DictReader(open(T / n)))
def r3(x): return str(Decimal(x).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))
def s3(x):
    v = Decimal(x).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP); return ("+" if v > 0 else "") + str(v) if v != 0 else "0.000"
def pp(x):
    v = Decimal(x)
    if v < Decimal("0.0001"): return "<0.0001"
    return str(v.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
def half_risk(x, q):  # value within 1e-12 of a rounding half-boundary -> flag
    d = Decimal(x) / Decimal(q); frac = d - d.to_integral_value(rounding="ROUND_FLOOR")
    return abs(frac - Decimal("0.5")) < Decimal("1e-9")
SIG = lambda r, k="holm_significant_0.05": "**yes**" if r[k] == "True" else "no"
t1, t1m, t1c, t2, tc = rd("rq1_model_pairs_primary.csv"), rd("rq1_model_pairs_mcnemar.csv"), rd("rq1_model_pairs_conditional_accuracy_ci.csv"), rd("rq2_configuration_vs_baseline.csv"), rd("configuration_level_ci.csv")
mc = {(r["dataset"], r["strategy"], r["model_A"], r["model_B"]): r for r in t1m}
flags = []
md = {}
for ds in ("dreaddit", "goemotions"):
    for metric in ("acc_eff", "macro_f1"):
        lines = ["| Strategy | Model A | Model B | A value | B value | Δ (A−B) | 95% CI | p (perm.) | Holm p | Holm sig. | McNemar b / c | McNemar Holm p |" if metric == "acc_eff" else
                 "| Strategy | Model A | Model B | A value | B value | Δ (A−B) | 95% CI | p (perm.) | Holm p | Holm sig. |",
                 "|" + "---|" * (12 if metric == "acc_eff" else 10)]
        for r in t1:
            if r["dataset"] != ds or r["metric"] != metric: continue
            for k in ("diff_A_minus_B", "ci_low", "ci_high", "A_value", "B_value"):
                if half_risk(r[k], "0.001"): flags.append((ds, metric, k, r[k]))
            row = [r["strategy"], r["model_A"], r["model_B"], r3(r["A_value"]), r3(r["B_value"]), s3(r["diff_A_minus_B"]),
                   f'[{s3(r["ci_low"])}, {s3(r["ci_high"])}]', pp(r["p_perm"]), pp(r["p_holm"]), SIG(r)]
            if metric == "acc_eff":
                m = mc[(ds, r["strategy"], r["model_A"], r["model_B"])]
                row += [f'{m["b_A_correct_B_wrong"]} / {m["c_A_wrong_B_correct"]}', pp(m["p_holm"]) + (" (sig.)" if m["holm_significant_0.05"] == "True" else "")]
            lines.append("| " + " | ".join(row) + " |")
        md[f"rq1_{ds}_{metric}"] = "\n".join(lines)
    lines = ["| Strategy | Model A | Model B | A cond. acc. | B cond. acc. | Δ (A−B) | 95% CI | valid run-outcomes A / B |", "|---|---|---|---|---|---|---|---|"]
    for r in t1c:
        if r["dataset"] == ds:
            lines.append(f'| {r["strategy"]} | {r["model_A"]} | {r["model_B"]} | {r3(r["A_acc_cond"])} | {r3(r["B_acc_cond"])} | {s3(r["diff_A_minus_B"])} | [{s3(r["ci_low"])}, {s3(r["ci_high"])}] | {r["A_valid_run_outcomes"]} / {r["B_valid_run_outcomes"]} |')
    md[f"rq1_{ds}_conditional"] = "\n".join(lines)
    lines = ["| Model | Strategy | Eff. acc. [95% CI] | Baseline (attrib.) | Δ vs baseline [95% CI] | p (perm.) | Holm p | Holm sig. | McNemar b / c | McNemar Holm p | Sensitivity: Δ vs frozen scalar [95% CI] |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in t2:
        if r["dataset"] != ds: continue
        for k in ("diff_vs_baseline", "ci_low", "ci_high", "acc_eff"):
            if half_risk(r[k], "0.001"): flags.append((ds, "rq2", k, r[k]))
        lines.append(f'| {r["model"]} | {r["strategy"]} | {r3(r["acc_eff"])} [{r3(r["acc_eff_ci_low"])}, {r3(r["acc_eff_ci_high"])}] | {r3(r["baseline_attributable"])} | {s3(r["diff_vs_baseline"])} [{s3(r["ci_low"])}, {s3(r["ci_high"])}] | {pp(r["p_perm"])} | {pp(r["p_holm"])} | {SIG(r)} | {r["mc_b_config_correct_base_wrong"]} / {r["mc_c_config_wrong_base_correct"]} | {pp(r["mc_p_holm"])}{" (sig.)" if r["mc_holm_significant_0.05"] == "True" else ""} | {s3(r["sens_diff_vs_frozen_scalar"])} [{s3(r["sens_ci_low"])}, {s3(r["sens_ci_high"])}] |')
    md[f"rq2_{ds}"] = "\n".join(lines)
    lines = ["| Model | Strategy | Eff. acc. [95% CI] | Cond. acc. [95% CI] | Macro-F1 [95% CI] |", "|---|---|---|---|---|"]
    for r in tc:
        if r["dataset"] == ds:
            lines.append(f'| {r["model"]} | {r["strategy"]} | ' + " | ".join(f'{r3(r[k])} [{r3(r[k+"_ci_low"])}, {r3(r[k+"_ci_high"])}]' for k in ("acc_eff", "acc_cond", "macro_f1")) + " |")
    md[f"cfg_{ds}"] = "\n".join(lines)
for k, v in md.items(): (T / f"{k}.md").write_text(v + "\n")

# ---- numeric summary (counts only)
S = {}
for ds in ("dreaddit", "goemotions"):
    S[ds] = {}
    for metric in ("acc_eff", "macro_f1"):
        rows = [r for r in t1 if r["dataset"] == ds and r["metric"] == metric]
        S[ds][f"rq1_{metric}_holm_sig"] = sum(r["holm_significant_0.05"] == "True" for r in rows)
        S[ds][f"rq1_{metric}_n"] = len(rows)
        S[ds][f"rq1_{metric}_raw_p_lt_0.05"] = sum(float(r["p_perm"]) < 0.05 for r in rows)
        S[ds][f"rq1_{metric}_ci_excludes_0"] = sum(float(r["ci_low"]) > 0 or float(r["ci_high"]) < 0 for r in rows)
        S[ds][f"rq1_{metric}_ci_vs_rawp_disagree"] = [f'{r["strategy"]}: {r["model_A"]} vs {r["model_B"]}' for r in rows
                                                      if (float(r["ci_low"]) > 0 or float(r["ci_high"]) < 0) != (float(r["p_perm"]) < 0.05)]
        S[ds][f"rq1_{metric}_borderline_holm_0.02_0.10"] = [f'{r["strategy"]}: {r["model_A"]} vs {r["model_B"]} (Holm p {pp(r["p_holm"])})' for r in rows if 0.02 <= float(r["p_holm"]) <= 0.10]
    rows = [r for r in t1m if r["dataset"] == ds]
    S[ds]["rq1_mcnemar_holm_sig"] = sum(r["holm_significant_0.05"] == "True" for r in rows)
    prim = {(r["strategy"], r["model_A"], r["model_B"]): r["holm_significant_0.05"] for r in t1 if r["dataset"] == ds and r["metric"] == "acc_eff"}
    S[ds]["rq1_acc_primary_vs_mcnemar_disagree"] = [f'{r["strategy"]}: {r["model_A"]} vs {r["model_B"]} (primary {prim[(r["strategy"], r["model_A"], r["model_B"])]}, McNemar {r["holm_significant_0.05"]})'
                                                     for r in rows if prim[(r["strategy"], r["model_A"], r["model_B"])] != r["holm_significant_0.05"]]
    rows = [r for r in t2 if r["dataset"] == ds]
    S[ds]["rq2_holm_sig_above"] = [f'{r["model"]} {r["strategy"]}' for r in rows if r["holm_significant_0.05"] == "True" and float(r["diff_vs_baseline"]) > 0]
    S[ds]["rq2_holm_sig_below"] = [f'{r["model"]} {r["strategy"]}' for r in rows if r["holm_significant_0.05"] == "True" and float(r["diff_vs_baseline"]) < 0]
    S[ds]["rq2_not_sig"] = [f'{r["model"]} {r["strategy"]}' for r in rows if r["holm_significant_0.05"] != "True"]
    S[ds]["rq2_mcnemar_sig"] = [f'{r["model"]} {r["strategy"]}' for r in rows if r["mc_holm_significant_0.05"] == "True"]
    S[ds]["rq2_sensitivity_ci_excludes_0_above"] = sum(float(r["sens_ci_low"]) > 0 for r in rows)
    S[ds]["rq2_sensitivity_ci_excludes_0_below"] = sum(float(r["sens_ci_high"]) < 0 for r in rows)
    S[ds]["rq2_primary_ci_excludes_0_above"] = sum(float(r["ci_low"]) > 0 for r in rows)
    S[ds]["rq2_primary_ci_excludes_0_below"] = sum(float(r["ci_high"]) < 0 for r in rows)
S["rounding_half_boundary_flags"] = flags
json.dump(S, open(OUT / "summary_counts.json", "w"), indent=1)
print(json.dumps(S, indent=1))

# ---- Monte Carlo sensitivity of permutation-based Holm decisions (derived, presentation only)
# The permutation p = (1+k)/(1+P) is a Monte Carlo estimate. For every primary result whose Holm-adjusted p is
# between 0.01 and 0.10 we compute the exact one-sided 99% Clopper-Pearson upper and lower bounds on the true
# exceedance probability from k of P = 10,000, re-run Holm with only that p replaced (all others fixed), and
# report whether the Holm decision at 0.05 could change. This does NOT alter any reported result.
import math
P = 10000
def binom_cdf(k, n, p):
    if p <= 0: return 1.0
    if p >= 1: return 0.0 if k < n else 1.0
    lp, lq = math.log(p), math.log1p(-p)
    return min(1.0, sum(math.exp(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lp + (n - i) * lq) for i in range(k + 1)))
def cp_upper(k, n, a=0.01):
    lo, hi = k / n, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if binom_cdf(k, n, mid) > a: lo = mid
        else: hi = mid
    return hi
def cp_lower(k, n, a=0.01):
    if k == 0: return 0.0
    lo, hi = 0.0, k / n
    for _ in range(80):
        mid = (lo + hi) / 2
        if 1 - binom_cdf(k - 1, n, mid) < a: lo = mid
        else: hi = mid
    return lo
def holm_list(ps):
    m = len(ps); o = sorted(range(m), key=lambda i: ps[i]); adj = [0.0] * m; run = 0.0
    for r_, i in enumerate(o): run = max(run, min(1.0, (m - r_) * ps[i])); adj[i] = run
    return adj
mcs = []
fams = [(ds, "RQ1", [r for r in t1 if r["dataset"] == ds]) for ds in ("dreaddit", "goemotions")] + \
       [(ds, "RQ2", [r for r in t2 if r["dataset"] == ds]) for ds in ("dreaddit", "goemotions")]
for ds, fam, rows in fams:
    ps = [float(r["p_perm"]) for r in rows]
    for i, r in enumerate(rows):
        if not (0.01 <= float(r["p_holm"]) <= 0.10): continue
        k = round(ps[i] * (P + 1)) - 1
        res = {}
        for tag, pr in (("upper99", cp_upper(k, P)), ("lower99", cp_lower(k, P))):
            q = list(ps); q[i] = pr; res[tag] = holm_list(q)[i]
        label = (f'{r["strategy"]}: {r["model_A"]} vs {r["model_B"]} [{r["metric"]}]' if fam == "RQ1" else f'{r["model"]} {r["strategy"]}')
        mcs.append({"dataset": ds, "family": fam, "comparison": label, "exceedances_k": k, "p_perm": ps[i], "holm_p": float(r["p_holm"]),
                    "holm_p_if_true_p_at_upper99": res["upper99"], "holm_p_if_true_p_at_lower99": res["lower99"],
                    "decision_stable_at_0.05": (res["upper99"] <= 0.05) == (res["lower99"] <= 0.05)})
S["monte_carlo_sensitivity"] = mcs
json.dump(S, open(OUT / "summary_counts.json", "w"), indent=1)
for m in mcs: print(m)
