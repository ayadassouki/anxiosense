#!/usr/bin/env python3
"""
INDEPENDENT verification of the inferential analysis (code/run_inferential.py).
Standard library only (no numpy); imports nothing from code/ or runner/. Written separately, using
different formulations where possible:
  * pairs/items rebuilt from authoritative_records.jsonl with dictionaries, not arrays;
  * effective accuracy as exact Fractions; macro-F1 via the frozen form 2PR/(P+R) (primary used 2tp/(2tp+fp+fn));
  * exact McNemar via an explicit binomial pmf sum in Fractions;
  * Holm via an explicit step-down loop written independently;
  * bootstrap draws regenerated from the documented seed strings; ALL 4,000 effective-accuracy and
    baseline replicates recomputed; conditional accuracy and macro-F1 recomputed for every 20th replicate;
  * permutation swap sets regenerated; effective-accuracy statistics recomputed for every 10th permutation,
    macro-F1 statistics for every 50th; all p-values re-derived from the saved statistic files;
  * 95% percentile CIs re-extracted with an independently written interpolation.
Writes verification/verification_result.json (VERIFICATION.md is the hand-written summary of it). Exit code 1 on any discrepancy
beyond 1e-12 (floating-point last-ulp differences are counted and reported, not hidden)."""
import csv, gzip, hashlib, json, math, random, sys, collections
from fractions import Fraction as Q
from pathlib import Path

V = Path(__file__).resolve().parent; OUT = V.parent; RES = OUT.parent; BASE = RES.parent
DESC = RES / "descriptive_2026-09-21"
TOL = 1e-12
LAB = {"dreaddit": [0, 1], "goemotions": ["anxiety", "fear", "sadness", "frustration", "non_distress"]}
SH = {"google/gemma-4-31b-it": "Gemma 4 31B", "meta-llama/llama-4-scout": "Llama 4 Scout",
      "mistralai/mistral-small-2603": "Mistral Small 4", "microsoft/phi-4": "Phi-4", "qwen/qwen3.5-27b": "Qwen3.5 27B"}
ORDER = ["Gemma 4 31B", "Llama 4 Scout", "Mistral Small 4", "Phi-4", "Qwen3.5 27B"]
ST = ["zero-shot", "zero-shot-cot", "one-shot-cot"]
issues, stats = [], collections.Counter()
maxd = collections.defaultdict(float)

def H(p):
    h = hashlib.sha256(); h.update(open(p, "rb").read()); return h.hexdigest()
def close(where, a, b, field):
    stats["float_checks"] += 1; d = abs(float(a) - float(b)); maxd[field] = max(maxd[field], d)
    if d == 0: stats["float_exact"] += 1
    elif d <= TOL: stats["float_ulp"] += 1
    else: issues.append(f"{where} {field}: verifier {a!r} vs primary {b!r} (|d|={d:.3g})")
def eq(where, a, b, field):
    stats["exact_checks"] += 1
    if a != b: issues.append(f"{where} {field}: verifier {a!r} vs primary {b!r}")

# ---------------------------------------------------------------- inputs
man = json.load(open(OUT / "analysis_manifest.json"))
fm = json.load(open(DESC / "frozen_grid_manifest.json"))
eq("input", H(DESC / "frozen_grid_manifest.json"), "fba6a4617558b64bec61cee18e2a0b63e9457a03c6a3d94cd8e1a1916527dfa8", "sha256 frozen_grid_manifest")
eq("input", H(DESC / "authoritative_records.jsonl"), "97c8ca960e0f349dda121515fb45855e9c8787cc8a5cc35a0ce292c1d214a18a", "sha256 authoritative_records")
for ds, info in fm["manifests"].items():
    eq("input", H(BASE / "manifests" / info["file"]), info["file_sha256"], f"sha256 {ds} manifest")
for name, h in man["output_sha256"].items():
    p = (OUT / "tables" / name) if name.endswith(".csv") else (OUT / "replicates" / name)
    eq("output", H(p), h, f"sha256 {name} vs analysis_manifest")
eq("manifest", (man["B"], man["P"]), (4000, 10000), "replicate/permutation counts")

# ---------------------------------------------------------------- rebuild items (dicts)
cell = collections.defaultdict(dict)          # cell -> sample_id -> record
for line in open(DESC / "authoritative_records.jsonl", encoding="utf-8"):
    r = json.loads(line); cell[r["cell_id"]][r["sample_id"]] = r
