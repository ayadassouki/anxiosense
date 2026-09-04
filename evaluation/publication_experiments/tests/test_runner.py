#!/usr/bin/env python3
"""Offline gate tests for the publication runner. No network, no paid model, no sklearn.

Run:  python3 evaluation/publication_experiments/tests/test_runner.py
"""
from __future__ import annotations
import contextlib, csv, hashlib, inspect, io, json, os, subprocess, sys, tempfile, unittest
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG_ROOT = HERE.parent
sys.path.insert(0, str(PKG_ROOT))

from runner import RUNNER_VERSION                                  # noqa: E402
from runner._reuse import REPO_ROOT, LabelMappingError             # noqa: E402
from runner.client import TransportResult                          # noqa: E402
from runner.config import (load_config, ConfigError,               # noqa: E402
                           RUN_CLASSES, DEFAULT_RUN_CLASS, HASH_COMPAT_DEFAULTS)
from runner.failures import Transport, classify_transport, is_retryable  # noqa: E402
from runner.identity import (new_uuid, sha256_text, prompt_hashes,
                             prompt_inventory, PromptError, AGENTS,
                             git_dirty, git_untracked_count)  # noqa: E402
from runner.manifest import build_manifest, verify_manifest, ManifestError  # noqa: E402
from runner.metrics import cell_metrics, MetricPolicy              # noqa: E402
from runner.mock import MockTransport, FIXTURES                    # noqa: E402
from runner.parse import parse_dreaddit, parse_goemotions          # noqa: E402
from runner.rescore import rescore                                 # noqa: E402
from runner.retry import RetryPolicy, next_action                  # noqa: E402
from runner.run import (preflight, run_experiment, PreflightError,   # noqa: E402
                        resolve_server_runtime)
from runner.run import main as run_main                            # noqa: E402
from runner.goemotions_mapping import (                            # noqa: E402
    LABEL_MAP, GOEMOTIONS_LABELS, EKMAN_GROUPING, SENTIMENT_GROUPING,
    EVAL_CLASSES as GE_EVAL_CLASSES, OUT_OF_TAXONOMY, MAPPING_VERSION,
    map_goemotions_labels, anxiosense_class, MappingDataError, UnscorableRow,
    UNSCORABLE_CONFLICT, UNSCORABLE_OUT_OF_TAXONOMY, mapping_provenance)
from runner.store import RunStore, DuplicateAssessment             # noqa: E402

OK = Transport.OK


# ── fixtures ─────────────────────────────────────────────────────────────────

def body_from(name: str) -> dict:
    return FIXTURES[name]().body


