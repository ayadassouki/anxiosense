#!/usr/bin/env python3
"""
Deterministic PRESENTATION tables for the frozen AnxioSense RQ1-RQ3 analysis.

This script RENDERS existing frozen results. It does not run experiments, does not call any model
API, does not recompute the inferential analysis, and never writes outside
results/rq1_rq3_tables/. All inputs are opened read-only and sha256-gated.

INPUTS (sha256 verified; any mismatch aborts before a single output byte is written)
  results/descriptive_2026-09-21/aggregate_results.csv      five-run means/SDs + 5-run count sums  [values used verbatim]
  results/descriptive_2026-09-21/aggregate_five_runs.json   same aggregates, JSON form             [cross-check]
  results/descriptive_2026-09-21/per_run_results.csv        150 per-run rows incl. macro P/R       [independent cross-check]
  results/descriptive_2026-09-21/cell_metrics.json          150 per-cell buckets                   [count cross-check]
  results/descriptive_2026-09-21/frozen_grid_manifest.json  grid assertions, observed providers
  results/rq1_rq3_reporting_2026-09-21/rq12_full_precision.json      verified full-precision macro P/R aggregates
  results/rq1_rq3_reporting_2026-09-21/tables/rq3_{dreaddit,goemotions}_latency.csv  verified RQ3 latency summaries
  configs/pub_*.yaml (11 authoritative publication configs)  methods/configuration table

VALUE POLICY
  * Conditional accuracy, effective accuracy, macro-F1, evaluability and all count columns are taken
    VERBATIM from the frozen aggregate_results.csv. They are never recalculated for display.
  * Macro precision and macro recall are absent from the frozen aggregates. They are taken from the
    already-verified rq12_full_precision.json, and independently re-derived here from per_run_results.csv
    (five-run arithmetic mean; sample SD with n-1, the same convention as the frozen aggregation) purely
    as a cross-check. A disagreement above ABORT_TOL stops the run.
  * Latency figures are copied verbatim from the verified RQ3 summaries; nothing is recomputed from raw runs.
  * Formatting is the only transformation: 3 decimals, ROUND_HALF_UP, applied to the stored value.
    CSVs additionally carry the unrounded mean/SD columns.
  * No winner is marked. These tables are descriptive; inference lives in results/inferential_2026-09-21/.

OUTPUTS (this directory only)
  README.md, 01_model_configuration.{csv,md}, 02_dreaddit_results.{csv,md},
  03_goemotions_results.{csv,md}, 04_latency_results.{csv,md}

Deterministic: no wall-clock timestamps, no randomness; re-running reproduces identical bytes.
Python >= 3.9, PyYAML.
"""
import csv, hashlib, json, statistics, sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import yaml

HERE = Path(__file__).resolve().parent
OUT = HERE.parent                       # results/rq1_rq3_tables
RES = OUT.parent                        # results/
PUB = RES.parent                        # evaluation/publication_experiments
DESC = RES / "descriptive_2026-09-21"
REP = RES / "rq1_rq3_reporting_2026-09-21"

# ── integrity gate ──────────────────────────────────────────────────────────────────────────
MANDATORY_SHA256 = {                    # the five frozen descriptive artifacts (hashes supplied by the user)
    DESC / "aggregate_results.csv":     "4242c3634c8939714eb0b7ff25b446783f1747add91c36040a95bf02f1646768",
    DESC / "per_run_results.csv":       "6b3f374a0e76d2c8068c06cc077a2affadd1cd15ac91aab027efeb591efe86ec",
    DESC / "cell_metrics.json":         "fcde951f0190441d0e0d6f31fd2dd03021f4c02d7df07161e403ef6410051221",
    DESC / "frozen_grid_manifest.json": "fba6a4617558b64bec61cee18e2a0b63e9457a03c6a3d94cd8e1a1916527dfa8",
    DESC / "aggregate_five_runs.json":  "96ebe4f0b880d989e796b88a4e8c4be1e7362d89b864c1125afd1c521e70fb91",
}
SUPPORTING_SHA256 = {                   # verified reporting artifacts + authoritative configs
    REP / "rq12_full_precision.json":               "707104a439bc50baa79dd4db1118234c6469ec86059e6bf8cdf79518cceacb17",
    REP / "tables" / "rq3_dreaddit_latency.csv":    "908233ed79e5de25e8dad0b84c6b23162a88efd8e165a2a36a5b578c36ab370c",
    REP / "tables" / "rq3_goemotions_latency.csv":  "535a8b24da59b9f7eb7d52de2c42ab7477d4067f27a0ad4d3e08e8553f86af5e",
    PUB / "configs" / "pub_001_dreaddit_qwen.yaml":                  "d46041d20b27bf8247badc9f819007130fa15ccb53fa8a4617f8b569b3da7016",
    PUB / "configs" / "pub_002_dreaddit_mistral.yaml":               "ec5fa958b2b4b3a67686dc7e62652a45d21f270aebd752e2c5e2f2d704b2c416",
    PUB / "configs" / "pub_003_dreaddit_llama.yaml":                 "6ffca17a5e3e99bcf576f07dbbabc9cfd4f1232d038ef458e9715fa7a22ba143",
    PUB / "configs" / "pub_005_dreaddit_phi.yaml":                   "1c47eacae12abed9ee7b8626c52f451a41cc5e56713955409bb2495525a09bbc",
    PUB / "configs" / "pub_006_goemotions715_mistral.yaml":          "e196b44d030f826ae45c182c8073e576c9d429f225d8c69d802520fa654afda2",
    PUB / "configs" / "pub_007_goemotions715_qwen.yaml":             "cb6fcc23fffd1624d9c7e626a053f06ab2c309659882fdbeef373b5401edbf68",
    PUB / "configs" / "pub_008_goemotions715_phi.yaml":              "297bddd04a1b012715c4c5ff306e139a4b167ff5ea6265b05ec2cd02d3eae2c8",
    PUB / "configs" / "pub_009_goemotions715_llama.yaml":            "0792d3b9b5e5b4a67ee60e885dde5e6be0507ac8a1205be436e300c75e2a6998",
    PUB / "configs" / "pub_011_dreaddit_gemma_coreweave.yaml":       "e08575005359926d962062098c71b7253ca77eadba18d1bc624bf92b6daa6b6b",
    PUB / "configs" / "pub_012_goemotions715_gemma_coreweave.yaml":  "3615dc6229231a82d33d5a54073ed571110fefc0d47308f3e36e16a139575c20",
    PUB / "configs" / "pub_013_dreaddit_gemma_coreweave_osc_run5.yaml": "47f4da0ccf7cfca3427ab90b5bf51468c00d5f1ab0b9f9a031c4556112ef1dbf",
}
ULP_TOL = 5e-16      # last-bit float differences between independently stored copies of the same value
ABORT_TOL = 1e-9     # anything larger is substantive and stops the run

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def abort(msg):
    sys.exit("ABORT (nothing written): " + msg)

