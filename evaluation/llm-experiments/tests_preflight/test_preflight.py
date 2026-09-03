#!/usr/bin/env python3
"""AnxioSense RQ1-RQ3 pre-flight gate tests.

Run:  python3 evaluation/llm-experiments/tests_preflight/test_preflight.py
Offline: no API keys, no network, no sklearn, no pytest.

CONTRACT tests  = properties the pipeline must satisfy before new data is collected.
EVIDENCE tests  = checks over the existing stage_c_recovered tree.
"""
from __future__ import annotations
import csv, glob, hashlib, json, os, re, sys, unittest, collections

csv.field_size_limit(10 ** 7)
HERE = os.path.dirname(os.path.abspath(__file__))
LLMEXP = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(LLMEXP, "..", ".."))
sys.path.insert(0, LLMEXP)
sys.path.insert(0, HERE)

from referral_risk_parser_port import extract_risk_level, risk_to_dreaddit_label
from src.label_mapping import (map_dreaddit_label, map_goemotions_label,
                               GOEMOTIONS_TO_ANXIOSENSE, EVAL_CLASSES, LabelMappingError)
from src.report_parser import extract_stress_label
from src.config import load_config

CONFIG = os.path.join(LLMEXP, "config", "experiment_config.yaml")
FROZEN = os.path.join(ROOT, "evaluation", "datasets", "frozen_2026-09-01")
RECOVERED = os.path.join(LLMEXP, "outputs", "stage_c_recovered", "raw")
WORKFLOW_TS = os.path.join(ROOT, "src", "mastra", "workflows",
                           "anxiety-screening-assessment-workflow.ts")
LOADER_TS = os.path.join(ROOT, "src", "mastra", "utils", "prompt-strategy-loader.ts")
RUNNER = os.path.join(LLMEXP, "scripts", "run_experiments.py")
STORE = os.path.join(LLMEXP, "src", "result_store.py")

PANEL = ("meta-llama/llama-4-scout", "mistralai/mistral-small-2603",
         "google/gemma-4-31b-it", "microsoft/phi-4", "qwen/qwen3.5-27b")


def read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def dreaddit_records():
    for f in sorted(glob.glob(os.path.join(RECOVERED, "dreaddit_*.jsonl"))):
        model = os.path.basename(f).split("_", 1)[1].rsplit("_", 2)[0]
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                yield os.path.basename(f), model, json.loads(line)