def write_csv(path: Path, rows: list[dict], cols: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def tiny_dreaddit(tmp: Path, n: int = 3, bad_label: bool = False) -> Path:
    p = tmp / "dreaddit_clean.csv"
    rows = []
    for i in range(n):
        rows.append({
            "sample_id": f"dread_{i:06d}", "split": "test",
            "text": f"I have been feeling very anxious about everything lately, item {i}.",
            "text_redacted": f"I have been feeling very anxious about everything lately, item {i}.",
            "label": ("banana" if (bad_label and i == 1) else str(i % 2)),
        })
    write_csv(p, rows, ["sample_id", "split", "text", "text_redacted", "label"])
    return p


def tiny_goemotions(tmp: Path, n: int = 3) -> Path:
    p = tmp / "goemotions_clean.csv"
    # label_names holds the RAW official GoEmotions labels, pipe-separated.
    # The frozen v1.0.0 mapping consumes this, not the old filtered
    # emotion_names column.
    emo = ["nervousness", "neutral", "sadness"]
    rows = [{"sample_id": f"ge_{i:06d}", "split": "test",
             "text": f"a comment number {i} that is long enough",
             "text_redacted": f"a comment number {i} that is long enough",
             "label_names": emo[i % 3]} for i in range(n)]
    write_csv(p, rows, ["sample_id", "split", "text", "text_redacted", "label_names"])
    return p


def make_config(tmp: Path, manifest_path: Path, dataset: str, *,
                experiment_id="t", runs=1, models=None) -> Path:
    models = models or [{"id": "microsoft/phi-4", "name": "Phi-4",
                         "provider": "openrouter", "enabled": True}]
    cfg = {
        "experiment_id": experiment_id,
        "output_root": str(tmp / "runs"),
        "models": models,
        "strategies": ["zero-shot"],
        "datasets": [{"name": dataset, "manifest": str(manifest_path)}],
        "runs": runs, "run_start": 1,
        "retry": {"max_attempts": 3, "backoff_base_ms": 1, "backoff_factor": 2},
        "server": {"base_url": "http://localhost:3001", "timeout_seconds": 180,
                   "server_poll_budget_seconds": 150},
    }
    import yaml
    p = tmp / "config.yaml"
    p.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return p


def build_and_save(tmp: Path, dataset: str, csv_path: Path) -> Path:
    m = build_manifest(dataset=dataset, processed_csv=str(csv_path), split="test",
                       text_column="text_redacted", min_chars=10)
    p = tmp / f"{dataset}_manifest.json"
    p.write_text(json.dumps(m, indent=2), encoding="utf-8")
    return p


# ── 1. ground truth ──────────────────────────────────────────────────────────

class T01_GroundTruth(unittest.TestCase):
    def test_manifest_computes_ground_truth_from_the_row(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            m = build_manifest(dataset="dreaddit", processed_csv=str(tiny_dreaddit(tmp)),
                               split="test", text_column="text_redacted", min_chars=10)
            self.assertEqual(m["ground_truth"], {"dread_000000": 0, "dread_000001": 1,
                                                 "dread_000002": 0})
            self.assertEqual(m["majority_baseline"], round(2 / 3, 6))

    def test_ground_truth_failure_aborts_before_dispatch(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            with self.assertRaises(ManifestError) as ctx:
                build_manifest(dataset="dreaddit",
                               processed_csv=str(tiny_dreaddit(tmp, bad_label=True)),
                               split="test", text_column="text_redacted", min_chars=10)
            self.assertIn("ground-truth mapping failure", str(ctx.exception))

    def test_no_dispatch_happens_when_ground_truth_fails(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            csvp = tiny_dreaddit(tmp, bad_label=True)
            transport = MockTransport({})
            with self.assertRaises(ManifestError):
                build_manifest(dataset="dreaddit", processed_csv=str(csvp), split="test",
                               text_column="text_redacted", min_chars=10)
            self.assertEqual(transport.calls, [], "a model was called despite a bad label")

    def test_parsers_cannot_see_ground_truth(self):
        for fn in (parse_dreaddit, parse_goemotions, classify_transport):
            params = set(inspect.signature(fn).parameters)
            for forbidden in ("ground_truth", "gt", "label", "y_true"):
                self.assertNotIn(forbidden, params,
                                 f"{fn.__name__} can see ground truth: {params}")


# ── 2-4. Dreaddit parsing ────────────────────────────────────────────────────

class T02_DreadditParsing(unittest.TestCase):
    def test_valid_prediction(self):
        p = parse_dreaddit(body_from("valid_prediction"), OK)
        self.assertEqual((p.parse_status, p.parsed_prediction, p.prediction_valid), ("ok", 1, True))
        self.assertTrue(p.include_in_metrics)

    def test_low_maps_to_zero(self):
        p = parse_dreaddit(body_from("valid_empty_emotions"), OK)
        self.assertEqual(p.parsed_prediction, 0)

    def test_missing_referral_level_is_invalid_not_moderate(self):
        p = parse_dreaddit(body_from("referral_unreadable"), OK)
        self.assertEqual(p.parse_status, "unparseable")
        self.assertIsNone(p.parsed_prediction)
        self.assertFalse(p.prediction_valid)
        self.assertFalse(p.include_in_metrics)
        self.assertEqual(p.failure_class, "MODEL_BEHAVIOUR")

    def test_malformed_complete_response_is_invalid_not_moderate(self):
        p = parse_dreaddit(body_from("malformed_complete"), OK)
        self.assertIsNone(p.parsed_prediction)
        self.assertNotEqual(p.parsed_prediction, 1)
        self.assertEqual(p.failure_class, "MODEL_BEHAVIOUR")

    def test_never_returns_moderate_for_any_unreadable_fixture(self):
        for name in ("referral_unreadable", "malformed_complete"):
            p = parse_dreaddit(body_from(name), OK)
            self.assertIsNone(p.parsed_prediction, name)

    def test_absent_raw_is_not_scoreable_even_if_server_reports_a_level(self):
        b = body_from("valid_prediction")
        b["referral_agent_raw"] = None
        p = parse_dreaddit(b, OK)
        self.assertEqual(p.parse_status, "raw_absent")
        self.assertFalse(p.prediction_valid)

    def test_safety_intercept_is_not_a_model_prediction(self):
        p = parse_dreaddit(body_from("safety_intercept"), Transport.SAFETY_INTERCEPT)
        self.assertEqual(p.failure_class, "SAFETY_INTERCEPT")
        self.assertFalse(p.include_in_metrics)


# ── 5-9. GoEmotions parsing ──────────────────────────────────────────────────

class T03_GoEmotionsParsing(unittest.TestCase):
    def test_valid_prediction(self):
        p = parse_goemotions(body_from("valid_prediction"), OK)
        self.assertEqual((p.parse_status, p.parsed_prediction, p.prediction_valid),
                         ("ok", "anxiety", True))

    def test_valid_empty_list_is_non_distress(self):
        p = parse_goemotions(body_from("valid_empty_emotions"), OK)
        self.assertEqual(p.parse_status, "ok_empty_list")
        self.assertEqual(p.parsed_prediction, "non_distress")
        self.assertTrue(p.prediction_valid)

    def test_malformed_output_is_not_non_distress(self):
        p = parse_goemotions(body_from("malformed_complete"), OK)
        self.assertNotEqual(p.parsed_prediction, "non_distress")
        self.assertIsNone(p.parsed_prediction)
        self.assertEqual(p.failure_class, "MODEL_BEHAVIOUR")

    def test_truncated_output_is_not_non_distress(self):
        p = parse_goemotions(body_from("truncated_emotion"), OK)
        self.assertIsNone(p.parsed_prediction)
        self.assertIn("fail_", p.parse_status)

    def test_absent_output_is_not_non_distress(self):
        b = body_from("valid_prediction"); b["emotion_agent_raw"] = None
        p = parse_goemotions(b, OK)
        self.assertIsNone(p.parsed_prediction)
        self.assertEqual(p.parse_status, "fail_absent")

    def test_out_of_vocabulary_is_invalid_not_remapped(self):
        p = parse_goemotions(body_from("oov_emotion"), OK)
        self.assertEqual(p.parse_status, "out_of_vocabulary")
        self.assertIsNone(p.parsed_prediction)
        self.assertIn("worried", p.failure_reason)


# ── 10-13, 16-17. retry ──────────────────────────────────────────────────────

class T04_Retry(unittest.TestCase):
    P = RetryPolicy(max_attempts=3, backoff_base_ms=1000, backoff_factor=2)

    def _cls(self, name):
        r = FIXTURES[name]()
        return classify_transport(error_kind=r.error_kind, http_status=r.http_status, body=r.body)

    def test_429_is_transient_and_retried(self):
        o, _ = self._cls("http_429")
        self.assertIs(o, Transport.INFRA_TRANSIENT)
        self.assertTrue(next_action(self.P, o, 1).retry)

    def test_5xx_is_transient_and_retried(self):
        o, _ = self._cls("http_500")
        self.assertIs(o, Transport.INFRA_TRANSIENT)
        self.assertTrue(next_action(self.P, o, 1).retry)

    def test_timeout_is_transient_and_retried(self):
        o, _ = self._cls("timeout")
        self.assertIs(o, Transport.INFRA_TRANSIENT)
        self.assertTrue(next_action(self.P, o, 1).retry)

    def test_400_is_terminal_not_retried(self):
        o, _ = self._cls("http_400")
        self.assertIs(o, Transport.INFRA_TERMINAL)
        self.assertFalse(next_action(self.P, o, 1).retry)

    def test_retry_exhaustion(self):
        d = next_action(self.P, Transport.INFRA_TRANSIENT, 3)
        self.assertFalse(d.retry)
        self.assertEqual(d.reason, "retries_exhausted")

    def test_backoff_is_deterministic_and_capped(self):
        p = RetryPolicy(max_attempts=6, backoff_base_ms=1000, backoff_factor=2, backoff_cap_ms=5000)
        self.assertEqual([p.backoff_ms(i) for i in range(1, 6)], [1000, 2000, 4000, 5000, 5000])
        self.assertEqual(next_action(p, Transport.INFRA_TRANSIENT, 2).wait_ms,
                         next_action(p, Transport.INFRA_TRANSIENT, 2).wait_ms)

    def test_complete_malformed_response_is_never_retried(self):
        o, _ = self._cls("malformed_complete")
        self.assertIs(o, Transport.OK)
        self.assertFalse(is_retryable(o))
        self.assertFalse(next_action(self.P, o, 1).retry)

    def test_oov_response_is_never_retried(self):
        o, _ = self._cls("oov_emotion")
        self.assertFalse(next_action(self.P, o, 1).retry)

    def test_retry_decision_cannot_depend_on_content_or_ground_truth(self):
        sig = set(inspect.signature(next_action).parameters)
        self.assertEqual(sig, {"policy", "outcome", "attempt_number"})
        sig2 = set(inspect.signature(classify_transport).parameters)
        self.assertEqual(sig2, {"error_kind", "http_status", "body"})


# ── 18-19. models and providers ──────────────────────────────────────────────

class T05_ModelSelection(unittest.TestCase):
    def test_disabled_model_is_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            man = build_and_save(tmp, "dreaddit", tiny_dreaddit(tmp))
            cfgp = make_config(tmp, man, "dreaddit", models=[
                {"id": "microsoft/phi-4", "name": "Phi-4", "provider": "openrouter", "enabled": True},
                {"id": "deepseek/deepseek-v4-flash", "name": "DeepSeek",
                 "provider": "openrouter", "enabled": False},
            ])
            cfg = load_config(cfgp)
            ids = [m.id for m in cfg.enabled_models]
            self.assertEqual(ids, ["microsoft/phi-4"])
            self.assertNotIn("deepseek/deepseek-v4-flash", ids)

    def test_enabled_has_no_default(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            man = build_and_save(tmp, "dreaddit", tiny_dreaddit(tmp))
            cfgp = make_config(tmp, man, "dreaddit", models=[
                {"id": "m", "name": "m", "provider": "openrouter"}])
            with self.assertRaises(ConfigError) as c:
                load_config(cfgp)
            self.assertIn("enabled", str(c.exception))

    def test_client_timeout_below_server_budget_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            man = build_and_save(tmp, "dreaddit", tiny_dreaddit(tmp))
            cfgp = make_config(tmp, man, "dreaddit")
            import yaml
            d = yaml.safe_load(cfgp.read_text())
            d["server"]["timeout_seconds"] = 90
            cfgp.write_text(yaml.safe_dump(d))
            with self.assertRaises(ConfigError):
                load_config(cfgp)

    def test_model_mismatch_aborts_the_experiment(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            man = build_and_save(tmp, "dreaddit", tiny_dreaddit(tmp))
            cfg = load_config(make_config(tmp, man, "dreaddit"))
            t = MockTransport({f"dread_{i:06d}": ["model_mismatch"] for i in range(3)})
            with self.assertRaises(PreflightError) as c:
                run_experiment(cfg, transport=t, sleep=lambda s: None)
            self.assertIn("ABORTED", str(c.exception))


# ── 20-22. prompts and ids ───────────────────────────────────────────────────

class T06_PromptsAndIds(unittest.TestCase):
    def test_prompt_hashing_is_stable_and_per_agent(self):
        h = prompt_hashes("zero-shot")
        self.assertEqual(set(h), set(AGENTS))
        self.assertEqual(h, prompt_hashes("zero-shot"))
        self.assertTrue(all(len(v) == 64 for v in h.values()))

    def test_strategies_produce_different_hashes(self):
        a, b = prompt_hashes("zero-shot"), prompt_hashes("one-shot-cot")
        self.assertNotEqual(a["emotion"], b["emotion"])

    def test_missing_prompt_fails_loudly(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(PromptError):
                prompt_hashes("zero-shot", prompts_dir=Path(td))

    def test_inventory_covers_all_strategies(self):
        inv = prompt_inventory(["zero-shot", "zero-shot-cot", "one-shot-cot"])
        self.assertEqual(set(inv["strategies"]), {"zero-shot", "zero-shot-cot", "one-shot-cot"})
        self.assertEqual(len(inv["prompt_set_sha256"]), 64)

    def test_uuid_uniqueness(self):
        ids = {new_uuid() for _ in range(20000)}
        self.assertEqual(len(ids), 20000)


# ── 23-26. storage, manifest, resume, end-to-end ─────────────────────────────

class T07_EndToEnd(unittest.TestCase):
    def _setup(self, td, scripts, dataset="dreaddit", runs=1):
        tmp = Path(td)
        csvp = tiny_dreaddit(tmp) if dataset == "dreaddit" else tiny_goemotions(tmp)
        man = build_and_save(tmp, dataset, csvp)
        cfg = load_config(make_config(tmp, man, dataset, runs=runs))
        return tmp, cfg, MockTransport(scripts)

    def test_raw_output_is_preserved_verbatim_and_before_parsing(self):
        with tempfile.TemporaryDirectory() as td:
            tmp, cfg, t = self._setup(td, {f"dread_{i:06d}": ["valid_prediction"] for i in range(3)})
            out = run_experiment(cfg, transport=t, sleep=lambda s: None)
            attempts = [json.loads(l) for l in
                        (Path(out["run_dir"]) / "raw" / "attempts.jsonl").read_text().splitlines()]
            self.assertEqual(len(attempts), 3)
            for a in attempts:
                self.assertIn("raw", a)
                self.assertEqual(a["raw"]["referral_agent_raw"],
                                 '{"risk_level":"moderate","reasoning":"x"}')
                self.assertIsNotNone(a["response_body"])
                # the derived prediction must NOT be in the raw store
                self.assertNotIn("parsed_prediction", a)
                self.assertNotIn("prediction_valid", a)

    def test_attempt_history_is_preserved_and_attempt_one_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            tmp, cfg, t = self._setup(td, {"dread_000000": ["http_429", "http_500", "valid_prediction"],
                                           "dread_000001": ["valid_prediction"],
                                           "dread_000002": ["valid_prediction"]})
            out = run_experiment(cfg, transport=t, sleep=lambda s: None)
            attempts = [json.loads(l) for l in
                        (Path(out["run_dir"]) / "raw" / "attempts.jsonl").read_text().splitlines()]
            first = [a for a in attempts if a["sample_id"] == "dread_000000"]
            self.assertEqual(len(first), 3)
            self.assertEqual([a["attempt_number"] for a in first], [1, 2, 3])
            self.assertEqual(first[0]["http_status"], 429)
            self.assertEqual(first[0]["outcome_class"], "INFRA_TRANSIENT")
            self.assertEqual(first[2]["outcome_class"], "OK")
            idx = [json.loads(l) for l in
                   (Path(out["run_dir"]) / "raw" / "index.jsonl").read_text().splitlines()]
            rec = [r for r in idx if r["sample_id"] == "dread_000000"][0]
            self.assertEqual(rec["attempt_count"], 3)
            self.assertEqual(len(rec["retry_history"]), 3)
            self.assertEqual(rec["final_outcome_class"], "OK")

    def test_retry_exhaustion_is_recorded_not_scored(self):
        with tempfile.TemporaryDirectory() as td:
            tmp, cfg, t = self._setup(td, {"dread_000000": ["timeout", "timeout", "timeout"],
                                           "dread_000001": ["valid_prediction"],
                                           "dread_000002": ["valid_prediction"]})
            out = run_experiment(cfg, transport=t, sleep=lambda s: None)
            idx = [json.loads(l) for l in
                   (Path(out["run_dir"]) / "raw" / "index.jsonl").read_text().splitlines()]
            rec = [r for r in idx if r["sample_id"] == "dread_000000"][0]
            self.assertEqual(rec["final_outcome_class"], "RETRIES_EXHAUSTED")
            self.assertEqual(rec["attempt_count"], 3)

    def test_resume_skips_successes_and_does_not_duplicate(self):
        with tempfile.TemporaryDirectory() as td:
            tmp, cfg, t = self._setup(td, {f"dread_{i:06d}": ["valid_prediction"] for i in range(3)})
            out = run_experiment(cfg, transport=t, sleep=lambda s: None)
            n_before = len((Path(out["run_dir"]) / "raw" / "index.jsonl").read_text().splitlines())
            t2 = MockTransport({f"dread_{i:06d}": ["valid_prediction"] for i in range(3)})
            out2 = run_experiment(cfg, transport=t2, resume=True, sleep=lambda s: None)
            n_after = len((Path(out2["run_dir"]) / "raw" / "index.jsonl").read_text().splitlines())
            self.assertEqual(n_before, n_after, "resume duplicated completed assessments")
            self.assertEqual(out2["stats"]["dispatched"], 0)
            self.assertEqual(out2["stats"]["skipped_resume"], 3)
            self.assertEqual(t2.calls, [], "resume re-called the model for completed work")

    def test_resume_can_retry_only_exhausted_infrastructure_failures(self):
        with tempfile.TemporaryDirectory() as td:
            tmp, cfg, t = self._setup(td, {"dread_000000": ["timeout", "timeout", "timeout"],
                                           "dread_000001": ["valid_prediction"],
                                           "dread_000002": ["valid_prediction"]})
            run_experiment(cfg, transport=t, sleep=lambda s: None)
            t2 = MockTransport({"dread_000000": ["valid_prediction"]})
            out2 = run_experiment(cfg, transport=t2, resume=True, retry_exhausted=True,
                                  sleep=lambda s: None)
            self.assertEqual(out2["stats"]["dispatched"], 1)
            self.assertEqual({c["sample_id"] for c in t2.calls}, {"dread_000000"})
            idx = [json.loads(l) for l in
                   (Path(out2["run_dir"]) / "raw" / "index.jsonl").read_text().splitlines()]
            for_sample = [r for r in idx if r["sample_id"] == "dread_000000"]
            self.assertEqual(len(for_sample), 2, "the superseded record was not retained")
            self.assertEqual(for_sample[0]["final_outcome_class"], "RETRIES_EXHAUSTED")
            self.assertEqual(for_sample[1]["final_outcome_class"], "OK")
            self.assertEqual(for_sample[1]["supersedes"], for_sample[0]["assessment_uuid"])

    def test_model_behaviour_failure_is_not_retried_on_resume(self):
        with tempfile.TemporaryDirectory() as td:
            tmp, cfg, t = self._setup(td, {"dread_000000": ["malformed_complete"],
                                           "dread_000001": ["valid_prediction"],
                                           "dread_000002": ["valid_prediction"]})
            run_experiment(cfg, transport=t, sleep=lambda s: None)
            t2 = MockTransport({})
            out2 = run_experiment(cfg, transport=t2, resume=True, retry_exhausted=True,
                                  sleep=lambda s: None)
            self.assertEqual(out2["stats"]["dispatched"], 0)
            self.assertEqual(t2.calls, [], "a completed model response was re-rolled")

    def test_refuses_to_write_into_an_existing_run_without_resume(self):
        with tempfile.TemporaryDirectory() as td:
            tmp, cfg, t = self._setup(td, {f"dread_{i:06d}": ["valid_prediction"] for i in range(3)})
            run_experiment(cfg, transport=t, sleep=lambda s: None)
            with self.assertRaises(PreflightError):
                run_experiment(cfg, transport=MockTransport({}), sleep=lambda s: None)

    def test_duplicate_assessment_write_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            s = RunStore(Path(td) / "r")
            rec = {"record_type": "assessment", "cell_id": "c", "sample_id": "s",
                   "assessment_uuid": "u"}
            s.close_assessment(rec)
            with self.assertRaises(DuplicateAssessment):
                s.close_assessment(dict(rec, assessment_uuid="u2"))

    def test_rescore_regenerates_predictions_from_raw_without_network(self):
        with tempfile.TemporaryDirectory() as td:
            tmp, cfg, t = self._setup(td, {"dread_000000": ["valid_prediction"],
                                           "dread_000001": ["referral_unreadable"],
                                           "dread_000002": ["oov_emotion"]})
            out = run_experiment(cfg, transport=t, sleep=lambda s: None)
            n_calls = len(t.calls)
            r1 = rescore(out["run_dir"])
            r2 = rescore(out["run_dir"])          # idempotent
            self.assertEqual(r1["parse_status_counts"], r2["parse_status_counts"])
            self.assertEqual(len(t.calls), n_calls, "rescore called the model")
            recs = [json.loads(l) for l in
                    (Path(out["run_dir"]) / "parsed" / "records.jsonl").read_text().splitlines()]
            self.assertEqual(len(recs), 3)
            by = {r["sample_id"]: r for r in recs}
            self.assertTrue(by["dread_000000"]["prediction_valid"])
            self.assertFalse(by["dread_000001"]["prediction_valid"])
            self.assertEqual(by["dread_000001"]["failure_class"], "MODEL_BEHAVIOUR")

    def test_manifest_validation_detects_dataset_drift(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            csvp = tiny_dreaddit(tmp)
            manp = build_and_save(tmp, "dreaddit", csvp)
            man = json.loads(manp.read_text())
            self.assertEqual(verify_manifest(man), [])
            csvp.write_text(csvp.read_text() + "\n", encoding="utf-8")
            problems = verify_manifest(man)
            self.assertTrue(any("CHANGED" in p for p in problems), problems)

    def test_preflight_freezes_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            tmp, cfg, t = self._setup(td, {})
            frozen = preflight(cfg)
            for k in ("config_sha256", "git_commit", "git_dirty",
                      "git_untracked_count", "prompt_inventory", "datasets",
                      "grid", "retry_policy", "runner_version"):
                self.assertIn(k, frozen)
            self.assertIsInstance(frozen["git_dirty"], bool)
            self.assertTrue(frozen["git_untracked_count"] is None
                            or isinstance(frozen["git_untracked_count"], int))
            self.assertEqual(frozen["runner_version"], RUNNER_VERSION)
            self.assertEqual(frozen["grid"]["cells"], 1)


# ── metrics ──────────────────────────────────────────────────────────────────

class T08_Metrics(unittest.TestCase):
    def test_buckets_account_for_every_record(self):
        recs = [
            {"ground_truth": 1, "parsed_prediction": 1, "prediction_valid": True, "failure_class": None},
            {"ground_truth": 0, "parsed_prediction": 0, "prediction_valid": True, "failure_class": None},
            {"ground_truth": 1, "parsed_prediction": None, "prediction_valid": False,
             "failure_class": "MODEL_BEHAVIOUR"},
            {"ground_truth": 1, "parsed_prediction": None, "prediction_valid": False,
             "failure_class": "INFRA_TRANSIENT"},
            {"ground_truth": 1, "parsed_prediction": None, "prediction_valid": False,
             "failure_class": "SAFETY_INTERCEPT"},
        ]
        m = cell_metrics(recs, labels=[0, 1], majority_baseline=0.688)
        b = m["buckets"]
        self.assertEqual(b["N_total"], 5)
        self.assertEqual(b["N_safety_intercept"], 1)
        self.assertEqual(b["N_attributable"], 4)
        self.assertEqual(b["N_successful_valid_predictions"], 2)
        self.assertEqual(b["N_model_behavior_invalid"], 1)
        self.assertEqual(b["N_infrastructure_failed"], 1)
        self.assertEqual(b["N_unaccounted"], 0)

    def test_failures_never_count_as_predictions(self):
        recs = [{"ground_truth": 1, "parsed_prediction": None, "prediction_valid": False,
                 "failure_class": "MODEL_BEHAVIOUR"}] * 3
        m = cell_metrics(recs, labels=[0, 1])
        self.assertIsNone(m["metrics"])
        self.assertEqual(m["buckets"]["N_successful_valid_predictions"], 0)
        self.assertEqual(m["rates"]["evaluability"], 0.0)

    def test_effective_accuracy_penalises_declining_to_answer(self):
        recs = [{"ground_truth": 1, "parsed_prediction": 1, "prediction_valid": True,
                 "failure_class": None}] + \
               [{"ground_truth": 1, "parsed_prediction": None, "prediction_valid": False,
                 "failure_class": "MODEL_BEHAVIOUR"}]
        m = cell_metrics(recs, labels=[0, 1])
        self.assertEqual(m["metrics"]["accuracy_conditional"], 1.0)
        self.assertEqual(m["metrics"]["accuracy_effective"], 0.5)


# ── historical data is untouched ─────────────────────────────────────────────

class T09_HistoricalReadOnly(unittest.TestCase):
    def test_runner_never_references_the_historical_output_tree(self):
        pkg = PKG_ROOT / "runner"
        for f in pkg.glob("*.py"):
            src = f.read_text(encoding="utf-8")
            self.assertNotIn("llm-experiments/outputs", src,
                             f"{f.name} references the historical output tree")
            self.assertNotIn("stage_c", src, f"{f.name} references historical stage_c data")

    def test_parser_port_matches_the_preflight_copy(self):
        a = (PKG_ROOT / "runner" / "referral_risk_parser.py").read_text(encoding="utf-8")
        b = (REPO_ROOT / "evaluation" / "llm-experiments" / "tests_preflight"
             / "referral_risk_parser_port.py").read_text(encoding="utf-8")
        self.assertEqual(a, b, "the two Python ports of the referral ladder have diverged")


# ── provenance reporting (fixes A and B) ─────────────────────────────────────

class T10_ProvenanceReporting(unittest.TestCase):
    """git_dirty must track TRACKED modifications only, and --preflight-only
    must emit complete, parseable JSON. Both are reporting-only guarantees:
    neither gates a run or touches methodology."""

    @staticmethod
    def _git(cwd, *args):
        return subprocess.run(["git", "-C", str(cwd), *args],
                              capture_output=True, text=True, check=True)

    def _repo(self, td):
        r = Path(td) / "repo"; r.mkdir()
        self._git(r, "init", "-q")
        self._git(r, "config", "user.email", "t@example.com")
        self._git(r, "config", "user.name", "t")
        (r / "tracked.txt").write_text("v1\n", encoding="utf-8")
        self._git(r, "add", "tracked.txt")
        self._git(r, "commit", "-q", "-m", "init")
        return r

    def test_clean_repo_is_not_dirty(self):
        with tempfile.TemporaryDirectory() as td:
            r = self._repo(td)
            self.assertFalse(git_dirty(r))
            self.assertEqual(git_untracked_count(r), 0)

    def test_untracked_files_do_not_make_the_repo_dirty(self):
        """The regression this fix exists for: the real repo deliberately keeps
        untracked archives and quarantine folders, and they used to force
        git_dirty=true on every single run record."""
        with tempfile.TemporaryDirectory() as td:
            r = self._repo(td)
            (r / "archive.zip").write_bytes(b"x")
            (r / "_to_delete").mkdir()
            (r / "_to_delete" / "old.json").write_text("{}", encoding="utf-8")
            (r / "stale_outputs").mkdir()
            (r / "stale_outputs" / "a.jsonl").write_text("{}\n", encoding="utf-8")
            self.assertFalse(git_dirty(r), "untracked files must not mark the tree dirty")
            self.assertEqual(git_untracked_count(r), 3)

    def test_modified_tracked_file_is_dirty(self):
        with tempfile.TemporaryDirectory() as td:
            r = self._repo(td)
            (r / "tracked.txt").write_text("v2\n", encoding="utf-8")
            self.assertTrue(git_dirty(r))

    def test_staged_tracked_change_is_dirty(self):
        with tempfile.TemporaryDirectory() as td:
            r = self._repo(td)
            (r / "tracked.txt").write_text("v2\n", encoding="utf-8")
            self._git(r, "add", "tracked.txt")
            self.assertTrue(git_dirty(r))

    def test_deleted_tracked_file_is_dirty(self):
        with tempfile.TemporaryDirectory() as td:
            r = self._repo(td)
            (r / "tracked.txt").unlink()
            self.assertTrue(git_dirty(r))

    def test_untracked_alongside_a_tracked_change_still_reads_dirty(self):
        with tempfile.TemporaryDirectory() as td:
            r = self._repo(td)
            (r / "tracked.txt").write_text("v2\n", encoding="utf-8")
            (r / "archive.zip").write_bytes(b"x")
            self.assertTrue(git_dirty(r))
            self.assertEqual(git_untracked_count(r), 1)

    def test_non_repo_fails_closed(self):
        """If git cannot answer, provenance must claim dirty, never clean."""
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "not_a_repo"; d.mkdir()
            self.assertTrue(git_dirty(d))
            self.assertIsNone(git_untracked_count(d))

    def test_preflight_only_prints_complete_valid_json(self):
        """Regression: the CLI used to slice the payload at 4000 chars, so
        redirecting --preflight-only produced truncated, unparseable JSON
        while still exiting 0."""
        with tempfile.TemporaryDirectory() as td:
            cfg = self._big_config(td)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = run_main(["--config", str(cfg), "--preflight-only"])
            self.assertEqual(rc, 0)
            out = buf.getvalue()
            self.assertGreater(
                len(out), self.OLD_CAP + 1,
                "fixture is smaller than the old cap, so it cannot detect a regression")
            parsed = json.loads(out)                      # must not raise
            for k in ("experiment_id", "config_sha256", "git_commit", "git_dirty",
                      "git_untracked_count", "models_enabled", "models_disabled",
                      "prompt_inventory", "datasets", "grid", "retry_policy", "server"):
                self.assertIn(k, parsed)
            self.assertIn("prompt_set_sha256", parsed["prompt_inventory"])
            self.assertTrue(parsed["datasets"], "datasets block must be present and complete")

    #: the character cap this test exists to prove is gone (was run.py's
    #: `print(json.dumps(frozen, indent=2)[:4000])`).
    OLD_CAP = 4000

    @staticmethod
    def _big_config(td):
        """A config whose frozen block is comfortably larger than OLD_CAP, so
        that a reinstated slice would truncate it and json.loads would fail.
        Built locally rather than via make_config so no other test's fixture
        changes."""
        import yaml
        tmp = Path(td)
        d_man = build_and_save(tmp, "dreaddit", tiny_dreaddit(tmp))
        g_man = build_and_save(tmp, "goemotions", tiny_goemotions(tmp))
        cfg = {
            "experiment_id": "preflight_json_probe",
            "output_root": str(tmp / "runs"),
            "models": [
                {"id": "microsoft/phi-4", "name": "Phi-4",
                 "provider": "openrouter", "enabled": True},
                {"id": "qwen/qwen3.5-27b", "name": "Qwen 3.5 27B",
                 "provider": "openrouter", "enabled": False},
                {"id": "meta-llama/llama-4-scout", "name": "Llama 4 Scout",
                 "provider": "openrouter", "enabled": False},
                {"id": "mistralai/mistral-small-2603", "name": "Mistral Small 4",
                 "provider": "openrouter", "enabled": False},
                {"id": "google/gemma-4-31b-it", "name": "Gemma 4 31B IT",
                 "provider": "openrouter", "enabled": False},
            ],
            "strategies": ["zero-shot", "zero-shot-cot", "one-shot-cot"],
            "datasets": [{"name": "dreaddit", "manifest": str(d_man)},
                         {"name": "goemotions", "manifest": str(g_man)}],
            "runs": 1, "run_start": 1,
            "retry": {"max_attempts": 3, "backoff_base_ms": 1, "backoff_factor": 2},
            "server": {"base_url": "http://localhost:3001", "timeout_seconds": 180,
                       "server_poll_budget_seconds": 150},
        }
        p = tmp / "big_config.yaml"
        p.write_text(yaml.safe_dump(cfg), encoding="utf-8")
        return p


# ── frozen GoEmotions mapping v1.0.0 ─────────────────────────────────────────

#: The adopted mapping, written out label by label so a change to
#: goemotions_mapping.py cannot pass silently. Sources are recorded in that
#: module; this is the assertion of the frozen decision itself.
EXPECTED_28 = {
    # anxiety - DEPARTS from the official Ekman grouping (S2 puts nervousness
    # under fear). Basis: S1 Appendix A definition + S4 construct distinction.
    "nervousness": "anxiety",
    # fear
    "fear": "fear",
    # official Ekman sadness group
    "sadness": "sadness", "disappointment": "sadness", "grief": "sadness",
    "embarrassment": "sadness", "remorse": "sadness",
    # official Ekman anger group -> AnxioSense "frustration"
    "anger": "frustration", "annoyance": "frustration", "disapproval": "frustration",
    # official positive sentiment group + neutral -> AnxioSense "non_distress"
    "admiration": "non_distress", "amusement": "non_distress", "approval": "non_distress",
    "caring": "non_distress", "desire": "non_distress", "excitement": "non_distress",
    "gratitude": "non_distress", "joy": "non_distress", "love": "non_distress",
    "optimism": "non_distress", "pride": "non_distress", "relief": "non_distress",
    "neutral": "non_distress",
    # official ambiguous sentiment group
    "realization": OUT_OF_TAXONOMY, "surprise": OUT_OF_TAXONOMY,
    "curiosity": OUT_OF_TAXONOMY, "confusion": OUT_OF_TAXONOMY,
    # own Ekman category, distinct from anger; no AnxioSense class
    "disgust": OUT_OF_TAXONOMY,
}


class T11_GoEmotionsMappingV1(unittest.TestCase):
    """Every one of the 28 labels, and all four multi-label rules."""

    def test_mapping_version_is_frozen(self):
        self.assertEqual(MAPPING_VERSION, "1.0.0")

    def test_label_space_is_exactly_the_28_official_labels(self):
        self.assertEqual(len(GOEMOTIONS_LABELS), 28)
        self.assertEqual(set(LABEL_MAP), set(GOEMOTIONS_LABELS))
        self.assertEqual(len(EXPECTED_28), 28)

    def test_every_one_of_the_28_labels_maps_as_frozen(self):
        for label in GOEMOTIONS_LABELS:
            with self.subTest(label=label):
                self.assertEqual(anxiosense_class(label), EXPECTED_28[label])
                if EXPECTED_28[label] != OUT_OF_TAXONOMY:
                    self.assertEqual(map_goemotions_labels([label]), EXPECTED_28[label])

    def test_class_counts_match_the_adopted_mapping(self):
        counts = Counter(EXPECTED_28.values())
        self.assertEqual(counts["anxiety"], 1)
        self.assertEqual(counts["fear"], 1)
        self.assertEqual(counts["sadness"], 5)
        self.assertEqual(counts["frustration"], 3)
        self.assertEqual(counts["non_distress"], 13)
        self.assertEqual(counts[OUT_OF_TAXONOMY], 5)

    def test_destinations_are_only_eval_classes_or_out_of_taxonomy(self):
        allowed = set(GE_EVAL_CLASSES) | {OUT_OF_TAXONOMY}
        self.assertTrue(all(c in allowed for c, _, _ in LABEL_MAP.values()))

    # -- the official groupings must not drift --------------------------------

    def test_official_ekman_grouping_is_verbatim(self):
        """google-research/goemotions/data/ekman_mapping.json, fetched 2026-09-04."""
        self.assertEqual(
            {k: sorted(v) for k, v in EKMAN_GROUPING.items()},
            {"anger": ["anger", "annoyance", "disapproval"],
             "disgust": ["disgust"],
             "fear": ["fear", "nervousness"],
             "joy": sorted(["joy", "amusement", "approval", "excitement", "gratitude",
                            "love", "optimism", "relief", "pride", "admiration",
                            "desire", "caring"]),
             "sadness": sorted(["sadness", "disappointment", "embarrassment",
                                "grief", "remorse"]),
             "surprise": sorted(["surprise", "realization", "confusion", "curiosity"])})

    def test_official_sentiment_grouping_is_verbatim(self):
        """google-research/goemotions/data/sentiment_mapping.json, fetched 2026-09-04."""
        self.assertEqual(sorted(SENTIMENT_GROUPING["ambiguous"]),
                         ["confusion", "curiosity", "realization", "surprise"])
        self.assertEqual(len(SENTIMENT_GROUPING["positive"]), 12)
        self.assertEqual(len(SENTIMENT_GROUPING["negative"]), 11)
        self.assertNotIn("neutral", SENTIMENT_GROUPING["positive"])

    def test_ekman_sadness_and_anger_groups_are_honoured_exactly(self):
        for l in EKMAN_GROUPING["sadness"]:
            self.assertEqual(anxiosense_class(l), "sadness", l)
        for l in EKMAN_GROUPING["anger"]:
            self.assertEqual(anxiosense_class(l), "frustration", l)

    def test_positive_sentiment_group_all_maps_to_non_distress(self):
        for l in SENTIMENT_GROUPING["positive"]:
            self.assertEqual(anxiosense_class(l), "non_distress", l)

    def test_ambiguous_sentiment_group_is_out_of_taxonomy(self):
        for l in SENTIMENT_GROUPING["ambiguous"]:
            self.assertEqual(anxiosense_class(l), OUT_OF_TAXONOMY, l)

    def test_nervousness_departs_from_ekman_deliberately(self):
        """Documented departure: S2 groups nervousness with fear; we map it to
        anxiety on S1's definition plus S4. If this ever silently becomes
        'fear', the anxiety class vanishes from GoEmotions."""
        self.assertIn("nervousness", EKMAN_GROUPING["fear"])
        self.assertEqual(anxiosense_class("nervousness"), "anxiety")
        self.assertEqual(LABEL_MAP["nervousness"][1], "derived")

    def test_disgust_is_not_folded_into_frustration(self):
        self.assertEqual(EKMAN_GROUPING["disgust"], ("disgust",))
        self.assertEqual(anxiosense_class("disgust"), OUT_OF_TAXONOMY)

    def test_positive_and_neutral_are_marked_operational_not_direct(self):
        """The grouping is GoEmotions'; the non_distress destination is ours."""
        for l in list(SENTIMENT_GROUPING["positive"]) + ["neutral"]:
            self.assertEqual(LABEL_MAP[l][1], "operational", l)

    # -- R1..R4 ---------------------------------------------------------------

    def test_R1_single_label(self):
        self.assertEqual(map_goemotions_labels(["sadness"]), "sadness")

    def test_R1_multiple_labels_all_agreeing(self):
        self.assertEqual(map_goemotions_labels(["anger", "annoyance", "disapproval"]),
                         "frustration")
        self.assertEqual(map_goemotions_labels(["grief", "sadness", "remorse"]), "sadness")
        self.assertEqual(map_goemotions_labels(["joy", "neutral", "gratitude"]),
                         "non_distress")

    def test_R2_conflicting_classes_is_unscorable(self):
        for labels in (["annoyance", "neutral"], ["fear", "joy"],
                       ["nervousness", "sadness"], ["anger", "grief"]):
            with self.subTest(labels=labels):
                with self.assertRaises(UnscorableRow) as cm:
                    map_goemotions_labels(labels)
                self.assertEqual(cm.exception.reason, UNSCORABLE_CONFLICT)

    def test_R3_mixed_mapped_and_out_of_taxonomy_resolves(self):
        self.assertEqual(map_goemotions_labels(["nervousness", "curiosity"]), "anxiety")
        self.assertEqual(map_goemotions_labels(["confusion", "sadness", "grief"]), "sadness")
        self.assertEqual(map_goemotions_labels(["disgust", "anger"]), "frustration")

    def test_R3_mixed_that_still_conflicts_is_unscorable(self):
        with self.assertRaises(UnscorableRow) as cm:
            map_goemotions_labels(["surprise", "anger", "joy"])
        self.assertEqual(cm.exception.reason, UNSCORABLE_CONFLICT)

    def test_R4_only_out_of_taxonomy_is_unscorable(self):
        for labels in (["curiosity"], ["confusion", "surprise"], ["disgust"],
                       ["realization", "curiosity", "disgust"]):
            with self.subTest(labels=labels):
                with self.assertRaises(UnscorableRow) as cm:
                    map_goemotions_labels(labels)
                self.assertEqual(cm.exception.reason, UNSCORABLE_OUT_OF_TAXONOMY)

    # -- the two removed defects ---------------------------------------------

    def test_empty_label_list_raises_and_is_never_non_distress(self):
        """The historical mapper returned 'non_distress' here, which at official
        scope would have fabricated ground truth for 2,670 of 5,427 rows."""
        for empty in ([], [""], ["   "]):
            with self.subTest(v=empty):
                with self.assertRaises(MappingDataError):
                    map_goemotions_labels(empty)

    def test_no_first_label_tie_break(self):
        """GoEmotions stores ids ascending, so 'take the first label' is a
        lowest-id-wins storage artefact. annoyance(3)+neutral(27) must NOT
        silently become frustration."""
        with self.assertRaises(UnscorableRow):
            map_goemotions_labels(["annoyance", "neutral"])
        with self.assertRaises(UnscorableRow):
            map_goemotions_labels(["neutral", "annoyance"])

    def test_rule_is_order_independent(self):
        for a, b in (("anger", "annoyance"), ("curiosity", "nervousness"),
                     ("neutral", "joy")):
            self.assertEqual(map_goemotions_labels([a, b]), map_goemotions_labels([b, a]))

    def test_unknown_label_is_fatal_not_silently_dropped(self):
        with self.assertRaises(MappingDataError):
            map_goemotions_labels(["ennui"])
        with self.assertRaises(MappingDataError):
            map_goemotions_labels(["sadness", "ennui"])

    def test_publication_path_does_not_use_the_historical_mapper(self):
        from runner import _reuse
        col, mapper = _reuse.GROUND_TRUTH_MAPPERS["goemotions"]
        self.assertEqual(col, "label_names")
        self.assertIsNot(mapper, _reuse.map_goemotions_label)
        # and the historical mapper's defect is still there, unmodified
        self.assertEqual(_reuse.map_goemotions_label("[]"), "non_distress")
        # while the frozen path refuses
        with self.assertRaises(MappingDataError):
            mapper("")

    def test_provenance_block_is_serialisable_and_honest(self):
        prov = mapping_provenance()
        self.assertEqual(prov["mapping_version"], "1.0.0")
        self.assertEqual(json.loads(json.dumps(prov)), prov)
        self.assertIn("the five AnxioSense destination class names",
                      prov["not_published_by_goemotions"])
        self.assertEqual(len(prov["evidence_tiers"]), 28)


# ── resume bookkeeping ───────────────────────────────────────────────────────

class T12_ResumeBookkeeping(unittest.TestCase):
    """A --resume invocation must never overwrite or misrepresent the original
    dispatch statistics, and must itself be separately auditable."""

    def _setup(self, td, scripts, n=3):
        tmp = Path(td)
        csvp = tiny_dreaddit(tmp, n=n)
        man = build_and_save(tmp, "dreaddit", csvp)
        cfg = load_config(make_config(tmp, man, "dreaddit"))
        return tmp, cfg, MockTransport(scripts)

    def _run(self, cfg, transport, **kw):
        return run_experiment(cfg, transport=transport, sleep=lambda *_: None, **kw)

    def test_resume_preserves_the_original_dispatch_counts(self):
        with tempfile.TemporaryDirectory() as td:
            tmp, cfg, t = self._setup(td, {})
            first = self._run(cfg, t)
            rd = Path(first["run_dir"])
            stats_path = rd / "summaries" / "dispatch_stats.json"
            after_first = json.loads(stats_path.read_text())

            n_dispatched = after_first["first_invocation"]["stats"]["dispatched"]
            self.assertGreater(n_dispatched, 0)
            self.assertEqual(after_first["invocation_count"], 1)
            self.assertEqual(after_first["totals"]["dispatched"], n_dispatched)

            # a resume that dispatches nothing
            second = self._run(cfg, MockTransport({}), resume=True)
            after_resume = json.loads(stats_path.read_text())

            # THE REGRESSION: the original counts survive
            self.assertEqual(after_resume["first_invocation"]["stats"]["dispatched"],
                             n_dispatched)
            self.assertEqual(after_resume["first_invocation"],
                             after_first["first_invocation"])
            self.assertEqual(after_resume["totals"]["dispatched"], n_dispatched)
            self.assertEqual(second["stats"]["dispatched"], 0)

    def test_resume_is_separately_auditable(self):
        with tempfile.TemporaryDirectory() as td:
            tmp, cfg, t = self._setup(td, {})
            first = self._run(cfg, t)
            rd = Path(first["run_dir"])
            self._run(cfg, MockTransport({}), resume=True)
            summary = json.loads((rd / "summaries" / "dispatch_stats.json").read_text())

            self.assertEqual(summary["invocation_count"], 2)
            modes = [i["mode"] for i in summary["invocations"]]
            self.assertEqual(modes, ["initial", "resume"])
            self.assertEqual(summary["invocations"][0]["invocation_number"], 1)
            self.assertEqual(summary["invocations"][1]["invocation_number"], 2)
            self.assertIs(summary["invocations"][0]["resume"], False)
            self.assertIs(summary["invocations"][1]["resume"], True)
            self.assertEqual(summary["invocations"][1]["stats"]["dispatched"], 0)
            self.assertGreater(summary["invocations"][1]["stats"]["skipped_resume"], 0)
            self.assertNotEqual(summary["invocations"][0]["invocation_uuid"],
                                summary["invocations"][1]["invocation_uuid"])
            for i in summary["invocations"]:
                for k in ("started_utc", "finished_utc", "git_commit", "config_sha256",
                          "runner_version"):
                    self.assertIn(k, i)

    def test_invocation_log_is_append_only(self):
        with tempfile.TemporaryDirectory() as td:
            tmp, cfg, t = self._setup(td, {})
            first = self._run(cfg, t)
            log = Path(first["run_dir"]) / "summaries" / "invocations.jsonl"
            line1 = log.read_text().splitlines()[0]
            self._run(cfg, MockTransport({}), resume=True)
            self._run(cfg, MockTransport({}), resume=True)
            lines = log.read_text().splitlines()
            self.assertEqual(len(lines), 3)
            self.assertEqual(lines[0], line1, "the first invocation record was rewritten")
            self.assertEqual([json.loads(l)["invocation_number"] for l in lines], [1, 2, 3])

    def test_resume_does_not_touch_raw_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            tmp, cfg, t = self._setup(td, {})
            first = self._run(cfg, t)
            rd = Path(first["run_dir"])
            before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (rd / "raw").iterdir()}
            self._run(cfg, MockTransport({}), resume=True)
            after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (rd / "raw").iterdir()}
            self.assertEqual(before, after, "a resume modified append-only raw evidence")

    def test_totals_accumulate_across_invocations(self):
        with tempfile.TemporaryDirectory() as td:
            tmp, cfg, t = self._setup(td, {}, n=3)
            first = self._run(cfg, t, limit=1)
            rd = Path(first["run_dir"])
            d1 = json.loads((rd / "summaries" / "dispatch_stats.json").read_text())
            n1 = d1["totals"]["dispatched"]
            self._run(cfg, MockTransport({}), resume=True)     # dispatches the rest
            d2 = json.loads((rd / "summaries" / "dispatch_stats.json").read_text())
            self.assertEqual(d2["invocation_count"], 2)
            self.assertEqual(d2["first_invocation"]["stats"]["dispatched"], n1)
            self.assertEqual(
                d2["totals"]["dispatched"],
                sum(i["stats"]["dispatched"] for i in d2["invocations"]))

    def test_summary_can_be_checked_against_raw(self):
        """recomputed_from_raw is independent of every summary file, so a legacy
        or corrupted summary can always be audited against the append-only index."""
        with tempfile.TemporaryDirectory() as td:
            tmp, cfg, t = self._setup(td, {})
            first = self._run(cfg, t)
            rd = Path(first["run_dir"])
            self._run(cfg, MockTransport({}), resume=True)
            s = json.loads((rd / "summaries" / "dispatch_stats.json").read_text())
            self.assertEqual(s["recomputed_from_raw"]["terminal_assessments"],
                             s["totals"]["dispatched"])
            self.assertEqual(s["schema"], "dispatch_stats/2")


# ── polling provenance ───────────────────────────────────────────────────────

def health(interval=3000, maxms=150_000, source="default", **extra):
    """A stand-in for GET /api/health, shaped exactly like server/src/index.ts."""
    body = {"status": "ok", "time": "2026-09-04T00:00:00.000Z",
            "mastra_poll_interval_ms": interval, "mastra_poll_max_ms": maxms,
            "mastra_poll_interval_source": source}
    body.update(extra)
    return lambda: body


def boom(exc=ConnectionRefusedError("connection refused")):
    def _p():
        raise exc
    return _p


class T13_PollingProvenance(unittest.TestCase):
    """The effective Mastra poll cadence must be read from the server, frozen
    into the run record and stamped on every attempt - because it changes
    measured latency, and latency is a reported result."""

    def _cfg(self, td, declared=None, dataset="dreaddit"):
        import yaml
        tmp = Path(td)
        csvp = tiny_dreaddit(tmp) if dataset == "dreaddit" else tiny_goemotions(tmp)
        man = build_and_save(tmp, dataset, csvp)
        server = {"base_url": "http://localhost:3001", "timeout_seconds": 180,
                  "server_poll_budget_seconds": 150}
        if declared is not None:
            server["mastra_poll_interval_ms"] = declared
        cfg = {"experiment_id": "poll", "output_root": str(tmp / "runs"),
               "models": [{"id": "microsoft/phi-4", "name": "Phi-4",
                           "provider": "openrouter", "enabled": True}],
               "strategies": ["zero-shot"],
               "datasets": [{"name": dataset, "manifest": str(man)}],
               "runs": 1, "run_start": 1,
               "retry": {"max_attempts": 3, "backoff_base_ms": 1, "backoff_factor": 2},
               "server": server}
        p = tmp / "cfg.yaml"
        p.write_text(yaml.safe_dump(cfg), encoding="utf-8")
        return load_config(p)

    # -- the default ---------------------------------------------------------

    def test_default_3000_is_read_and_recorded(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = self._cfg(td, declared=3000)
            rt = resolve_server_runtime(cfg, health(3000, source="default"))
            self.assertEqual(rt["effective_mastra_poll_interval_ms"], 3000)
            self.assertEqual(rt["expected_mastra_poll_interval_ms"], 3000)
            self.assertEqual(rt["source"], "default")
            self.assertTrue(rt["verified"])
            self.assertIsNone(rt["probe_error"])

    # -- the explicit 250 ----------------------------------------------------

    def test_explicit_250_is_read_and_recorded(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = self._cfg(td, declared=250)
            rt = resolve_server_runtime(cfg, health(250, source="env"))
            self.assertEqual(rt["effective_mastra_poll_interval_ms"], 250)
            self.assertEqual(rt["source"], "env")
            self.assertTrue(rt["verified"])

    # -- mismatch ------------------------------------------------------------

    def test_mismatch_aborts_preflight(self):
        """Declared 250 but the server is still on the 3000 default."""
        with tempfile.TemporaryDirectory() as td:
            cfg = self._cfg(td, declared=250)
            with self.assertRaises(PreflightError) as cm:
                resolve_server_runtime(cfg, health(3000))
            m = str(cm.exception)
            self.assertIn("250", m)
            self.assertIn("3000", m)
            self.assertIn("mismatch", m.lower())

    def test_mismatch_the_other_way_also_aborts(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = self._cfg(td, declared=3000)
            with self.assertRaises(PreflightError):
                resolve_server_runtime(cfg, health(250))

    def test_mismatch_aborts_the_whole_preflight(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = self._cfg(td, declared=250)
            with self.assertRaises(PreflightError):
                preflight(cfg, server_probe=health(3000))

    # -- missing / invalid ---------------------------------------------------

    def test_null_interval_aborts_when_declared(self):
        """The server reports null when MASTRA_POLL_INTERVAL_MS is non-numeric."""
        with tempfile.TemporaryDirectory() as td:
            cfg = self._cfg(td, declared=250)
            with self.assertRaises(PreflightError) as cm:
                resolve_server_runtime(cfg, health(None))
            self.assertIn("null", str(cm.exception))

    def test_missing_field_aborts_when_declared(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = self._cfg(td, declared=250)
            probe = lambda: {"status": "ok", "time": "t"}       # legacy server
            with self.assertRaises(PreflightError):
                resolve_server_runtime(cfg, probe)

    def test_unreachable_server_aborts_when_declared(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = self._cfg(td, declared=3000)
            with self.assertRaises(PreflightError) as cm:
                resolve_server_runtime(cfg, boom())
            self.assertIn("could not be read", str(cm.exception))

    def test_invalid_declared_value_is_a_config_error(self):
        for bad in (0, -1):
            with tempfile.TemporaryDirectory() as td:
                with self.assertRaises(ConfigError):
                    self._cfg(td, declared=bad)

    # -- backward compatibility ---------------------------------------------

    def test_undeclared_config_records_but_does_not_abort(self):
        """Configs written before 2026-09-04 declare nothing. They keep their
        config_sha256 and stay comparable with the runs already made."""
        with tempfile.TemporaryDirectory() as td:
            cfg = self._cfg(td, declared=None)
            self.assertIsNone(cfg.server.mastra_poll_interval_ms)
            rt = resolve_server_runtime(cfg, health(3000))
            self.assertEqual(rt["effective_mastra_poll_interval_ms"], 3000)
            self.assertFalse(rt["verified"])

    def test_undeclared_config_survives_an_unreachable_server(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = self._cfg(td, declared=None)
            rt = resolve_server_runtime(cfg, boom())
            self.assertIsNone(rt["effective_mastra_poll_interval_ms"])
            self.assertEqual(rt["source"], "unavailable")
            self.assertFalse(rt["verified"])
            self.assertIn("ConnectionRefusedError", rt["probe_error"])

    # -- it reaches the run record ------------------------------------------

    def test_frozen_block_carries_server_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = self._cfg(td, declared=250)
            f = preflight(cfg, server_probe=health(250, source="env"))
            self.assertEqual(f["server_runtime"]["effective_mastra_poll_interval_ms"], 250)
            self.assertEqual(f["server"]["mastra_poll_interval_ms"], 250)
            self.assertEqual(json.loads(json.dumps(f["server_runtime"])),
                             f["server_runtime"])

    def test_every_attempt_records_the_effective_interval(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = self._cfg(td, declared=250)
            out = run_experiment(cfg, transport=MockTransport({}),
                                 sleep=lambda *_: None,
                                 server_probe=health(250, source="env"))
            rd = Path(out["run_dir"])
            exp = json.loads((rd / "experiment.json").read_text())
            self.assertEqual(exp["server_runtime"]["effective_mastra_poll_interval_ms"], 250)
            att = [json.loads(l) for l in
                   (rd / "raw" / "attempts.jsonl").read_text().splitlines() if l.strip()]
            self.assertTrue(att)
            self.assertEqual({a["mastra_poll_interval_ms"] for a in att}, {250})

    def test_undeclared_run_records_null_rather_than_a_guess(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = self._cfg(td, declared=None)
            out = run_experiment(cfg, transport=MockTransport({}),
                                 sleep=lambda *_: None, server_probe=boom())
            att = [json.loads(l) for l in
                   (Path(out["run_dir"]) / "raw" / "attempts.jsonl").read_text().splitlines()
                   if l.strip()]
            self.assertEqual({a["mastra_poll_interval_ms"] for a in att}, {None})


# ── run_class ────────────────────────────────────────────────────────────────

class T14_RunClass(unittest.TestCase):
    """Run class is DECLARED in the config. It is never inferred from the
    experiment_id, the config path, or a CLI flag."""

    def _write(self, td, *, run_class=None, poll=None, eid="rc"):
        import yaml
        tmp = Path(td)
        man = build_and_save(tmp, "dreaddit", tiny_dreaddit(tmp))
        server = {"base_url": "http://localhost:3001", "timeout_seconds": 180,
                  "server_poll_budget_seconds": 150}
        if poll is not None:
            server["mastra_poll_interval_ms"] = poll
        cfg = {"experiment_id": eid, "output_root": str(tmp / "runs"),
               "models": [{"id": "microsoft/phi-4", "name": "Phi-4",
                           "provider": "openrouter", "enabled": True}],
               "strategies": ["zero-shot"],
               "datasets": [{"name": "dreaddit", "manifest": str(man)}],
               "runs": 1, "run_start": 1,
               "retry": {"max_attempts": 3, "backoff_base_ms": 1, "backoff_factor": 2},
               "server": server}
        if run_class is not None:
            cfg["run_class"] = run_class
        p = tmp / f"{eid}.yaml"
        p.write_text(yaml.safe_dump(cfg), encoding="utf-8")
        return p

    def test_all_four_classes_load(self):
        self.assertEqual(set(RUN_CLASSES), {"publication", "benchmark", "smoke", "mock"})
        for rc in RUN_CLASSES:
            with tempfile.TemporaryDirectory() as td, self.subTest(rc=rc):
                poll = 3000 if rc == "publication" else None
                self.assertEqual(load_config(self._write(td, run_class=rc, poll=poll)).run_class, rc)

    def test_default_is_benchmark_when_omitted(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(load_config(self._write(td)).run_class, "benchmark")
            self.assertEqual(DEFAULT_RUN_CLASS, "benchmark")

    def test_unknown_class_is_a_config_error(self):
        for bad in ("Publication", "prod", "", "production", "PUBLICATION"):
            with tempfile.TemporaryDirectory() as td, self.subTest(bad=bad):
                with self.assertRaises(ConfigError) as cm:
                    load_config(self._write(td, run_class=bad, poll=3000))
                self.assertIn("run_class", str(cm.exception))

    def test_publication_without_poll_interval_is_rejected_at_load(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ConfigError) as cm:
                load_config(self._write(td, run_class="publication", poll=None))
            m = str(cm.exception)
            self.assertIn("mastra_poll_interval_ms", m)
            self.assertIn("publication", m)

    def test_publication_with_poll_interval_loads(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = load_config(self._write(td, run_class="publication", poll=250))
            self.assertEqual(cfg.run_class, "publication")
            self.assertEqual(cfg.server.mastra_poll_interval_ms, 250)

    def test_non_publication_classes_do_not_require_it(self):
        for rc in ("benchmark", "smoke", "mock"):
            with tempfile.TemporaryDirectory() as td, self.subTest(rc=rc):
                cfg = load_config(self._write(td, run_class=rc, poll=None))
                self.assertIsNone(cfg.server.mastra_poll_interval_ms)

    def test_publication_preflight_aborts_on_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = load_config(self._write(td, run_class="publication", poll=250))
            with self.assertRaises(PreflightError):
                preflight(cfg, server_probe=health(3000))

    def test_publication_preflight_aborts_when_unreachable(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = load_config(self._write(td, run_class="publication", poll=3000))
            with self.assertRaises(PreflightError):
                preflight(cfg, server_probe=boom())

    def test_publication_preflight_aborts_on_null_or_missing(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = load_config(self._write(td, run_class="publication", poll=3000))
            with self.assertRaises(PreflightError):
                preflight(cfg, server_probe=health(None))
            with self.assertRaises(PreflightError):
                preflight(cfg, server_probe=lambda: {"status": "ok"})

    def test_publication_preflight_succeeds_when_matched(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = load_config(self._write(td, run_class="publication", poll=250))
            f = preflight(cfg, server_probe=health(250, source="env"))
            self.assertEqual(f["run_class"], "publication")
            self.assertEqual(f["server_runtime"]["effective_mastra_poll_interval_ms"], 250)
            self.assertTrue(f["server_runtime"]["verified"])

    def test_run_class_is_frozen_into_the_run_record(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = load_config(self._write(td, run_class="publication", poll=250))
            out = run_experiment(cfg, transport=MockTransport({}), sleep=lambda *_: None,
                                 server_probe=health(250, source="env"))
            exp = json.loads((Path(out["run_dir"]) / "experiment.json").read_text())
            self.assertEqual(exp["run_class"], "publication")

    def test_run_class_is_never_inferred_from_the_experiment_id(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = load_config(self._write(td, eid="rq1_publication_full_dreaddit"))
            self.assertEqual(cfg.run_class, "benchmark")
            self.assertIsNone(cfg.server.mastra_poll_interval_ms)

    def test_hash_compat_defaults_match_load_config(self):
        """Every entry must state the value load_config produces when the key is
        absent. If they drift, an old config silently changes hash."""
        with tempfile.TemporaryDirectory() as td:
            cfg = load_config(self._write(td))
            for path, default in HASH_COMPAT_DEFAULTS.items():
                node = cfg
                for part in path:
                    node = getattr(node, part)
                with self.subTest(path=path):
                    self.assertEqual(node, default)

    def test_omitting_a_post_change_key_hashes_as_before(self):
        with tempfile.TemporaryDirectory() as td:
            bare = load_config(self._write(td, eid="a"))
            explicit = load_config(self._write(td, eid="a", run_class="benchmark"))
            self.assertEqual(bare.config_sha256(), explicit.config_sha256(),
                             "declaring the default must hash like omitting it")

    def test_non_default_values_do_change_the_hash(self):
        with tempfile.TemporaryDirectory() as td:
            bare = load_config(self._write(td, eid="b"))
            pub = load_config(self._write(td, eid="b", run_class="publication", poll=3000))
            smoke = load_config(self._write(td, eid="b", run_class="smoke"))
            poll_only = load_config(self._write(td, eid="b", poll=3000))
            h = bare.config_sha256()
            self.assertNotEqual(h, pub.config_sha256())
            self.assertNotEqual(h, smoke.config_sha256())
            self.assertNotEqual(h, poll_only.config_sha256())
            self.assertNotEqual(pub.config_sha256(), poll_only.config_sha256())

    def test_completed_run_hashes_are_unchanged(self):
        cfgs = REPO_ROOT / "evaluation/publication_experiments/configs"
        runs = REPO_ROOT / "evaluation/publication_experiments/runs"
        for name in ["smoke_001", "bench_002_qwen_qwen3.5-27b",
                     "bench_003_official_dreaddit_qwen", "bench_004_official_dreaddit_qwen",
                     "bench_005_poll250_dreaddit_qwen"]:
            cfg_p, run_p = cfgs / f"{name}.yaml", runs / name / "experiment.json"
            if not (cfg_p.exists() and run_p.exists()):
                continue
            with self.subTest(cfg=name):
                recorded = json.loads(run_p.read_text())["config_sha256"]
                self.assertEqual(load_config(cfg_p).config_sha256(), recorded)

    def test_every_shipped_config_still_loads(self):
        cfgs = sorted((REPO_ROOT / "evaluation/publication_experiments/configs").glob("*.yaml"))
        self.assertGreaterEqual(len(cfgs), 10)
        for p in cfgs:
            with self.subTest(cfg=p.name):
                load_config(p)


if __name__ == "__main__":
    unittest.main(verbosity=2)