hash_report = []
for path, expected in list(MANDATORY_SHA256.items()) + list(SUPPORTING_SHA256.items()):
    if not path.exists():
        abort(f"missing input {path}")
    actual = sha256(path)
    ok = actual == expected
    hash_report.append((str(path.relative_to(PUB)), expected, actual, ok,
                        "mandatory" if path in MANDATORY_SHA256 else "supporting"))
    if not ok:
        abort(f"sha256 mismatch for {path}\n  expected {expected}\n  actual   {actual}")

# ── load frozen inputs ──────────────────────────────────────────────────────────────────────
grid = json.load(open(DESC / "frozen_grid_manifest.json"))
if grid["totals"]["cells"] != 150:            abort(f'frozen grid cells = {grid["totals"]["cells"]}, expected 150')
if grid["totals"]["records"] != 100350:       abort(f'frozen grid records = {grid["totals"]["records"]}, expected 100,350')
if grid["validation"].get("passed") is not True: abort("frozen grid validation.passed is not true")
if grid["validation"].get("n_problems") != 0: abort(f'frozen grid has {grid["validation"]["n_problems"]} validation problems')
if len(grid["cells"]) != 150:                 abort("frozen grid cell list is not 150 entries")

agg_rows = list(csv.DictReader(open(DESC / "aggregate_results.csv")))
if len(agg_rows) != 30: abort(f"aggregate_results.csv has {len(agg_rows)} rows, expected 30")
AGG = {(r["dataset"], r["model"], r["strategy"]): r for r in agg_rows}

agg_json = json.load(open(DESC / "aggregate_five_runs.json"))
if len(agg_json) != 30: abort("aggregate_five_runs.json is not 30 entries")

per_run = list(csv.DictReader(open(DESC / "per_run_results.csv")))
if len(per_run) != 150: abort(f"per_run_results.csv has {len(per_run)} rows, expected 150")

cells = json.load(open(DESC / "cell_metrics.json"))
if len(cells) != 150: abort("cell_metrics.json is not 150 entries")

fullprec = json.load(open(REP / "rq12_full_precision.json"))["aggregates"]
if len(fullprec) != 30: abort("rq12_full_precision.json aggregates is not 30 entries")

# ── cross-checks (recorded, and fatal beyond ABORT_TOL) ─────────────────────────────────────
checks = {"comparisons": 0, "exact": 0, "within_ulp": 0, "max_abs_diff": 0.0, "notes": [], "discrepancies": []}

def cmp_float(where, field, a, b, tol=ULP_TOL):
    checks["comparisons"] += 1
    d = abs(float(a) - float(b))
    checks["max_abs_diff"] = max(checks["max_abs_diff"], d)
    if d == 0.0:
        checks["exact"] += 1
    elif d <= tol:
        checks["within_ulp"] += 1
        checks["discrepancies"].append({"where": where, "field": field, "a": repr(float(a)), "b": repr(float(b)),
                                        "abs_diff": d, "class": "last-bit float"})
    else:
        abort(f"{where} {field}: {a!r} vs {b!r} differ by {d:.3g} (> {tol:g})")