eq("grid", (len(cell), sum(len(v) for v in cell.values())), (150, 100350), "cells/records")
for cid, d in cell.items():
    src = {r["source_run"] for r in d.values()}
    if cid == "dreaddit|google/gemma-4-31b-it|one-shot-cot|run5": eq(cid, src, {"pub_013_dreaddit_gemma_coreweave_osc_run5"}, "source")
    elif cid.startswith("dreaddit|google/gemma-4-31b-it"): eq(cid, src, {"pub_011_dreaddit_gemma_coreweave"}, "source")

DS = {}
for ds in LAB:
    cids = [c for c in cell if c.startswith(ds + "|")]
    idsets = {frozenset(cell[c]) for c in cids}
    safe = {frozenset(s for s, r in cell[c].items() if r["final_outcome_class"] == "SAFETY_INTERCEPT") for c in cids}
    eq(ds, (len(idsets), len(safe)), (1, 1), "one item set / one safety set")
    safe = next(iter(safe)); items = sorted(next(iter(idsets)) - safe)
    eq(ds, hashlib.sha256("\n".join(items).encode()).hexdigest(), man["items"][ds]["items_sha256"], "attributable item list")
    eq(ds, sorted(safe), man["items"][ds]["safety_excluded"], "safety items")
    gt = {s: cell[cids[0]][s]["ground_truth"] for s in items}
    # per configuration: list over runs of {sample: prediction or None}
    conf = {}
    for c in cids:
        _, m, st, run = c.split("|")
        conf.setdefault((SH[m], st), {})[int(run[3:])] = {s: (cell[c][s]["parsed_prediction"] if cell[c][s]["prediction_valid"] else None) for s in items}
    DS[ds] = {"items": items, "gt": gt, "conf": conf, "n": len(items)}

def per_run_metrics(preds, gt, items, L, weights=None):
    """weights: multiplicity of each item (bootstrap). Returns acc_eff, acc_cond, macro_f1 (frozen 2PR/(P+R) form)."""
    w = weights or {s: 1 for s in items}
    n = sum(w.values()); corr = sum(w[s] for s in items if preds[s] is not None and preds[s] == gt[s])
    val = sum(w[s] for s in items if preds[s] is not None)
    f1s = []
    for c in L:
        tp = sum(w[s] for s in items if preds[s] == c and gt[s] == c)
        fp = sum(w[s] for s in items if preds[s] is not None and preds[s] == c and gt[s] != c)
        fn = sum(w[s] for s in items if preds[s] is not None and preds[s] != c and gt[s] == c)
        P = tp / (tp + fp) if tp + fp else 0.0; R = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * P * R / (P + R) if P + R else 0.0)
    return Q(corr, n), (corr / val if val else 0.0), sum(f1s) / len(L)

OBS = {}
for ds, D in DS.items():
    for key, runs in D["conf"].items():
        ms = [per_run_metrics(runs[k], D["gt"], D["items"], LAB[ds]) for k in range(1, 6)]
        OBS[(ds,) + key] = {"acc_eff": sum((m[0] for m in ms), Q(0)) / 5, "acc_cond": sum(m[1] for m in ms) / 5, "macro_f1": sum(m[2] for m in ms) / 5,
                            "corr_runs": {s: sum(1 for k in range(1, 6) if runs[k][s] is not None and runs[k][s] == D["gt"][s]) for s in D["items"]}}

# ---------------------------------------------------------------- independent statistics helpers
def mcn(b, c):
    n = b + c
    if n == 0: return 1.0
    pmf = [Q(math.comb(n, k), 1) / (2 ** n) for k in range(n + 1)]
    return float(min(Q(1), 2 * sum(pmf[:min(b, c) + 1])))
def holm_v(ps):
    m = len(ps); idx = sorted(range(m), key=lambda i: (ps[i], i)); out = [None] * m; prev = 0.0
    for j, i in enumerate(idx):
        val = min(1.0, ps[i] * (m - j)); prev = val if val > prev else prev; out[i] = prev
    return out
def ci_v(xs):
    s = sorted(xs); B = len(s); res = []
    for q in (0.025, 0.975):
        pos = q * (B - 1); i = int(pos); frac = pos - i
        res.append(s[i] * (1 - frac) + s[min(i + 1, B - 1)] * frac if frac else s[i])
    return res

# ---------------------------------------------------------------- tables from primary
def rd(name): return list(csv.DictReader(open(OUT / "tables" / name)))
t1, t1m, t1c, t2, tc = (rd(n) for n in ("rq1_model_pairs_primary.csv", "rq1_model_pairs_mcnemar.csv",
                        "rq1_model_pairs_conditional_accuracy_ci.csv", "rq2_configuration_vs_baseline.csv", "configuration_level_ci.csv"))
