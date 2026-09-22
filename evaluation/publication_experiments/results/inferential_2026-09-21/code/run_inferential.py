#!/usr/bin/env python3
"""
Inferential analysis for RQ1 (model comparison) and RQ2 (configuration vs majority baseline)
on the FROZEN AnxioSense publication grid. Design: STATISTICAL_ANALYSIS_PLAN.md, section F.

INPUTS (read-only, sha256-checked against frozen values before anything is computed)
  results/descriptive_2026-09-21/authoritative_records.jsonl   100,350 scored records (the only data source)
  results/descriptive_2026-09-21/frozen_grid_manifest.json      cells, composition rule, per-cell record hashes
  results/descriptive_2026-09-21/per_run_results.csv, aggregate_results.csv   (cross-check only)
  manifests/official_dreaddit_test.json, manifests/goemotions_715_subset_2026-09-09.json (ground truth)

STATISTICAL UNIT  the dataset item (sample_id). Safety-intercepted items (identical in every cell:
                  16 Dreaddit, 1 GoEmotions) are excluded from model attribution exactly as frozen.
                  Inference population: 699 Dreaddit / 622 GoEmotions attributable items.
PAIRING           every configuration was scored on the same items -> comparisons are paired by item.
                  Runs are NOT paired across configurations; they stay nested inside their item.
REPEATED RUNS     never treated as independent observations. The estimand is the frozen five-run
                  value = mean over runs 1..5 of the per-run metric.
BOOTSTRAP         resample ITEMS with replacement (cluster = item carrying all 15 configs x 5 runs),
                  one shared index vector per replicate for all configurations; B = 4,000;
                  seed string "20260921|<dataset>|bootstrap"; 95% percentile CI, linear interpolation.
PERMUTATION TEST  primary p-values. Paired item-level swap test, P = 10,000 swap sets per dataset,
                  seed string "20260922|<dataset>|permutation"; p = (1 + #{|T*| >= |T_obs|}) / (1 + P).
McNEMAR           secondary: exact test on per-item majority-vote effective correctness (>= 3 of 5 runs).
HOLM              families (per dataset): RQ1 primary 60 (10 pairs x 3 strategies x {acc_eff, macro_f1});
                  RQ1 McNemar 30; RQ2 primary 15; RQ2 McNemar 15.
METRICS           MetricPolicy 1.0.0: model-invalid outputs count as not-correct on the attributable
                  denominator (effective accuracy) and contribute nothing to per-class tp/fp/fn (macro-F1);
                  conditional accuracy = correct/valid (CIs only, no tests).
OUTPUTS           tables/*.csv, tables/*.md, replicates/*.csv.gz, analysis_manifest.json (this directory only).

Requires Python >= 3.9 and numpy (used only for exact integer-valued matrix sums; all counts are
integers < 2^53, so float64 matrix products are exact).
"""
import csv, gzip, hashlib, json, math, os, platform, random, sys, time, collections
from fractions import Fraction
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent                                   # results/inferential_2026-09-21
RES = OUT.parent                                    # results/
BASE = RES.parent                                   # evaluation/publication_experiments
DESC = RES / "descriptive_2026-09-21"

# ---------------------------------------------------------------- frozen expectations
EXPECTED_SHA256 = {   # values recorded in the frozen descriptive results / grid manifest
    DESC / "authoritative_records.jsonl": "97c8ca960e0f349dda121515fb45855e9c8787cc8a5cc35a0ce292c1d214a18a",
    DESC / "frozen_grid_manifest.json": "fba6a4617558b64bec61cee18e2a0b63e9457a03c6a3d94cd8e1a1916527dfa8",
    DESC / "per_run_results.csv": "6b3f374a0e76d2c8068c06cc077a2affadd1cd15ac91aab027efeb591efe86ec",
    DESC / "aggregate_results.csv": "4242c3634c8939714eb0b7ff25b446783f1747add91c36040a95bf02f1646768",
}
B_REPS, P_PERMS, ALPHA = 4000, 10000, 0.05
BOOT_SEED, PERM_SEED = "20260921", "20260922"
LABELS = {"dreaddit": [0, 1], "goemotions": ["anxiety", "fear", "sadness", "frustration", "non_distress"]}
N_ITEMS = {"dreaddit": 715, "goemotions": 623}
N_SAFETY = {"dreaddit": 16, "goemotions": 1}
MODELS = ["google/gemma-4-31b-it", "meta-llama/llama-4-scout", "mistralai/mistral-small-2603",
          "microsoft/phi-4", "qwen/qwen3.5-27b"]          # fixed order; pair (A,B) has A earlier in this list