def cmp_int(where, field, a, b):
    checks["comparisons"] += 1
    if int(a) == int(b):
        checks["exact"] += 1
    else:
        abort(f"{where} {field}: {a} vs {b}")

CSV_TO_JSON = {"accuracy_conditional": "accuracy_conditional", "accuracy_effective": "accuracy_effective",
               "macro_f1": "macro_f1", "evaluability": "evaluability"}
FP_KEY = {"accuracy_conditional": "acc_cond", "accuracy_effective": "acc_eff",
          "macro_f1": "macro_f1", "evaluability": "evaluability"}

# per-run aggregation, independent of the frozen aggregation, used only to cross-check
derived = {}
by_cfg = {}
for r in per_run:
    by_cfg.setdefault((r["dataset"], r["model"], r["strategy"]), []).append(r)
for key, rows in by_cfg.items():
    if len(rows) != 5: abort(f"{key} has {len(rows)} runs, expected 5")
    if sorted(int(r["run"]) for r in rows) != [1, 2, 3, 4, 5]: abort(f"{key}: run numbers are not 1..5")
    d = {}
    for field in ("accuracy_conditional", "accuracy_effective", "macro_precision", "macro_recall",
                  "macro_f1", "evaluability"):
        vals = [float(r[field]) for r in rows]
        d[field] = {"mean": sum(vals) / 5.0, "sd": statistics.stdev(vals)}   # sample SD (n-1)
    for field in ("N_total", "N_safety_intercept", "N_valid", "N_model_invalid", "correct",
                  "N_attributable", "N_infra_failed", "N_unaccounted"):
        d["sum_" + field] = sum(int(r[field]) for r in rows)
    derived[key] = d

for key, arow in AGG.items():
    ds, model, strat = key
    jkey = "|".join(key)
    where = jkey
    if int(arow["n_runs"]) != 5: abort(f"{where}: n_runs != 5")
    # (1) aggregate_results.csv vs aggregate_five_runs.json
    for csv_field, jf in CSV_TO_JSON.items():
        cmp_float(where, f"{csv_field}_mean csv-vs-json", arow[csv_field + "_mean"], agg_json[jkey][jf]["mean"])
        cmp_float(where, f"{csv_field}_sd csv-vs-json", arow[csv_field + "_sd"], agg_json[jkey][jf]["sd"])
    # (2) aggregate_results.csv vs rq12_full_precision.json
    fp = fullprec[jkey]
    for csv_field, fpk in FP_KEY.items():
        cmp_float(where, f"{csv_field}_mean csv-vs-fullprec", arow[csv_field + "_mean"], fp[fpk]["mean"]["float"])
        cmp_float(where, f"{csv_field}_sd csv-vs-fullprec", arow[csv_field + "_sd"], fp[fpk]["sd"]["float"])
    for sf, fpf in (("sum_N_total", "sum_N_total"), ("sum_N_safety", "sum_N_safety"), ("sum_N_valid", "sum_N_valid"),
                    ("sum_N_model_invalid", "sum_N_model_invalid"), ("sum_correct", "sum_correct")):
        cmp_int(where, f"{sf} csv-vs-fullprec", arow[sf], fp[fpf])
    # (3) aggregate_results.csv vs an independent five-run aggregation of per_run_results.csv
    dv = derived[key]
    for csv_field in CSV_TO_JSON:
        cmp_float(where, f"{csv_field}_mean csv-vs-per_run", arow[csv_field + "_mean"], dv[csv_field]["mean"], 1e-12)
        cmp_float(where, f"{csv_field}_sd csv-vs-per_run", arow[csv_field + "_sd"], dv[csv_field]["sd"], 1e-12)
    cmp_int(where, "sum_N_total csv-vs-per_run", arow["sum_N_total"], dv["sum_N_total"])
    cmp_int(where, "sum_N_safety csv-vs-per_run", arow["sum_N_safety"], dv["sum_N_safety_intercept"])
    cmp_int(where, "sum_N_valid csv-vs-per_run", arow["sum_N_valid"], dv["sum_N_valid"])
    cmp_int(where, "sum_N_model_invalid csv-vs-per_run", arow["sum_N_model_invalid"], dv["sum_N_model_invalid"])
    cmp_int(where, "sum_correct csv-vs-per_run", arow["sum_correct"], dv["sum_correct"])
    # (4) macro precision / recall: verified full-precision aggregate vs independent per-run aggregation
    for field, fpk in (("macro_precision", "macro_p"), ("macro_recall", "macro_r")):
        cmp_float(where, f"{field}_mean fullprec-vs-per_run", fp[fpk]["mean"]["float"], dv[field]["mean"], 1e-12)
        cmp_float(where, f"{field}_sd fullprec-vs-per_run", fp[fpk]["sd"]["float"], dv[field]["sd"], 1e-12)