eq("tables", (len(t1), len(t1m), len(t1c), len(t2), len(tc)), (120, 60, 60, 30, 30), "row counts")

# observed effects + pair construction
for r in t1:
    ds = r["dataset"]; a, b = OBS[(ds, r["model_A"], r["strategy"])], OBS[(ds, r["model_B"], r["strategy"])]
    eq(ds, ORDER.index(r["model_A"]) < ORDER.index(r["model_B"]), True, "pair orientation")
    close(ds, float(a[r["metric"]] - b[r["metric"]]), r["diff_A_minus_B"], "rq1 diff " + r["metric"])
    close(ds, float(a[r["metric"]]), r["A_value"], "rq1 A value")
pairs_seen = collections.Counter((r["dataset"], r["strategy"], r["model_A"], r["model_B"]) for r in t1)
eq("rq1", set(pairs_seen.values()), {2}, "each pair appears once per primary metric")
eq("rq1", len(pairs_seen), 60, "10 pairs x 3 strategies x 2 datasets")
# McNemar
for r in t1m:
    ds = r["dataset"]; a, b = OBS[(ds, r["model_A"], r["strategy"])], OBS[(ds, r["model_B"], r["strategy"])]
    bb = sum(1 for s in DS[ds]["items"] if a["corr_runs"][s] >= 3 and b["corr_runs"][s] < 3)
    cc = sum(1 for s in DS[ds]["items"] if a["corr_runs"][s] < 3 and b["corr_runs"][s] >= 3)
    eq(ds, (bb, cc), (int(r["b_A_correct_B_wrong"]), int(r["c_A_wrong_B_correct"])), "McNemar discordant counts")
    close(ds, mcn(bb, cc), r["p_exact"], "McNemar exact p")
for r in t1c:
    ds = r["dataset"]; a, b = OBS[(ds, r["model_A"], r["strategy"])], OBS[(ds, r["model_B"], r["strategy"])]
    close(ds, a["acc_cond"] - b["acc_cond"], r["diff_A_minus_B"], "rq1 conditional diff")
# baselines
BL = {}
for ds, D in DS.items():
    maj = collections.Counter(D["gt"].values()).most_common(1)[0][0]
    fullmaj = collections.Counter(json.load(open(BASE / "manifests" / fm["manifests"][ds]["file"]))["ground_truth"][s]
                                  for s in json.load(open(BASE / "manifests" / fm["manifests"][ds]["file"]))["included_sample_ids"])
    eq(ds, maj, fullmaj.most_common(1)[0][0], "majority class same on attributable and full set")
    BL[ds] = {"maj": maj, "rate": Q(sum(1 for s in D["items"] if D["gt"][s] == maj), D["n"]),
              "frozen": Q(fullmaj.most_common(1)[0][1], sum(fullmaj.values()))}
eq("baseline", (BL["dreaddit"]["rate"], BL["goemotions"]["rate"], BL["dreaddit"]["frozen"], BL["goemotions"]["frozen"]),
   (Q(355, 699), Q(487, 622), Q(369, 715), Q(487, 623)), "baseline fractions")
for r in t2:
    ds = r["dataset"]; o = OBS[(ds, r["model"], r["strategy"])]; D = DS[ds]
    close(ds, float(BL[ds]["rate"]), r["baseline_attributable"], "rq2 baseline")
    close(ds, float(o["acc_eff"] - BL[ds]["rate"]), r["diff_vs_baseline"], "rq2 diff")
    close(ds, float(o["acc_eff"] - BL[ds]["frozen"]), r["sens_diff_vs_frozen_scalar"], "rq2 sensitivity diff")
    bb = sum(1 for s in D["items"] if o["corr_runs"][s] >= 3 and D["gt"][s] != BL[ds]["maj"])
    cc = sum(1 for s in D["items"] if o["corr_runs"][s] < 3 and D["gt"][s] == BL[ds]["maj"])
    eq(ds, (bb, cc), (int(r["mc_b_config_correct_base_wrong"]), int(r["mc_c_config_wrong_base_correct"])), "rq2 McNemar counts")
    close(ds, mcn(bb, cc), r["mc_p_exact"], "rq2 McNemar p")