SHORT = {"google/gemma-4-31b-it": "Gemma 4 31B", "meta-llama/llama-4-scout": "Llama 4 Scout",
         "mistralai/mistral-small-2603": "Mistral Small 4", "microsoft/phi-4": "Phi-4", "qwen/qwen3.5-27b": "Qwen3.5 27B"}
STRATS = ["zero-shot", "zero-shot-cot", "one-shot-cot"]
CONFIGS = [(m, s) for m in MODELS for s in STRATS]        # 15 configurations per dataset
RUNS = [1, 2, 3, 4, 5]
GEMMA_REPLACED = "dreaddit|google/gemma-4-31b-it|one-shot-cot|run5"

def gz_text_writer(path):
    """Deterministic gzip (mtime=0, no embedded filename) so reruns produce byte-identical files."""
    import io
    return io.TextIOWrapper(gzip.GzipFile(filename="", mode="wb", fileobj=open(path, "wb"), mtime=0), newline="", encoding="utf-8")

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def fail(msg):
    sys.exit("FAIL-CLOSED: " + msg)

# ================================================================ 1. integrity checks
for p, h in EXPECTED_SHA256.items():
    if sha256(p) != h: fail(f"sha256 mismatch for {p}")
fm = json.load(open(DESC / "frozen_grid_manifest.json"))
for ds, info in fm["manifests"].items():
    if sha256(BASE / "manifests" / info["file"]) != info["file_sha256"]: fail(f"dataset manifest hash {ds}")

records = collections.defaultdict(list)
n_lines = 0
with open(DESC / "authoritative_records.jsonl", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line); n_lines += 1; records[r["cell_id"]].append(r)
if n_lines != 100350 or len(records) != 150: fail(f"expected 150 cells / 100,350 records, got {len(records)} / {n_lines}")
if set(records) != set(fm["cells"]): fail("cell set differs from frozen manifest")

gt_manifest = {}
for ds, info in fm["manifests"].items():
    M = json.load(open(BASE / "manifests" / info["file"]))
    gt_manifest[ds] = {s: M["ground_truth"][s] for s in M["included_sample_ids"]}
    if len(gt_manifest[ds]) != N_ITEMS[ds]: fail(f"{ds} manifest size")

src_rule = {}
for cid, recs in records.items():
    ds, model, strat, run = cid.split("|")
    fc = fm["cells"][cid]
    if len(recs) != N_ITEMS[ds] or fc["n"] != N_ITEMS[ds]: fail(f"{cid}: n")
    # per-cell record hash exactly as frozen: sha256 of sorted "sample_id|terminal_attempt_uuid" lines
    key = "\n".join(sorted(f'{r["sample_id"]}|{r["terminal_attempt_uuid"]}' for r in recs))
    if hashlib.sha256(key.encode()).hexdigest() != fc["records_sha256"]: fail(f"{cid}: records_sha256")
    srcs = {r["source_run"] for r in recs}
    if len(srcs) != 1: fail(f"{cid}: mixed source runs")
    src_rule[cid] = srcs.pop()
    for r in recs:
        if r["cell_id"] != cid or r["dataset"] != ds or r["model"] != model or r["strategy"] != strat: fail(f"{cid}: identity")
        if r["ground_truth"] != gt_manifest[ds].get(r["sample_id"]): fail(f"{cid} {r['sample_id']}: ground truth")
        o = (r["final_outcome_class"], r["failure_class"], r["prediction_valid"])
        if o == ("OK", None, True):
            if r["parsed_prediction"] not in LABELS[ds]: fail(f"{cid}: valid prediction outside label set")
        elif o not in {("OK", "MODEL_BEHAVIOUR", False), ("SAFETY_INTERCEPT", "SAFETY_INTERCEPT", False)}:
            fail(f"{cid}: unexpected outcome {o}")