# (5) per-cell buckets in cell_metrics.json must agree with per_run_results.csv
for r in per_run:
    cid = f'{r["dataset"]}|{r["model"]}|{r["strategy"]}|run{r["run"]}'
    if cid not in cells: abort(f"cell_metrics.json missing {cid}")
    b = cells[cid]["buckets"]
    cmp_int(cid, "N_total", r["N_total"], b["N_total"])
    cmp_int(cid, "N_safety_intercept", r["N_safety_intercept"], b["N_safety_intercept"])
    cmp_int(cid, "N_valid", r["N_valid"], b["N_successful_valid_predictions"])
    cmp_int(cid, "N_model_invalid", r["N_model_invalid"], b["N_model_behavior_invalid"])
    if cells[cid]["source_run"] != r["source_run"]: abort(f"{cid}: source_run differs between artifacts")

# ── configuration facts, read from the authoritative configs + frozen provenance ─────────────
CONFIGS = {
    "dreaddit":  {"qwen/qwen3.5-27b": ["pub_001_dreaddit_qwen"],
                  "mistralai/mistral-small-2603": ["pub_002_dreaddit_mistral"],
                  "meta-llama/llama-4-scout": ["pub_003_dreaddit_llama"],
                  "microsoft/phi-4": ["pub_005_dreaddit_phi"],
                  "google/gemma-4-31b-it": ["pub_011_dreaddit_gemma_coreweave",
                                            "pub_013_dreaddit_gemma_coreweave_osc_run5"]},
    "goemotions": {"mistralai/mistral-small-2603": ["pub_006_goemotions715_mistral"],
                   "qwen/qwen3.5-27b": ["pub_007_goemotions715_qwen"],
                   "microsoft/phi-4": ["pub_008_goemotions715_phi"],
                   "meta-llama/llama-4-scout": ["pub_009_goemotions715_llama"],
                   "google/gemma-4-31b-it": ["pub_012_goemotions715_gemma_coreweave"]},
}
# Per-model request parameters recorded in the app, quoted from the configs' own documentation.
REQUEST_OVERRIDE = {"qwen/qwen3.5-27b": "reasoning={enabled:false} (documented per-model deviation; not a sampling parameter)"}

cfg_facts = {}
for ds, per_model in CONFIGS.items():
    for mid, cfg_names in per_model.items():
        for name in cfg_names:
            cfg = yaml.safe_load(open(PUB / "configs" / f"{name}.yaml"))
            enabled = [m for m in cfg["models"] if m.get("enabled")]
            if len(enabled) != 1: abort(f"{name}: expected exactly one enabled model, found {len(enabled)}")
            m = enabled[0]
            if m["id"] != mid: abort(f"{name}: enabled model {m['id']} != expected {mid}")
            rec = cfg_facts.setdefault(mid, {"display": m.get("name"), "pins": set(), "quant": set(),
                                             "datasets": set(), "strategies": set(), "runs": set(),
                                             "configs": [], "provider_field": set()})
            if rec["display"] != m.get("name"): abort(f"{mid}: display name differs across configs")
            rec["pins"].add(m.get("pin_provider"))
            rec["quant"].add(m.get("pin_quantization"))
            rec["provider_field"].add(m.get("provider"))
            rec["datasets"].add(cfg["datasets"][0]["name"])
            rec["strategies"].update(cfg["strategies"])
            rec["runs"].add((int(cfg["runs"]), int(cfg.get("run_start", 1))))
            rec["configs"].append(name)
            for k in ("temperature", "max_tokens", "max_completion_tokens", "seed", "top_p", "top_k"):
                if k in cfg: abort(f"{name}: unexpected decoding key {k} present in config")

# providers actually observed in the frozen grid (OK records only), per model
observed = {}
for cid, c in grid["cells"].items():
    mid = cid.split("|")[1]
    for prov, n in c.get("providers_ok", {}).items():
        observed.setdefault(mid, {}).setdefault(prov, 0)
        observed[mid][prov] += n

STRAT_ORDER = ["zero-shot", "zero-shot-cot", "one-shot-cot"]
MODEL_ORDER = sorted(cfg_facts, key=lambda mid: cfg_facts[mid]["display"])

# ── formatting helpers ──────────────────────────────────────────────────────────────────────
def r3(x):
    """3 decimals, ROUND_HALF_UP, applied to the stored value (never to an already-rounded one)."""
    return str(Decimal(repr(float(x))).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))

def pm(mean, sd):
    return f"{r3(mean)} ± {r3(sd)}"

def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)

def write_csv(path, headers, rows):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(headers)
        w.writerows(rows)

# ── table 01: model configuration ───────────────────────────────────────────────────────────
CFG_HEADERS = ["display_name", "model_id", "api_provider_field", "provider_pin_configured",
               "provider_observed_in_frozen_grid", "quantization_directive_configured",
               "datasets_evaluated", "prompt_strategies", "runs_per_strategy_per_dataset",
               "temperature", "max_tokens", "seed", "top_p_top_k",
               "other_request_parameters", "source_configs"]