# ---------------------------------------------------------------- bootstrap
for ds, D in DS.items():
    n, items = D["n"], D["items"]
    rng = random.Random(man["bootstrap_seed_strings"][ds]); eq(ds, man["bootstrap_seed_strings"][ds], f"20260921|{ds}|bootstrap", "bootstrap seed")
    idx = [[rng.randrange(n) for _ in range(n)] for _ in range(4000)]
    h = hashlib.sha256()
    for row in idx: h.update(b"".join(i.to_bytes(2, "little") for i in row))
    eq(ds, h.hexdigest(), man["draw_sha256"][ds]["bootstrap_indices_u16le"], "bootstrap draws digest")
    with gzip.open(OUT / "replicates" / f"bootstrap_{ds}.csv.gz", "rt") as f:
        rows = list(csv.reader(f))
    hdr, data = rows[0], rows[1:]
    eq(ds, len(data), 4000, "bootstrap replicate count (saved)")
    col = {h_: i for i, h_ in enumerate(hdr)}
    base_ok = {s: 1 if D["gt"][s] == BL[ds]["maj"] else 0 for s in items}
    keys = list(D["conf"])
    for b, row in enumerate(idx):
        mult = collections.Counter(row); w = {items[i]: m for i, m in mult.items()}
        close(ds, sum(base_ok[s] * m for s, m in w.items()) / n, data[b][col["constant_majority_acc"]], "boot baseline replicate")
        for key in keys:
            o = OBS[(ds,) + key]
            acc = Q(sum(o["corr_runs"][s] * m for s, m in w.items()), 5 * n)
            close(ds, float(acc), data[b][col[f"{key[0]}|{key[1]}|acc_eff"]], "boot acc_eff replicate")
            if b % 20 == 0:
                sub = [s for s in items if s in w]
                ms = [per_run_metrics(D["conf"][key][k], D["gt"], sub, LAB[ds], w) for k in range(1, 6)]
                close(ds, sum(m[1] for m in ms) / 5, data[b][col[f"{key[0]}|{key[1]}|acc_cond"]], "boot acc_cond replicate")
                close(ds, sum(m[2] for m in ms) / 5, data[b][col[f"{key[0]}|{key[1]}|macro_f1"]], "boot macro_f1 replicate")
    stats[f"{ds}_boot_acc_replicates_recomputed"] = 4000 * len(keys); stats[f"{ds}_boot_f1_replicates_recomputed"] = 200 * len(keys)
    # CI extraction from the saved replicates (independent interpolation)
    get = lambda name: [float(r_[col[name]]) for r_ in data]
    for r in [x for x in tc if x["dataset"] == ds]:
        for k in ("acc_eff", "acc_cond", "macro_f1"):
            lo, hi = ci_v(get(f'{r["model"]}|{r["strategy"]}|{k}'))
            close(ds, lo, r[k + "_ci_low"], "cfg CI low"); close(ds, hi, r[k + "_ci_high"], "cfg CI high")
    for r in [x for x in t1 if x["dataset"] == ds]:
        A, B_ = get(f'{r["model_A"]}|{r["strategy"]}|{r["metric"]}'), get(f'{r["model_B"]}|{r["strategy"]}|{r["metric"]}')
        lo, hi = ci_v([x - y for x, y in zip(A, B_)]); close(ds, lo, r["ci_low"], "rq1 CI low"); close(ds, hi, r["ci_high"], "rq1 CI high")
    for r in [x for x in t1c if x["dataset"] == ds]:
        A, B_ = get(f'{r["model_A"]}|{r["strategy"]}|acc_cond'), get(f'{r["model_B"]}|{r["strategy"]}|acc_cond')
        lo, hi = ci_v([x - y for x, y in zip(A, B_)]); close(ds, lo, r["ci_low"], "cond CI low"); close(ds, hi, r["ci_high"], "cond CI high")
    bl = get("constant_majority_acc")
    for r in [x for x in t2 if x["dataset"] == ds]:
        A = get(f'{r["model"]}|{r["strategy"]}|acc_eff')
        lo, hi = ci_v([x - y for x, y in zip(A, bl)]); close(ds, lo, r["ci_low"], "rq2 CI low"); close(ds, hi, r["ci_high"], "rq2 CI high")
        lo, hi = ci_v([x - float(BL[ds]["frozen"]) for x in A]); close(ds, lo, r["sens_ci_low"], "rq2 sens CI low"); close(ds, hi, r["sens_ci_high"], "rq2 sens CI high")