# Gemma Dreaddit composition as frozen
for cid, src in src_rule.items():
    if cid.startswith("dreaddit|google/gemma-4-31b-it|"):
        want = "pub_013_dreaddit_gemma_coreweave_osc_run5" if cid == GEMMA_REPLACED else "pub_011_dreaddit_gemma_coreweave"
        if src != want: fail(f"Gemma composition: {cid} from {src}")
    if src == "pub_013_dreaddit_gemma_coreweave_osc_run5" and cid != GEMMA_REPLACED: fail("pub_013 used outside replacement cell")

# ================================================================ 2. item x config x run arrays
DATA = {}
for ds in ("dreaddit", "goemotions"):
    cells = {c: records[c] for c in records if c.startswith(ds + "|")}
    id_sets = {frozenset(r["sample_id"] for r in v) for v in cells.values()}
    safe_sets = {frozenset(r["sample_id"] for r in v if r["final_outcome_class"] == "SAFETY_INTERCEPT") for v in cells.values()}
    if len(id_sets) != 1 or len(safe_sets) != 1: fail(f"{ds}: items do not pair across cells")
    ids, safe = next(iter(id_sets)), next(iter(safe_sets))
    if ids != set(gt_manifest[ds]) or len(safe) != N_SAFETY[ds]: fail(f"{ds}: item/safety set")
    items = sorted(ids - safe)                                  # ATTRIBUTABLE items, fixed order
    L = LABELS[ds]; K = len(L); n = len(items); pos = {s: i for i, s in enumerate(items)}
    gt = np.array([L.index(gt_manifest[ds][s]) for s in items])
    pred = np.full((n, len(CONFIGS), 5), -1, dtype=np.int64)    # -1 = model-invalid output
    for ci, (m, s) in enumerate(CONFIGS):
        for run in RUNS:
            recs = cells[f"{ds}|{m}|{s}|run{run}"]
            seen = 0
            for r in recs:
                if r["sample_id"] in safe: continue
                seen += 1
                if r["prediction_valid"]: pred[pos[r["sample_id"]], ci, run - 1] = L.index(r["parsed_prediction"])
            if seen != n: fail(f"{ds} {m} {s} run{run}: attributable count")
    # Per item, config, run: feature vector [correct, valid, tp_0..tp_K-1, fp_0.., fn_0..]  (all 0/1)
    valid = pred >= 0
    correct = valid & (pred == gt[:, None, None])
    feats = [correct, valid]
    for k in range(K):
        feats.append(valid & (pred == k) & (gt[:, None, None] == k))   # tp_k
    for k in range(K):
        feats.append(valid & (pred == k) & (gt[:, None, None] != k))   # fp_k
    for k in range(K):
        feats.append(valid & (pred != k) & (gt[:, None, None] == k))   # fn_k
    F = np.stack(feats, axis=-1).astype(np.float64)             # (n, 15, 5, 2+3K)
    maj = collections.Counter(gt_manifest[ds].values()).most_common(1)[0][0]   # same class as frozen baseline
    DATA[ds] = {"items": items, "n": n, "K": K, "gt": gt, "pred": pred, "F": F, "correct": correct,
                "maj_index": L.index(maj), "maj_label": maj, "safe": sorted(safe)}