cfg_rows = []
for mid in MODEL_ORDER:
    rec = cfg_facts[mid]
    if len(rec["pins"]) != 1: abort(f"{mid}: conflicting pin_provider across its authoritative configs: {rec['pins']}")
    quant = {q for q in rec["quant"] if q}
    obs = observed.get(mid, {})
    obs_txt = "; ".join(f"{p} ({n:,} OK records)" for p, n in sorted(obs.items()))
    covered = sorted({i for n, st in rec["runs"] for i in range(st, st + n)})
    if covered != list(range(covered[0], covered[-1] + 1)): abort(f"{mid}: run indices are not contiguous: {covered}")
    runs_txt = f"{len(covered)} runs (runs {covered[0]}\u2013{covered[-1]})"
    cfg_rows.append([
        rec["display"], mid, "; ".join(sorted(x for x in rec["provider_field"] if x)),
        "; ".join(sorted(p for p in rec["pins"] if p)) or "not set",
        obs_txt,
        ("; ".join(sorted(quant)) + " (configured request directive; provider responses do not report quantization)")
        if quant else "none configured",
        "; ".join(sorted(rec["datasets"])),
        "; ".join(s for s in STRAT_ORDER if s in rec["strategies"]),
        runs_txt,
        "Not explicitly set (provider defaults)", "Not explicitly set (provider defaults)",
        "Not explicitly set (provider defaults)", "Not explicitly set (provider defaults)",
        REQUEST_OVERRIDE.get(mid, "none"),
        "; ".join(sorted(set(rec["configs"]))),
    ])
write_csv(OUT / "01_model_configuration.csv", CFG_HEADERS, cfg_rows)

cfg_md_headers = ["Model", "Model ID", "Provider (pinned in config)", "Provider (observed in frozen grid)",
                  "Quantization directive", "Datasets", "Prompt strategies", "Runs per strategy",
                  "Temperature", "Max tokens", "Seed", "Other request parameters"]
cfg_md_rows = [[r[0], f"`{r[1]}`", r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11], r[13]] for r in cfg_rows]
(OUT / "01_model_configuration.md").write_text(f"""# Table 1. Model configuration (AnxioSense publication grid)

All values are read from the authoritative publication configs (`configs/pub_*.yaml`) and from the frozen
grid manifest. Nothing here is inferred from model family or looked up externally.

{md_table(cfg_md_headers, cfg_md_rows)}

Notes.

- Every request is routed through OpenRouter (`provider: openrouter` in each config); the provider column is
  the upstream endpoint pinned with `allow_fallbacks: false`.
- "Provider (observed in frozen grid)" counts the `providers_ok` histogram recorded per cell in
  `frozen_grid_manifest.json`. Each model was served by exactly one upstream provider across all of its
  OK records, and the observed provider matches the configured pin in every case.
- The Gemma `fp4` entry is a **configured request directive**. OpenRouter's response carries the provider but
  not the quantization, so it is enforced by hard failure, not independently observed.
- Temperature, max tokens, max completion tokens, seed, top-p and top-k are **not set** in any publication
  config and are not recorded in any run's provenance; the provider's own defaults applied. The generator
  asserts their absence rather than assuming it.
- Qwen carries the one documented per-model request override (`reasoning={{enabled:false}}`), which the configs
  describe as a reasoning toggle rather than a sampling parameter.
- Gemma on Dreaddit spans two configs: `pub_011` supplies 14 cells and `pub_013` supplies the frozen
  replacement cell `dreaddit|google/gemma-4-31b-it|one-shot-cot|run5` (715 records).
- Context window and knowledge cutoff are deliberately omitted: they are not recorded in the frozen
  publication artifacts.
""")

# ── tables 02 / 03: per-dataset results ─────────────────────────────────────────────────────
RES_HEADERS = ["dataset", "model", "model_id", "prompt_strategy", "n_runs",
               "conditional_accuracy", "conditional_accuracy_mean", "conditional_accuracy_sd",
               "effective_accuracy", "effective_accuracy_mean", "effective_accuracy_sd",
               "macro_precision", "macro_precision_mean", "macro_precision_sd",
               "macro_recall", "macro_recall_mean", "macro_recall_sd",
               "macro_f1", "macro_f1_mean", "macro_f1_sd",
               "evaluability", "evaluability_mean", "evaluability_sd",
               "safety_intercepts_5runs", "model_invalid_outputs_5runs",
               "valid_predictions_5runs", "total_records_5runs", "source_runs"]
MD_HEADERS = ["Model", "Prompt strategy", "Conditional accuracy", "Effective accuracy", "Macro precision",
              "Macro recall", "Macro F1", "Evaluability", "Safety intercepts (5 runs)",
              "Model-invalid outputs (5 runs)"]
DATASET_TITLE = {"dreaddit": "Dreaddit (binary stress vs non-stress; Referral agent)",
                 "goemotions": "GoEmotions (5-class distress taxonomy; Emotion agent)"}