# ---------------------------------------------------------------- permutation
for ds, D in DS.items():
    n, items = D["n"], D["items"]
    eq(ds, man["permutation_seed_strings"][ds], f"20260922|{ds}|permutation", "permutation seed")
    rng = random.Random(man["permutation_seed_strings"][ds]); bits = [rng.getrandbits(n) for _ in range(10000)]
    h = hashlib.sha256()
    for bb in bits: h.update(bb.to_bytes((n + 7) // 8, "little"))
    eq(ds, h.hexdigest(), man["draw_sha256"][ds]["permutation_bits_le"], "permutation draws digest")
    with gzip.open(OUT / "replicates" / f"permutation_{ds}.csv.gz", "rt") as f:
        rows = list(csv.reader(f))
    hdr, data = rows[0], rows[1:]; col = {h_: i for i, h_ in enumerate(hdr)}
    eq(ds, len(data), 10000, "permutation count (saved)")
    swapped = [[i for i in range(n) if (bb >> i) & 1] for bb in bits]
    def pval_from(saved, obs, integer):
        if integer: return (1 + sum(1 for x in saved if abs(int(x)) >= abs(obs))) / 10001
        return (1 + sum(1 for x in saved if abs(float(x)) >= abs(obs) - 1e-12)) / 10001
    for r in [x for x in t1 if x["dataset"] == ds]:
        tag = f'{r["model_A"]} vs {r["model_B"]} @ {r["strategy"]}'
        a, b = OBS[(ds, r["model_A"], r["strategy"])], OBS[(ds, r["model_B"], r["strategy"])]
        if r["metric"] == "acc_eff":
            name = tag + " | acc_eff (int)"; d = [a["corr_runs"][s] - b["corr_runs"][s] for s in items]; Tobs = sum(d)
            for p_ in range(0, 10000, 10):
                eq(ds, Tobs - 2 * sum(d[i] for i in swapped[p_]), int(data[p_][col[name]]), "perm acc statistic")
            saved = [row[col[name]] for row in data]; p = pval_from(saved, Tobs, True)
        else:
            name = tag + " | macro_f1"; Tobs = float(a["macro_f1"] - b["macro_f1"])
            ra, rb = D["conf"][(r["model_A"], r["strategy"])], D["conf"][(r["model_B"], r["strategy"])]
            for p_ in range(0, 10000, 50):
                sw = {items[i] for i in swapped[p_]}
                fa = [per_run_metrics({s: (rb[k][s] if s in sw else ra[k][s]) for s in items}, D["gt"], items, LAB[ds])[2] for k in range(1, 6)]
                fb = [per_run_metrics({s: (ra[k][s] if s in sw else rb[k][s]) for s in items}, D["gt"], items, LAB[ds])[2] for k in range(1, 6)]
                close(ds, sum(fa) / 5 - sum(fb) / 5, data[p_][col[name]], "perm macro_f1 statistic")
            saved = [row[col[name]] for row in data]; p = pval_from(saved, Tobs, False)
        close(ds, p, r["p_perm"], "perm p-value")
    for r in [x for x in t2 if x["dataset"] == ds]:
        name = f'{r["model"]}|{r["strategy"]} vs constant | acc_eff (int)'; o = OBS[(ds, r["model"], r["strategy"])]
        d = [o["corr_runs"][s] - (5 if D["gt"][s] == BL[ds]["maj"] else 0) for s in items]; Tobs = sum(d)
        for p_ in range(0, 10000, 10):
            eq(ds, Tobs - 2 * sum(d[i] for i in swapped[p_]), int(data[p_][col[name]]), "rq2 perm statistic")
        close(ds, pval_from([row[col[name]] for row in data], Tobs, True), r["p_perm"], "rq2 perm p")

# ---------------------------------------------------------------- Holm (independent)
for fam_rows, pk, hk, sk in ((t1, "p_perm", "p_holm", "holm_significant_0.05"), (t1m, "p_exact", "p_holm", "holm_significant_0.05"),
                             (t2, "p_perm", "p_holm", "holm_significant_0.05"), (t2, "mc_p_exact", "mc_p_holm", "mc_holm_significant_0.05")):
    for ds in LAB:
        rows = [r for r in fam_rows if r["dataset"] == ds]
        adj = holm_v([float(r[pk]) for r in rows])
        for r, a in zip(rows, adj):
            close(ds, a, r[hk], f"Holm {pk}"); eq(ds, str(a <= 0.05), r[sk], f"Holm decision {pk}")
        eq(ds, len(rows), {"p_perm": 60 if fam_rows is t1 else 15, "p_exact": 30, "mc_p_exact": 15}[pk], f"family size {pk}")

res = {"passed": not issues, "issues": issues, "stats": dict(stats), "max_abs_float_diff_by_field": dict(maxd)}
json.dump(res, open(V / "verification_result.json", "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "issues"}, indent=1)); print("ISSUES:", len(issues))
for i in issues[:50]: print("  ", i)
sys.exit(0 if not issues else 1)