# ================================================================ 3. metric functions
def metrics_from_counts(C, n, K):
    """C: (..., 5 runs, 2+3K) counts. Returns five-run acc_eff, acc_cond, macro_f1 (each shape C.shape[:-2]).
    Per run: acc_eff = correct/n; acc_cond = correct/valid; F1_k = 2tp/(2tp+fp+fn) if tp>0 else 0
    (== frozen 2PR/(P+R) with P,R=0 when undefined); macro = mean_k F1_k. Five-run value = mean over runs."""
    corr, val = C[..., 0], C[..., 1]
    tp, fp, fn = C[..., 2:2 + K], C[..., 2 + K:2 + 2 * K], C[..., 2 + 2 * K:2 + 3 * K]
    with np.errstate(divide="ignore", invalid="ignore"):
        f1 = np.where(tp > 0, 2 * tp / (2 * tp + fp + fn), 0.0)
        acc_cond = np.where(val > 0, corr / val, 0.0)
    return {"acc_eff": (corr / n).mean(axis=-1), "acc_cond": acc_cond.mean(axis=-1), "macro_f1": f1.mean(axis=-1).mean(axis=-1)}

def pct_ci(x):
    """95% percentile interval, linear interpolation between order statistics (numpy 'linear' / type 7)."""
    xs = sorted(x); out = []
    for q in (0.025, 0.975):
        h = (len(xs) - 1) * q; lo = math.floor(h)
        out.append(float(xs[lo] + (h - lo) * (xs[min(lo + 1, len(xs) - 1)] - xs[lo])))
    return out

def mcnemar_exact(b, c):
    """Exact two-sided McNemar: 2 * P(X <= min(b,c)), X ~ Bin(b+c, 1/2), capped at 1. Exact rational arithmetic."""
    n = b + c
    if n == 0: return 1.0
    tail = Fraction(sum(math.comb(n, k) for k in range(min(b, c) + 1)), 2 ** n)
    return float(min(Fraction(1), 2 * tail))

def holm(pvals):
    """Holm step-down adjusted p-values, returned in the original order."""
    m = len(pvals); order = sorted(range(m), key=lambda i: pvals[i]); adj = [0.0] * m; running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvals[i])); adj[i] = running
    return adj

# ================================================================ 4. observed values + cross-check with frozen results
frozen_run = {("%s|%s|%s|run%s" % (r["dataset"], r["model"], r["strategy"], r["run"])): r for r in csv.DictReader(open(DESC / "per_run_results.csv"))}
frozen_agg = {(r["dataset"], r["model"], r["strategy"]): r for r in csv.DictReader(open(DESC / "aggregate_results.csv"))}
OBS = {}
maxdiff = 0.0
for ds, D in DATA.items():
    C = D["F"].sum(axis=0)                                      # (15, 5, feat)
    OBS[ds] = metrics_from_counts(C, D["n"], D["K"])
    corr, val = C[..., 0], C[..., 1]
    for ci, (m, s) in enumerate(CONFIGS):
        for run in RUNS:
            fr = frozen_run[f"{ds}|{m}|{s}|run{run}"]
            if int(fr["correct"]) != corr[ci, run - 1] or int(fr["N_valid"]) != val[ci, run - 1]: fail(f"count mismatch {ds} {m} {s} {run}")
            one = metrics_from_counts(C[ci:ci + 1, run - 1:run], D["n"], D["K"])
            for key, col in (("acc_eff", "accuracy_effective"), ("acc_cond", "accuracy_conditional"), ("macro_f1", "macro_f1")):
                d = abs(float(one[key][0]) - float(fr[col])); maxdiff = max(maxdiff, d)
                if d > 1e-12: fail(f"per-run {key} differs from frozen {ds} {m} {s} run{run}: {d}")
        fa = frozen_agg[(ds, m, s)]
        for key, col in (("acc_eff", "accuracy_effective_mean"), ("acc_cond", "accuracy_conditional_mean"), ("macro_f1", "macro_f1_mean")):
            d = abs(float(OBS[ds][key][ci]) - float(fa[col])); maxdiff = max(maxdiff, d)
            if d > 1e-12: fail(f"five-run {key} differs from frozen {ds} {m} {s}: {d}")