def dataset_rows(ds):
    csv_rows, md_rows = [], []
    for mid in MODEL_ORDER:
        disp = cfg_facts[mid]["display"]
        for strat in STRAT_ORDER:
            a = AGG[(ds, mid, strat)]
            fp = fullprec[f"{ds}|{mid}|{strat}"]
            srcs = sorted({r["source_run"] for r in by_cfg[(ds, mid, strat)]})
            mp, mpsd = fp["macro_p"]["mean"]["float"], fp["macro_p"]["sd"]["float"]
            mr, mrsd = fp["macro_r"]["mean"]["float"], fp["macro_r"]["sd"]["float"]
            ac, acsd = float(a["accuracy_conditional_mean"]), float(a["accuracy_conditional_sd"])
            ae, aesd = float(a["accuracy_effective_mean"]), float(a["accuracy_effective_sd"])
            f1, f1sd = float(a["macro_f1_mean"]), float(a["macro_f1_sd"])
            ev, evsd = float(a["evaluability_mean"]), float(a["evaluability_sd"])
            csv_rows.append([ds, disp, mid, strat, a["n_runs"],
                             pm(ac, acsd), repr(ac), repr(acsd),
                             pm(ae, aesd), repr(ae), repr(aesd),
                             pm(mp, mpsd), repr(mp), repr(mpsd),
                             pm(mr, mrsd), repr(mr), repr(mrsd),
                             pm(f1, f1sd), repr(f1), repr(f1sd),
                             pm(ev, evsd), repr(ev), repr(evsd),
                             a["sum_N_safety"], a["sum_N_model_invalid"], a["sum_N_valid"], a["sum_N_total"],
                             "; ".join(srcs)])
            md_rows.append([disp, strat, pm(ac, acsd), pm(ae, aesd), pm(mp, mpsd), pm(mr, mrsd),
                            pm(f1, f1sd), pm(ev, evsd), a["sum_N_safety"], a["sum_N_model_invalid"]])
    return csv_rows, md_rows

MANI = grid["manifests"]
for idx, ds in (("02", "dreaddit"), ("03", "goemotions")):
    crows, mrows = dataset_rows(ds)
    if len(crows) != 15: abort(f"{ds}: built {len(crows)} rows, expected 15")
    write_csv(OUT / f"{idx}_{ds}_results.csv", RES_HEADERS, crows)
    n_scorable = MANI[ds]["n_scorable"]
    base = MANI[ds]["majority_baseline"]
    safety_per_run = int(AGG[(ds, MODEL_ORDER[0], "zero-shot")]["sum_N_safety"]) // 5
    (OUT / f"{idx}_{ds}_results.md").write_text(f"""# Table {int(idx)}. {DATASET_TITLE[ds]} — five-run results

Descriptive results, 5 runs per configuration, {n_scorable} scoreable items per run
({safety_per_run} safety-intercepted per run, excluded from model attribution by MetricPolicy 1.0.0).
Majority baseline {base}. Values are mean ± SD across the 5 runs, shown to 3 decimals.
No cell is marked as a winner; statistical comparisons are in `results/inferential_2026-09-21/`.

{md_table(MD_HEADERS, mrows)}

Definitions (MetricPolicy 1.0.0, unchanged).

- **Conditional accuracy** = correct / valid predictions.
- **Effective accuracy** = correct / attributable records; a model-invalid output counts as incorrect.
- **Macro precision / recall / F1** = unweighted mean over the fixed label list, computed on valid predictions.
- **Evaluability** = valid / attributable.
- **Safety intercepts** are deterministic pre-LLM interceptions, identical in every cell, excluded from
  model attribution and reported here as the 5-run count.
- **Model-invalid outputs** are records with `failure_class = MODEL_BEHAVIOUR` (unparseable, truncated,
  `{{}}`, refusal or out-of-vocabulary), kept exactly as the frozen parser classified them.

Sources: conditional accuracy, effective accuracy, macro F1, evaluability and all counts are taken verbatim
from `descriptive_2026-09-21/aggregate_results.csv`; macro precision and macro recall from the verified
`rq1_rq3_reporting_2026-09-21/rq12_full_precision.json`, independently re-derived from
`descriptive_2026-09-21/per_run_results.csv` as a cross-check. A displayed 1.000 may hide a small shortfall;
the count columns give the exact numbers.
""")

# ── table 04: RQ3 descriptive latency ───────────────────────────────────────────────────────
LAT_SRC = {"dreaddit": REP / "tables" / "rq3_dreaddit_latency.csv",
           "goemotions": REP / "tables" / "rq3_goemotions_latency.csv"}

# DISPLAY-LABEL NORMALISATION (presentation only).
# The verified RQ3 tables carry their own human-readable labels ("Gemma 4 31B", "Qwen3.5 27B") which differ
# from the display names recorded in the publication configs. Table 4 shows the config display names so that
# all four tables read consistently. This is a label substitution and nothing else: no model ID, no latency
# value, no source_run field and no source artifact is touched, and the verbatim source label is preserved in
# the CSV column `model_source_label`. The mapping is explicit and fail-closed: an unrecognised source label,
# or a model id absent from the configs, aborts the run.
LATENCY_LABEL_TO_MODEL_ID = {
    "Gemma 4 31B":     "google/gemma-4-31b-it",
    "Llama 4 Scout":   "meta-llama/llama-4-scout",
    "Mistral Small 4": "mistralai/mistral-small-2603",
    "Phi-4":           "microsoft/phi-4",
    "Qwen3.5 27B":     "qwen/qwen3.5-27b",
}
for _label, _mid in LATENCY_LABEL_TO_MODEL_ID.items():
    if _mid not in cfg_facts:
        abort(f"latency label {_label!r} maps to {_mid}, which is not in the authoritative configs")