# ══════════════════════════════════════════════════════════════════════════
class T1_DatasetIntegrity(unittest.TestCase):
    """CONTRACT — the frozen snapshot still describes the data on disk."""

    def test_frozen_manifest_present(self):
        self.assertTrue(os.path.exists(os.path.join(FROZEN, "MANIFEST.json")),
                        "frozen snapshot missing — run freeze/verify_frozen.py first")

    def test_no_drift_since_freeze(self):
        import subprocess
        r = subprocess.run([sys.executable, os.path.join(FROZEN, "verify_frozen.py")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, f"dataset drift detected:\n{r.stdout}\n{r.stderr}")

    def test_test_split_ids_unique_and_nonempty(self):
        man = json.load(open(os.path.join(FROZEN, "MANIFEST.json"), encoding="utf-8"))
        for name, d in man["datasets"].items():
            with self.subTest(dataset=name):
                ids = read(os.path.join(FROZEN, f"{name}_test_ids.txt")).split()
                self.assertEqual(len(ids), len(set(ids)), "duplicate sample_id in test split")
                self.assertEqual(len(ids), d["test_rows"])
                self.assertEqual(d["duplicate_sample_ids"], 0)

    def test_short_rows_are_documented_not_deleted(self):
        """The 29 sub-10-character GoEmotions rows must be listed, not removed."""
        with open(os.path.join(FROZEN, "exclusions.csv"), encoding="utf-8") as fh:
            excl = list(csv.DictReader(fh))
        short = [r for r in excl if "below_min_length_gate" in r["reasons"]]
        self.assertEqual(len(short), 29)
        self.assertTrue(all(r["excluded_from_dispatch"] == "yes" for r in short))
        ids = set(read(os.path.join(FROZEN, "goemotions_test_ids.txt")).split())
        for r in short:
            self.assertIn(r["sample_id"], ids, "short row was deleted from the test split")


# ══════════════════════════════════════════════════════════════════════════
class T2_GroundTruth(unittest.TestCase):
    """CONTRACT — ground truth is total, deterministic and prediction-independent."""

    def test_dreaddit_mapping(self):
        for raw, exp in ((0, 0), (1, 1), ("0", 0), ("1", 1)):
            self.assertEqual(map_dreaddit_label(raw), exp)
        for bad in ("2", "yes", "", None, "moderate"):
            with self.assertRaises(LabelMappingError):
                map_dreaddit_label(bad)

    def test_goemotions_mapping_is_closed(self):
        self.assertEqual(set(GOEMOTIONS_TO_ANXIOSENSE.values()) <= set(EVAL_CLASSES), True)
        self.assertEqual(map_goemotions_label("['nervousness']"), "anxiety")
        self.assertEqual(map_goemotions_label("['grief']"), "sadness")
        self.assertEqual(map_goemotions_label("['neutral']"), "non_distress")
        with self.assertRaises(LabelMappingError):
            map_goemotions_label("['excitement']")

    def test_mapping_total_over_every_test_row(self):
        for name, col, fn in (("dreaddit", "label", map_dreaddit_label),
                              ("goemotions", "emotion_names", map_goemotions_label)):
            path = os.path.join(ROOT, "evaluation", "datasets", "processed", f"{name}_clean.csv")
            with open(path, newline="", encoding="utf-8") as fh:
                rows = [r for r in csv.DictReader(fh) if r["split"] == "test"]
            errs = []
            for r in rows:
                try: fn(r[col])
                except LabelMappingError as e: errs.append((r["sample_id"], str(e)[:60]))
            with self.subTest(dataset=name):
                self.assertEqual(errs, [], f"{len(errs)} unmappable label(s)")

    def test_ground_truth_never_derived_from_model_output(self):
        """get_ground_truth must take only the dataset row, and the record's
        ground_truth field must be assigned from it alone."""
        src = read(RUNNER)
        m = re.search(r"def get_ground_truth\(([^)]*)\)", src)
        self.assertIsNotNone(m)
        params = m.group(1)
        for forbidden in ("result", "report", "response", "prediction", "label="):
            self.assertNotIn(forbidden, params,
                             f"get_ground_truth signature references model output: {params}")
        assigns = re.findall(r'"ground_truth":\s*([A-Za-z_][A-Za-z0-9_]*)', src)
        self.assertTrue(assigns, "no ground_truth assignment found")
        for a in assigns:
            self.assertEqual(a, "ground_truth", f'ground_truth assigned from {a!r}')

    def test_ground_truth_computed_before_the_api_call(self):
        src = read(RUNNER)
        gt = src.index("ground_truth = get_ground_truth")
        call = src.index("result = call_anxiosense")
        self.assertLess(gt, call, "ground truth is computed after the model call")


# ══════════════════════════════════════════════════════════════════════════
class T3_ReferralExtraction(unittest.TestCase):
    """CONTRACT — the risk-level ladder recovers, never invents."""

    GOOD = [
        ('{"risk_level":"low"}', "low"),
        ('{"risk_level":"moderate"}', "moderate"),
        ('{"risk_level":"urgent"}', "urgent"),
        ('{"risk_level":"  URGENT  "}', "urgent"),                 # weird capitalisation + padding
        ('```json\n{"risk_level": "Low"}\n```', "low"),            # markdown fence
        ('```\n{"risk_level":"moderate"}\n```', "moderate"),
        ('Step 1 - read.\nStep 6 - return:\n{"risk_level":"low","reasoning":"x"}', "low"),  # CoT prose
        ('{"risk_level":"urgent","reasoning":"contains { and } braces"}', "urgent"),        # braces in string
        ('{"risk_level":"low","reasoning":"he said \\"fine\\""}', "low"),                   # escaped quotes
        ('prefix {"a":{"b":1}} then {"risk_level":"moderate"}', None),                      # first object wins, has no key
    ]
    BAD = [
        '{"risk_level":"elevated"}', '{"risk_level":"high"}', '{"risk_level":"severe"}',
        '{"risk_level":"medium"}', '{"riskLevel":"low"}', '{"risk":"low"}',
        '{"risk_level":123}', '{"risk_level":null}', '{"risk_level":["low"]}',
        '{"risk_level":"low"', '{"risk_level":', '{', '', '   ',
        'The risk level is low.', 'risk_level: low',
        '{"risk_level":"low","reasoning\\":\\"broken escaping\\"}',  # the real Qwen failure mode
        None, 123, [],
    ]

    def test_valid_forms_recovered(self):
        for raw, exp in self.GOOD:
            with self.subTest(raw=str(raw)[:50]):
                self.assertEqual(extract_risk_level(raw), exp)

    def test_unreadable_forms_return_none_never_moderate(self):
        for raw in self.BAD:
            with self.subTest(raw=str(raw)[:50]):
                got = extract_risk_level(raw)
                self.assertIsNone(got, f"expected None, got {got!r}")
                self.assertNotEqual(got, "moderate", "unreadable response became 'moderate'")

    def test_label_mapping_from_risk_level(self):
        self.assertEqual(risk_to_dreaddit_label("low"), 0)
        self.assertEqual(risk_to_dreaddit_label("moderate"), 1)
        self.assertEqual(risk_to_dreaddit_label("urgent"), 1)
        self.assertIsNone(risk_to_dreaddit_label(None))

    def test_report_parser_referral_level_mapping(self):
        self.assertEqual(extract_stress_label({"report": {"referralLevel": "low"}}), 0)
        self.assertEqual(extract_stress_label({"report": {"referralLevel": "moderate"}}), 1)
        self.assertEqual(extract_stress_label({"report": {"referralLevel": "urgent"}}), 1)
        for bad in ({"report": {"referralLevel": "elevated"}}, {"report": {}}, {}):
            self.assertIsNone(extract_stress_label(bad))


# ══════════════════════════════════════════════════════════════════════════
class T4_NoModerateDefault(unittest.TestCase):
    """CONTRACT + EVIDENCE — an unreadable referral response must never score as 'moderate'."""

    def test_workflow_has_no_moderate_default(self):
        src = read(WORKFLOW_TS)
        self.assertNotRegex(
            src, r"let\s+riskLevel\s*:\s*RiskLevel\s*=\s*'moderate'",
            "workflow still initialises riskLevel to 'moderate'; an unreadable referral "
            "response will be scored as moderate (label 1) instead of failing")

    def test_evidence_no_record_scores_an_unreadable_response(self):
        offenders = []
        for fname, model, r in dreaddit_records():
            if r.get("safety_intercept") or r.get("api_error"): continue
            raw = r.get("referral_agent_raw")
            if not raw: continue
            if extract_risk_level(raw) is None and r.get("label") is not None:
                offenders.append((fname, r["sample_id"], model,
                                  r.get("referral_level"), r.get("label"),
                                  bool(r.get("referral_risk_fallback_used"))))
        fb = [o for o in offenders if o[5]]
        by_model = collections.Counter(o[2] for o in offenders)
        self.assertEqual(
            len(offenders), 0,
            f"{len(offenders)} record(s) carry a scoreable label derived from a referral "
            f"response the parser cannot read; {len(fb)} of them are the 'moderate' fallback.\n"
            f"    by model: {dict(by_model)}\n"
            f"    examples: {offenders[:3]}")


# ══════════════════════════════════════════════════════════════════════════
class T5_RecoveryReproducible(unittest.TestCase):
    """EVIDENCE — the historical Dreaddit labels regenerate from the saved raw responses."""

    def test_recovered_labels_regenerate(self):
        checked = mism = 0
        examples = []
        for fname, model, r in dreaddit_records():
            if r.get("safety_intercept") or r.get("api_error"): continue
            raw = r.get("referral_agent_raw")
            if not raw: continue
            lvl = extract_risk_level(raw)
            if lvl is None: continue          # covered by T4
            checked += 1
            if risk_to_dreaddit_label(lvl) != r.get("label"):
                mism += 1
                if len(examples) < 5:
                    examples.append((fname, r["sample_id"], lvl, r.get("referral_level"), r.get("label")))
        self.assertGreater(checked, 5000, "too few records re-derived to be meaningful")
        self.assertEqual(mism, 0, f"{mism}/{checked} re-derived labels differ. {examples}")

    def test_recovered_level_matches_stored_level(self):
        bad = 0
        for _f, _m, r in dreaddit_records():
            if r.get("safety_intercept") or r.get("api_error"): continue
            raw = r.get("referral_agent_raw")
            if not raw: continue
            lvl = extract_risk_level(raw)
            if lvl is None: continue
            if lvl != (r.get("referral_level") or "").strip().lower(): bad += 1
        self.assertEqual(bad, 0, f"{bad} records where the re-derived level differs from the stored level")


# ══════════════════════════════════════════════════════════════════════════
class T6_ModelSelection(unittest.TestCase):
    """CONTRACT — only the five panel models can be selected; DeepSeek cannot."""

    def setUp(self): self.cfg = load_config(CONFIG)

    def test_config_declares_only_the_panel(self):
        ids = [m.id for m in self.cfg.models]
        extra = [i for i in ids if i not in PANEL]
        self.assertEqual(extra, [], f"non-panel model(s) selectable from config: {extra}")

    def test_default_selection_excludes_deepseek(self):
        """Reproduces run_experiments.py's selection with --model absent."""
        selected = [m.id for m in self.cfg.models]          # args.model is None -> all models
        self.assertNotIn("deepseek/deepseek-v4-flash", selected,
                         "a bare run would dispatch DeepSeek: it is disabled only by a YAML comment")

    def test_runner_has_an_enabled_filter(self):
        src = read(RUNNER)
        self.assertRegex(src, r"getattr\(m,\s*['\"]enabled['\"]|m\.enabled|\benabled\b.*cfg\.models",
                         "run_experiments.py has no 'enabled' filter — a commented-out model still runs")


# ══════════════════════════════════════════════════════════════════════════
class T7_PromptProvenance(unittest.TestCase):
    """CONTRACT — every record must prove which prompt text was actually used."""

    STRATEGIES = ("zero-shot", "zero-shot-cot", "one-shot-cot")
    AGENTS = ("emotion", "symptom", "context", "referral", "report")

    def test_all_strategy_files_exist_and_are_distinct(self):
        for agent in self.AGENTS:
            texts = {}
            for s in self.STRATEGIES:
                p = os.path.join(ROOT, "prompts", agent, f"{s}.md")
                with self.subTest(agent=agent, strategy=s):
                    self.assertTrue(os.path.exists(p), f"missing prompt file {p}")
                texts[s] = read(p)
            self.assertEqual(len(set(texts.values())), 3,
                             f"prompts/{agent}: two strategies have identical text")

    def test_prompt_loader_failure_is_not_swallowed(self):
        """A prompt that cannot be loaded must abort the assessment, not fall back
        to the agent's hardcoded instructions."""
        wf = read(WORKFLOW_TS)
        swallowed = re.findall(r"loadAgentInstructions\([^)]*\)\s*\?\?\s*undefined", wf)
        self.assertEqual(
            swallowed, [],
            f"{len(swallowed)} call site(s) do `loadAgentInstructions(...) ?? undefined`: "
            "when the prompt file cannot be read the agent silently uses its hardcoded "
            "instructions and the requested strategy is NOT applied. Nothing in the result "
            "record shows this happened.")

    def test_records_carry_a_prompt_hash(self):
        f = sorted(glob.glob(os.path.join(RECOVERED, "*.jsonl")))[0]
        with open(f, encoding="utf-8") as fh:
            rec = json.loads(fh.readline())
        self.assertTrue(
            any(k in rec for k in ("prompt_sha256", "prompt_hash", "prompt_version")),
            f"no prompt hash in record schema ({len(rec)} fields) — a record cannot prove "
            f"which prompt text produced it")

    def test_records_carry_requested_and_actual_strategy(self):
        f = sorted(glob.glob(os.path.join(RECOVERED, "*.jsonl")))[0]
        with open(f, encoding="utf-8") as fh:
            rec = json.loads(fh.readline())
        self.assertIn("strategy", rec)
        self.assertIn("strategy_actual", rec)


# ══════════════════════════════════════════════════════════════════════════
class T8_ProviderRouting(unittest.TestCase):
    """CONTRACT + EVIDENCE — the model and provider that ran must be recorded and pinned."""

    def test_records_identify_model_and_provider(self):
        for f in sorted(glob.glob(os.path.join(RECOVERED, "*.jsonl")))[:3]:
            with open(f, encoding="utf-8") as fh:
                rec = json.loads(fh.readline())
            for k in ("model_id", "model_actual", "upstream_provider"):
                self.assertIn(k, rec, f"{os.path.basename(f)} record lacks {k}")

    def test_evidence_pin_held_on_every_served_request(self):
        PIN = {"meta-llama_llama-4-scout": "DeepInfra", "microsoft_phi-4": "DeepInfra",
               "google_gemma-4-31b-it": "DeepInfra", "mistralai_mistral-small-2603": "Mistral",
               "qwen_qwen3.5-27b": "Alibaba"}
        bad = collections.Counter()
        for f in sorted(glob.glob(os.path.join(RECOVERED, "*.jsonl"))):
            model = os.path.basename(f).split("_", 1)[1].rsplit("_", 2)[0]
            if model not in PIN: continue
            with open(f, encoding="utf-8") as fh:
                lines = fh.readlines()
            for line in lines:
                r = json.loads(line)
                if r.get("api_error") or r.get("safety_intercept"): continue
                up = r.get("upstream_provider")
                if up is not None and up != PIN[model]: bad[(model, up)] += 1
        self.assertEqual(dict(bad), {}, f"upstream provider differed from the pin: {dict(bad)}")

    def test_evidence_no_groq_or_unevaluated_model_served_a_record(self):
        bad = collections.Counter()
        for f in sorted(glob.glob(os.path.join(RECOVERED, "*.jsonl"))):
            with open(f, encoding="utf-8") as fh:
                lines = fh.readlines()
            for line in lines:
                r = json.loads(line)
                actual = (r.get("model_actual") or "")
                if "groq" in actual.lower() or "llama-3.3" in actual.lower():
                    bad[actual] += 1
        self.assertEqual(dict(bad), {}, f"records served by an unevaluated default model: {dict(bad)}")

    def test_env_defaults_cannot_silently_substitute_a_model(self):
        src = read(os.path.join(ROOT, "src", "mastra", "utils", "model-provider.ts"))
        self.assertNotRegex(
            src, r"process\.env\.MODEL_(PROVIDER|ID)\s*\?\?\s*'",
            "model-provider.ts falls back to a hardcoded provider/model when the env var "
            "is unset; an unevaluated model can run silently")


# ══════════════════════════════════════════════════════════════════════════
class T9_FailureAndResume(unittest.TestCase):
    """CONTRACT — failures are retried, and a stored failure is never treated as done."""

    def test_runner_implements_retry(self):
        src = read(RUNNER)
        self.assertRegex(src, r"(max_attempts|for\s+attempt\s+in|@retry|tenacity)",
                         "run_experiments.py has no client-side retry; the retry: block in "
                         "experiment_config.yaml is parsed and never used")

    def test_resume_retries_a_failed_record(self):
        src = read(STORE)
        self.assertRegex(
            src, r"prediction_valid|include_in_primary_metrics|failure_reason",
            "ResultStore.is_completed keys only on (sample_id, model, strategy, run), so a "
            "stored FAILED record counts as completed and --resume will never retry it")

    def test_client_timeout_not_shorter_than_server_poll_budget(self):
        cfg = load_config(CONFIG)
        ts = read(os.path.join(ROOT, "server", "src", "routes", "workflow.ts"))
        m = re.search(r"maxMs\s*=\s*([0-9_]+)", ts)
        self.assertIsNotNone(m)
        server_budget = int(m.group(1).replace("_", "")) / 1000
        self.assertGreaterEqual(
            cfg.server.timeout_seconds, server_budget,
            f"client gives up after {cfg.server.timeout_seconds}s but the server keeps working "
            f"for up to {server_budget:.0f}s — abandoned runs are still billed")

    def test_a_failed_record_is_never_scoreable(self):
        bad = 0
        for _f, _m, r in dreaddit_records():
            if (r.get("api_error") or r.get("failure_reason")) and r.get("label") is not None:
                bad += 1
        self.assertEqual(bad, 0, f"{bad} record(s) carry both a failure and a scoreable label")


# ══════════════════════════════════════════════════════════════════════════
class T10_DuplicateDetection(unittest.TestCase):
    """CONTRACT + EVIDENCE — duplicate samples and duplicate runs must be detected."""

    def test_evidence_no_duplicate_sample_within_a_cell(self):
        bad = {}
        for f in sorted(glob.glob(os.path.join(RECOVERED, "*.jsonl"))):
            with open(f, encoding="utf-8") as fh:
                ids = [json.loads(l)["sample_id"] for l in fh]
            if len(ids) != len(set(ids)):
                bad[os.path.basename(f)] = len(ids) - len(set(ids))
        self.assertEqual(bad, {}, f"duplicate sample_id inside a cell file: {bad}")

    def test_evidence_no_duplicate_run_content(self):
        """Two runs of the same cell must not be byte-identical prediction vectors."""
        cells = collections.defaultdict(dict)
        for f in sorted(glob.glob(os.path.join(RECOVERED, "*.jsonl"))):
            b = os.path.basename(f)
            m = re.match(r"(dreaddit|goemotions)_(.+?)_((?:zero|one)-shot(?:-cot)?)_run(\d)\.jsonl", b)
            if not m: continue
            with open(f, encoding="utf-8") as fh:
                rows = sorted((json.loads(l) for l in fh), key=lambda r: r["sample_id"])
            cells[(m.group(1), m.group(2), m.group(3))][int(m.group(4))] = \
                hashlib.sha256(json.dumps([r.get("label") for r in rows]).encode()).hexdigest()
        identical = {}
        for k, runs in cells.items():
            h = collections.Counter(runs.values())
            dup = sum(c - 1 for c in h.values() if c > 1)
            if dup: identical["|".join(k)] = dup
        self.assertEqual(
            sum(identical.values()), 0,
            f"{sum(identical.values())} duplicate run vector(s) across {len(identical)} cell(s) "
            f"— those repeated runs carry no additional information.\n"
            f"    worst: {sorted(identical.items(), key=lambda kv: -kv[1])[:5]}")

    def test_runner_refuses_to_append_to_an_existing_cell(self):
        src = read(RUNNER)
        self.assertRegex(
            src, r"sys\.exit\(1\)[^\n]*\n[^\n]*already exists|already exists[\s\S]{0,400}?sys\.exit\(1\)",
            "re-running a cell without --resume only logs a WARNING and then APPENDS, "
            "silently duplicating records")


if __name__ == "__main__":
    unittest.main(verbosity=2, buffer=False)