# ================================================================ 5. random draws (stdlib RNG, reproducible without numpy)
def bootstrap_indices(ds, n):
    rng = random.Random(f"{BOOT_SEED}|{ds}|bootstrap")
    return [[rng.randrange(n) for _ in range(n)] for _ in range(B_REPS)]
def permutation_bits(ds, n):
    rng = random.Random(f"{PERM_SEED}|{ds}|permutation")
    return [rng.getrandbits(n) for _ in range(P_PERMS)]
def digest_indices(idx):
    h = hashlib.sha256()
    for row in idx: h.update(np.asarray(row, dtype="<u2").tobytes())
    return h.hexdigest()
def digest_bits(bits, n):
    h = hashlib.sha256()
    for b in bits: h.update(b.to_bytes((n + 7) // 8, "little"))
    return h.hexdigest()

manifest = {"created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "python": platform.python_version(),
            "numpy": np.__version__, "B": B_REPS, "P": P_PERMS, "alpha": ALPHA,
            "bootstrap_seed_strings": {}, "permutation_seed_strings": {}, "draw_sha256": {},
            "input_sha256": {str(p.relative_to(RES)): h for p, h in EXPECTED_SHA256.items()},
            "max_abs_diff_observed_vs_frozen": maxdiff, "families": {}, "items": {}, "notes": []}
for p in sorted(HERE.glob("*.py")): manifest.setdefault("code_sha256", {})[p.name] = sha256(p)

rows_rq1, rows_rq1_mc, rows_rq1_cond, rows_rq2, rows_cfg = [], [], [], [], []
for ds, D in DATA.items():
    n, K, F = D["n"], D["K"], D["F"]
    t0 = time.time()
    idx = bootstrap_indices(ds, n); bits = permutation_bits(ds, n)
    manifest["bootstrap_seed_strings"][ds] = f"{BOOT_SEED}|{ds}|bootstrap"
    manifest["permutation_seed_strings"][ds] = f"{PERM_SEED}|{ds}|permutation"
    manifest["draw_sha256"][ds] = {"bootstrap_indices_u16le": digest_indices(idx), "permutation_bits_le": digest_bits(bits, n)}
    manifest["items"][ds] = {"n_attributable": n, "items_sha256": hashlib.sha256("\n".join(D["items"]).encode()).hexdigest(),
                             "safety_excluded": D["safe"], "majority_class": D["maj_label"]}
    # W[b, i] = how many times item i was drawn in replicate b
    W = np.zeros((B_REPS, n))
    for b, row in enumerate(idx): np.add.at(W[b], row, 1)
    assert (W.sum(axis=1) == n).all()
    # S[p, i] = 1 if item i is swapped in permutation p
    S = np.array([[(bb >> i) & 1 for i in range(n)] for bb in bits], dtype=np.float64)

    # ---- bootstrap: replicate five-run metrics for every configuration (shared draws)
    Fflat = F.reshape(n, -1)
    Cb = (W @ Fflat).reshape(B_REPS, len(CONFIGS), 5, -1)        # exact integer counts
    REP = metrics_from_counts(Cb, n, K)                         # each (B, 15)
    b_corr = (D["gt"] == D["maj_index"]).astype(np.float64)     # constant majority predictor: correct 0/1 per item
    rep_base = (W @ b_corr) / n                                 # (B,)
    obs_base = float(b_corr.mean())
    no_anx = int((W[:, D["gt"] == 0] .sum(axis=1) == 0).sum()) if ds == "goemotions" else None
    if ds == "goemotions": manifest["notes"].append(f"goemotions: {no_anx} of {B_REPS} bootstrap replicates contain no 'anxiety' item; per MetricPolicy 1.0.0 its recall/F1 = 0 in those replicates (applied verbatim).")
    # save replicate values (enough to re-derive every CI by subtraction)
    with gz_text_writer(OUT / "replicates" / f"bootstrap_{ds}.csv.gz") as f:
        w = csv.writer(f); hdr = ["replicate", "constant_majority_acc"]
        for (m, s) in CONFIGS:
            hdr += [f"{SHORT[m]}|{s}|{k}" for k in ("acc_eff", "acc_cond", "macro_f1")]
        w.writerow(hdr)
        for b in range(B_REPS):
            row = [b, repr(float(rep_base[b]))]
            for ci in range(len(CONFIGS)):
                row += [repr(float(REP[k][b, ci])) for k in ("acc_eff", "acc_cond", "macro_f1")]
            w.writerow(row)

    # ---- configuration-level CIs (RQ2 descriptive support)
    for ci, (m, s) in enumerate(CONFIGS):
        r = {"dataset": ds, "model": SHORT[m], "strategy": s, "n_items": n}
        for k in ("acc_eff", "acc_cond", "macro_f1"):
            lo, hi = pct_ci(REP[k][:, ci]); r[k] = float(OBS[ds][k][ci]); r[k + "_ci_low"] = lo; r[k + "_ci_high"] = hi
        rows_cfg.append(r)

    # ---- permutation machinery for a pair of configurations (A = ci, B = cj)
    corr_runs = D["correct"].sum(axis=2).astype(np.int64)        # (n, 15) correct runs per item (0..5)
    def perm_pair(ci, cj):
        """Swap test: for swapped items, A receives B's five run outcomes and vice versa."""
        dF = (F[:, cj] - F[:, ci]).reshape(n, -1)                # (n, 5*feat)
        base_A = F[:, ci].sum(axis=0); base_B = F[:, cj].sum(axis=0)
        shift = (S @ dF).reshape(P_PERMS, 5, -1)
        mA = metrics_from_counts(base_A[None] + shift, n, K); mB = metrics_from_counts(base_B[None] - shift, n, K)
        # effective accuracy compared EXACTLY as integers: T = sum of correct run-outcomes (A) - (B)
        d_int = corr_runs[:, ci] - corr_runs[:, cj]
        T_obs_int = int(d_int.sum())
        T_perm_int = (d_int[None, :] * (1 - 2 * S)).sum(axis=1).astype(np.int64)
        p_acc = (1 + int((np.abs(T_perm_int) >= abs(T_obs_int)).sum())) / (1 + P_PERMS)
        T_obs_f1 = float(OBS[ds]["macro_f1"][ci] - OBS[ds]["macro_f1"][cj])
        T_perm_f1 = mA["macro_f1"] - mB["macro_f1"]
        p_f1 = (1 + int((np.abs(T_perm_f1) >= abs(T_obs_f1) - 1e-12).sum())) / (1 + P_PERMS)
        # sanity: integer statistic equals 5n * accuracy difference of the permuted metrics
        assert np.allclose(T_perm_int / (5 * n), mA["acc_eff"] - mB["acc_eff"], atol=1e-12)
        return p_acc, p_f1, T_perm_int, T_perm_f1

    perm_store = {}
    fam_rq1, fam_rq1_mc = [], []
    for s in STRATS:
        for a in range(len(MODELS)):
            for bm in range(a + 1, len(MODELS)):
                ci, cj = CONFIGS.index((MODELS[a], s)), CONFIGS.index((MODELS[bm], s))
                p_acc, p_f1, Tpi, Tpf = perm_pair(ci, cj)
                tag = f"{SHORT[MODELS[a]]} vs {SHORT[MODELS[bm]]} @ {s}"
                perm_store[tag + " | acc_eff (int)"] = Tpi; perm_store[tag + " | macro_f1"] = Tpf
                for metric, p in (("acc_eff", p_acc), ("macro_f1", p_f1)):
                    vA, vB = float(OBS[ds][metric][ci]), float(OBS[ds][metric][cj])
                    lo, hi = pct_ci(REP[metric][:, ci] - REP[metric][:, cj])
                    row = {"dataset": ds, "family": f"RQ1-primary-{ds}", "metric": metric, "strategy": s,
                           "model_A": SHORT[MODELS[a]], "model_B": SHORT[MODELS[bm]], "n_items": n,
                           "A_value": vA, "B_value": vB, "diff_A_minus_B": vA - vB, "ci_low": lo, "ci_high": hi,
                           "p_perm": p, "direction": ("A higher" if vA > vB else "B higher" if vB > vA else "equal")}
                    rows_rq1.append(row); fam_rq1.append(row)
                # conditional accuracy: CI only, clearly labelled
                vA, vB = float(OBS[ds]["acc_cond"][ci]), float(OBS[ds]["acc_cond"][cj])
                lo, hi = pct_ci(REP["acc_cond"][:, ci] - REP["acc_cond"][:, cj])
                rows_rq1_cond.append({"dataset": ds, "strategy": s, "model_A": SHORT[MODELS[a]], "model_B": SHORT[MODELS[bm]],
                                      "A_acc_cond": vA, "B_acc_cond": vB, "diff_A_minus_B": vA - vB, "ci_low": lo, "ci_high": hi,
                                      "A_valid_run_outcomes": int(D["F"][:, ci, :, 1].sum()), "B_valid_run_outcomes": int(D["F"][:, cj, :, 1].sum()),
                                      "note": "conditional on each configuration's own valid predictions; denominators differ; no test"})
                # McNemar on majority-vote effective correctness (>= 3 of 5 runs)
                mvA, mvB = corr_runs[:, ci] >= 3, corr_runs[:, cj] >= 3
                bb, cc = int((mvA & ~mvB).sum()), int((~mvA & mvB).sum())
                r = {"dataset": ds, "family": f"RQ1-mcnemar-{ds}", "strategy": s, "model_A": SHORT[MODELS[a]], "model_B": SHORT[MODELS[bm]],
                     "n_items": n, "A_majority_correct": int(mvA.sum()), "B_majority_correct": int(mvB.sum()),
                     "b_A_correct_B_wrong": bb, "c_A_wrong_B_correct": cc, "discordant": bb + cc,
                     "diff_majority_acc": (int(mvA.sum()) - int(mvB.sum())) / n, "p_exact": mcnemar_exact(bb, cc)}
                rows_rq1_mc.append(r); fam_rq1_mc.append(r)
    for fam, key in ((fam_rq1, "p_perm"), (fam_rq1_mc, "p_exact")):
        adj = holm([r[key] for r in fam])
        for r, a in zip(fam, adj): r["p_holm"] = a; r["holm_significant_0.05"] = a <= ALPHA; r["family_size"] = len(fam)
    manifest["families"][f"RQ1-primary-{ds}"] = len(fam_rq1); manifest["families"][f"RQ1-mcnemar-{ds}"] = len(fam_rq1_mc)

    # ---- RQ2: each configuration vs the paired constant majority-class predictor (effective accuracy)
    fam_rq2 = []
    frozen_scalar = Fraction(*{"dreaddit": (369, 715), "goemotions": (487, 623)}[ds])
    b_int = (D["gt"] == D["maj_index"]).astype(np.int64) * 5      # constant predictor: 5 correct run-outcomes or 0
    for ci, (m, s) in enumerate(CONFIGS):
        d_int = corr_runs[:, ci] - b_int
        T_obs = int(d_int.sum())
        T_perm = (d_int[None, :] * (1 - 2 * S)).sum(axis=1).astype(np.int64)
        perm_store[f"{SHORT[m]}|{s} vs constant | acc_eff (int)"] = T_perm
        p = (1 + int((np.abs(T_perm) >= abs(T_obs)).sum())) / (1 + P_PERMS)
        v = float(OBS[ds]["acc_eff"][ci])
        lo, hi = pct_ci(REP["acc_eff"][:, ci] - rep_base)
        slo, shi = pct_ci(REP["acc_eff"][:, ci] - float(frozen_scalar))
        mv = corr_runs[:, ci] >= 3; bc = b_corr.astype(bool)
        bb, cc = int((mv & ~bc).sum()), int((~mv & bc).sum())
        r = {"dataset": ds, "family": f"RQ2-primary-{ds}", "model": SHORT[m], "strategy": s, "n_items": n,
             "acc_eff": v, "acc_eff_ci_low": pct_ci(REP["acc_eff"][:, ci])[0], "acc_eff_ci_high": pct_ci(REP["acc_eff"][:, ci])[1],
             "baseline_attributable": obs_base, "diff_vs_baseline": v - obs_base, "ci_low": lo, "ci_high": hi, "p_perm": p,
             "direction": "above baseline" if v > obs_base else "below baseline" if v < obs_base else "equal",
             "mc_config_majority_correct": int(mv.sum()), "mc_baseline_correct": int(bc.sum()),
             "mc_b_config_correct_base_wrong": bb, "mc_c_config_wrong_base_correct": cc, "mc_p_exact": mcnemar_exact(bb, cc),
             "sens_frozen_scalar": float(frozen_scalar), "sens_diff_vs_frozen_scalar": v - float(frozen_scalar),
             "sens_ci_low": slo, "sens_ci_high": shi}
        rows_rq2.append(r); fam_rq2.append(r)
    adj = holm([r["p_perm"] for r in fam_rq2]); adjm = holm([r["mc_p_exact"] for r in fam_rq2])
    for r, a, am in zip(fam_rq2, adj, adjm):
        r["p_holm"] = a; r["holm_significant_0.05"] = a <= ALPHA; r["mc_p_holm"] = am; r["mc_holm_significant_0.05"] = am <= ALPHA
    manifest["families"][f"RQ2-primary-{ds}"] = len(fam_rq2); manifest["families"][f"RQ2-mcnemar-{ds}"] = len(fam_rq2)
    # save permutation statistics (enables independent re-derivation of every permutation p-value)
    with gz_text_writer(OUT / "replicates" / f"permutation_{ds}.csv.gz") as f:
        w = csv.writer(f); keys = list(perm_store); w.writerow(["permutation"] + keys)
        for p_ in range(P_PERMS): w.writerow([p_] + [(int(perm_store[k][p_]) if k.endswith("(int)") else repr(float(perm_store[k][p_]))) for k in keys])
    print(f"{ds}: done in {time.time() - t0:.1f}s", flush=True)

# ================================================================ 6. write tables
def write_csv(name, rows):
    with open(OUT / "tables" / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader()
        for r in rows:
            for k, v in r.items():
                if type(v).__module__ == "numpy": fail(f"numpy scalar leaked into table {name}:{k}")
            w.writerow({k: (repr(v) if isinstance(v, float) else v) for k, v in r.items()})
write_csv("rq1_model_pairs_primary.csv", rows_rq1)
write_csv("rq1_model_pairs_mcnemar.csv", rows_rq1_mc)
write_csv("rq1_model_pairs_conditional_accuracy_ci.csv", rows_rq1_cond)
write_csv("rq2_configuration_vs_baseline.csv", rows_rq2)
write_csv("configuration_level_ci.csv", rows_cfg)
manifest["output_sha256"] = {p.name: sha256(p) for p in sorted((OUT / "tables").glob("*.csv"))}
manifest["output_sha256"].update({p.name: sha256(p) for p in sorted((OUT / "replicates").glob("*.gz"))})
json.dump(manifest, open(OUT / "analysis_manifest.json", "w"), indent=1)
print("rq1 primary sig:", sum(r["holm_significant_0.05"] for r in rows_rq1), "/", len(rows_rq1),
      "| rq1 mcnemar sig:", sum(r["holm_significant_0.05"] for r in rows_rq1_mc), "/", len(rows_rq1_mc),
      "| rq2 sig:", sum(r["holm_significant_0.05"] for r in rows_rq2), "/", len(rows_rq2))
print("max |observed - frozen| =", maxdiff)