def normalise_latency_label(label):
    mid = LATENCY_LABEL_TO_MODEL_ID.get(label)
    if mid is None:
        abort(f"unrecognised model label {label!r} in an RQ3 latency table; refusing to guess")
    return cfg_facts[mid]["display"], mid

lat_rows, lat_md = [], []
lat_headers = None
for ds in ("dreaddit", "goemotions"):
    rows = list(csv.DictReader(open(LAT_SRC[ds])))
    if len(rows) != 15: abort(f"{ds} latency table has {len(rows)} rows, expected 15")
    if lat_headers is None:
        lat_headers = ["dataset"] + list(rows[0].keys()) + ["model_id", "model_source_label"]
    seen_pairs = set()
    for r in rows:                     # every value except the display label is copied verbatim
        disp, mid = normalise_latency_label(r["model"])
        if r["strategy"] not in STRAT_ORDER: abort(f"{ds} latency: unknown strategy {r['strategy']!r}")
        seen_pairs.add((mid, r["strategy"]))
        out = {**r, "model": disp}
        lat_rows.append([ds] + [out[k] for k in lat_headers[1:-2]] + [mid, r["model"]])
        lat_md.append([ds, disp, r["strategy"], r["client_latency_mean_s"], r["client_latency_median_s"],
                       r["client_latency_p90_s"], r["server_latency_mean_s"], r["n_llm_served_5runs"],
                       r["retried_assessments_5runs"], r["source_run"]])
    expected_pairs = {(mid, st) for mid in MODEL_ORDER for st in STRAT_ORDER}
    if seen_pairs != expected_pairs:
        abort(f"{ds} latency: model x strategy coverage does not match the frozen grid configurations")
write_csv(OUT / "04_latency_results.csv", lat_headers, lat_rows)
(OUT / "04_latency_results.md").write_text(f"""# Table 4. RQ3 — DESCRIPTIVE latency results (no inferential claim)

These are **descriptive** end-to-end latency summaries, copied verbatim from the verified RQ3 artifacts
(`rq1_rq3_reporting_2026-09-21/tables/rq3_dreaddit_latency.csv` and `..._goemotions_latency.csv`). Nothing was
recomputed from raw runs, and no statistical test was run on latency.

{md_table(["Dataset", "Model", "Prompt strategy", "Client mean (s)", "Client median (s)", "Client p90 (s)",
           "Server mean (s)", "n (5 runs)", "Retried assessments (5 runs)", "Source run"], lat_md)}

What these numbers are.

- **Client mean/median/p90** = the runner's wall-clock around the whole HTTP POST to the AnxioSense
  `/api/workflow/evaluate` endpoint, for the terminal attempt of each assessment; mean ± SD over the five
  per-run statistics.
- **Server mean** = the Express-measured duration of the same request.
- Safety-intercepted assessments are excluded (they short-circuit before any agent call) and are counted
  separately in the source tables.

Limitations, preserved from the RQ3 audit.

- Only terminal client-side and server-side request latency exists. There is **no per-agent timing, no phase
  breakdown and no time-to-first-token** in the recorded data.
- Latency is quantised by the server's 3-second poll cadence (99.97% of values lie within 0.5 s of a 3 s
  multiple), so differences smaller than 3 s are at or below the measurement resolution.
- Prompt-strategy blocks were executed **sequentially** within each model, so strategy is confounded with
  time of day, provider load and local state. These numbers do not support a causal claim that any
  prompting strategy is faster.
- Runs were executed on two different machines and across different upstream providers, so cross-model and
  cross-dataset latency comparisons are not controlled.
- Time spent in failed attempts and retry backoff is excluded; the retry count is shown per row.
- Model **display labels** in this table are normalised to the authoritative publication-config display names,
  so that Tables 1\u20134 read consistently: the source tables' "Gemma 4 31B" is shown as "Gemma 4 31B IT" and
  "Qwen3.5 27B" as "Qwen 3.5 27B". This is a presentation-only substitution performed by an explicit,
  fail-closed mapping in the generator. Every other field \u2014 latency values, counts, source runs \u2014 is copied
  verbatim, no model ID was altered, and no source artifact was modified. `04_latency_results.csv` keeps the
  verbatim source label in `model_source_label` and the model ID in `model_id`.
""")

# ── README ──────────────────────────────────────────────────────────────────────────────────
hash_md = md_table(["File", "Role", "Expected sha256", "Verified"],
                   [[f"`{p}`", role, f"`{exp}`", "yes" if ok else "NO"] for p, exp, act, ok, role in hash_report])
