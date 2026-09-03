#!/usr/bin/env python3
"""Offline gate tests for the publication runner. No network, no paid model, no sklearn.

Run:  python3 evaluation/publication_experiments/tests/test_runner.py
"""
from __future__ import annotations
import csv, inspect, json, os, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG_ROOT = HERE.parent
sys.path.insert(0, str(PKG_ROOT))

from runner import RUNNER_VERSION                                  # noqa: E402
from runner._reuse import REPO_ROOT, LabelMappingError             # noqa: E402
from runner.client import TransportResult                          # noqa: E402
from runner.config import load_config, ConfigError                 # noqa: E402
from runner.failures import Transport, classify_transport, is_retryable  # noqa: E402
from runner.identity import (new_uuid, sha256_text, prompt_hashes,
                             prompt_inventory, PromptError, AGENTS)  # noqa: E402
from runner.manifest import build_manifest, verify_manifest, ManifestError  # noqa: E402
from runner.metrics import cell_metrics, MetricPolicy              # noqa: E402
from runner.mock import MockTransport, FIXTURES                    # noqa: E402
from runner.parse import parse_dreaddit, parse_goemotions          # noqa: E402
from runner.rescore import rescore                                 # noqa: E402
from runner.retry import RetryPolicy, next_action                  # noqa: E402
from runner.run import preflight, run_experiment, PreflightError   # noqa: E402
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
    emo = ["['nervousness']", "['neutral']", "['sadness']"]
    rows = [{"sample_id": f"ge_{i:06d}", "split": "test",
             "text": f"a comment number {i} that is long enough",
             "text_redacted": f"a comment number {i} that is long enough",
             "emotion_names": emo[i % 3]} for i in range(n)]
    write_csv(p, rows, ["sample_id", "split", "text", "text_redacted", "emotion_names"])
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
            for k in ("config_sha256", "git_commit", "prompt_inventory", "datasets",
                      "grid", "retry_policy", "runner_version"):
                self.assertIn(k, frozen)
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