disc = checks["discrepancies"]
disc_txt = ("None. Every cross-checked value matched bit-for-bit."
            if not disc else
            f"{len(disc)} of {checks['comparisons']} cross-checked values differed only in the last bits of the "
            f"floating-point representation (largest absolute difference {checks['max_abs_diff']:.3g}); all are "
            f"below the {ULP_TOL:g} tolerance and none changes a 3-decimal displayed value. No substantive "
            f"discrepancy was found.")
(OUT / "README.md").write_text(f"""# RQ1–RQ3 publication tables

Presentation tables for the **already-frozen** AnxioSense RQ1–RQ3 analysis. This folder contains no new
analysis: it renders values that were computed, frozen and independently verified on 2026-09-21.

- **No experiment was rerun** and **no model API was called**.
- **No inferential analysis was changed.** Confidence intervals, permutation tests, McNemar tests and Holm
  corrections live in `results/inferential_2026-09-21/` and are not reproduced or recomputed here.
- **Nothing outside this folder was written.** All inputs are opened read-only and sha256-gated.
- Tables are generated **deterministically** by `code/generate_rq1_rq3_tables.py`: no timestamps, no
  randomness, identical bytes on every run.
- **RQ4** (expert Likert ratings and Cohen's kappa) is a separate evaluation and is **not** included here.

## Files

| File | Contents |
|---|---|
| `01_model_configuration.csv` / `.md` | Model, provider pin, observed provider, quantization directive, datasets, strategies, runs, decoding parameters |
| `02_dreaddit_results.csv` / `.md` | Dreaddit, 15 rows (5 models × 3 prompting strategies) |
| `03_goemotions_results.csv` / `.md` | GoEmotions, 15 rows |
| `04_latency_results.csv` / `.md` | RQ3 descriptive latency, 30 rows (both datasets) |
| `code/generate_rq1_rq3_tables.py` | The generator |

The `.md` files are the publication-ready renderings (3 decimals, mean ± SD). The `.csv` files carry the same
rendered strings **and** the unrounded mean/SD columns for reproducibility.

## Frozen inputs and hash verification

The generator aborts before writing anything if any hash differs.

{hash_md}

## Grid assertions checked at generation time

- 150 cells — pass
- 100,350 records — pass
- `validation.passed = true` — pass
- 0 validation problems — pass
- `aggregate_results.csv` has 30 configuration rows; `per_run_results.csv` has 150 cell rows; each
  configuration has exactly runs 1–5.

Frozen grid timestamp: `{grid["frozen_utc"]}` · parser `{grid["parser_version"]}` · metric policy
`{grid["metric_policy_version"]}`.

## Value policy

- Conditional accuracy, effective accuracy, macro F1, evaluability and all counts are taken **verbatim** from
  the frozen `aggregate_results.csv`. They were not recalculated for display.
- Macro precision and macro recall are not present in the frozen aggregates. They are taken from the verified
  full-precision aggregates in `rq1_rq3_reporting_2026-09-21/rq12_full_precision.json`, and independently
  re-derived here from `per_run_results.csv` (five-run arithmetic mean, sample SD with n−1 — the same
  convention as the frozen aggregation) as a cross-check only.
- Latency values are copied verbatim from the verified RQ3 summary tables. Raw runs were not re-read.
- Formatting is the only transformation applied: 3 decimals, ROUND_HALF_UP, applied to the stored value.
- No winner is marked and no ranking is implied. These tables are descriptive.

## Cross-checks performed before writing

{checks["comparisons"]:,} comparisons across four independent copies of the same quantities
(`aggregate_results.csv`, `aggregate_five_runs.json`, `rq12_full_precision.json`, and a fresh aggregation of
`per_run_results.csv`), plus per-cell bucket agreement between `per_run_results.csv` and `cell_metrics.json`.

{disc_txt}

One cosmetic cross-artifact difference is normalised at render time. The verified RQ3 latency tables label
the models "Gemma 4 31B" and "Qwen3.5 27B", while the publication configs record "Gemma 4 31B IT" and
"Qwen 3.5 27B". Table 4 displays the config display names so that all four tables read consistently. This is a
**display-label substitution only**, applied by an explicit fail-closed mapping in the generator (an
unrecognised label aborts the run): no latency value, count, source-run field or model ID is changed, and no
source artifact is touched. `04_latency_results.csv` additionally carries `model_id` and the verbatim
`model_source_label` from the source tables, so the substitution is fully traceable.

## Reproducing

```bash
cd evaluation/publication_experiments/results/rq1_rq3_tables
python3 code/generate_rq1_rq3_tables.py
```

Requires Python ≥ 3.9 and PyYAML. The script writes only into this directory.
""")

print(json.dumps({"hash_checks": len(hash_report), "all_hashes_ok": all(h[3] for h in hash_report),
                  "cross_check_comparisons": checks["comparisons"], "exact": checks["exact"],
                  "last_bit_float": checks["within_ulp"], "max_abs_diff": checks["max_abs_diff"],
                  "files_written": sorted(str(p.relative_to(OUT)) for p in OUT.rglob("*") if p.is_file())},
                 indent=1))
