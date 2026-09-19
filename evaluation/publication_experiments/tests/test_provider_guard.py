#!/usr/bin/env python3
"""Offline gate tests for the fail-closed provider guard. No network, no paid model.

Covers provider_pin_violated(), its wiring into the attempt record, and the
supersede restrictions the guard's abort path depends on.

Run:  python3 evaluation/publication_experiments/tests/test_provider_guard.py
"""
from __future__ import annotations
import sys, tempfile, types, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG_ROOT = HERE.parent
sys.path.insert(0, str(PKG_ROOT))

from runner.client import TransportResult                           # noqa: E402
from runner.failures import Transport                               # noqa: E402
from runner.run import provider_pin_violated, _attempt_record       # noqa: E402
from runner.store import RunStore, DuplicateAssessment              # noqa: E402


def _body(provider, providers_all, model_actual):
    """A minimal /evaluate response shaped like the real one."""
    return {
        "metadata": {
            "model_actual": model_actual,
            "provider_actual": "openrouter",
            "upstream_provider": provider,
            "upstream_providers": providers_all,
            "strategy_used": "one-shot-cot",
            "latency_ms": 9000,
            "token_usage": {},
            "quality_flags": {},
            "safety_override": False,
        },
        "report": {},
        "mastra_run_id": "run-id",
    }


def make_record(provider, providers_all, *, pin="CoreWeave",
                model_id="google/gemma-4-31b-it",
                model_actual="openrouter/google/gemma-4-31b-it",
                outcome=Transport.OK):
    """Build a real attempt record through the production builder."""
    cfg = types.SimpleNamespace(experiment_id="test_exp")
    frozen = {
        "prompt_inventory": {"prompt_set_sha256": "ps",
                             "strategies": {"one-shot-cot": {"emotion": "e"}}},
        "git_commit": "deadbeef",
        "config_sha256": "cfg",
        "server_runtime": {"effective_mastra_poll_interval_ms": 3000},
    }
    manifest = {"manifest_sha256": "m",
                "processed": {"sha256": "p", "text_column": "t"},
                "official_split": "test"}
    model = types.SimpleNamespace(id=model_id, provider="openrouter", pin_provider=pin)
    result = TransportResult(http_status=200,
                             body=_body(provider, providers_all, model_actual),
                             raw_body_text="{}", error_kind=None, error_detail=None,
                             latency_ms=9000.0)
    return _attempt_record(cfg=cfg, frozen=frozen, dataset="dreaddit", manifest=manifest,
                           sample_id="dread_1", text="hello world", gt=1, model=model,
                           strategy="one-shot-cot", run=5, assessment_uuid="a",
                           attempt_number=1, result=result, outcome=outcome, detail=None)


class TProviderPredicate(unittest.TestCase):
    """The pure predicate. A completed response must come from the pinned provider."""

    def test_1_pinned_provider_served_the_response(self):
        self.assertFalse(provider_pin_violated("CoreWeave", "CoreWeave", ["CoreWeave"]))

    def test_2_another_provider_served_the_response(self):
        self.assertTrue(provider_pin_violated("CoreWeave", "DeepInfra", ["DeepInfra"]))

    def test_3_no_upstream_call_never_trips(self):
        """SAFETY_INTERCEPT reaches no provider: upstream_provider None, list empty."""
        self.assertFalse(provider_pin_violated("CoreWeave", None, []))
        self.assertFalse(provider_pin_violated("CoreWeave", None, None))

    def test_4_any_non_pinned_provider_among_several_trips(self):
        self.assertTrue(
            provider_pin_violated("CoreWeave", "CoreWeave", ["CoreWeave", "DeepInfra"]))
        self.assertTrue(provider_pin_violated("CoreWeave", "MIXED", ["MIXED"]))

    def test_transport_failure_never_trips(self):
        self.assertFalse(provider_pin_violated("CoreWeave", None, []))

    def test_unpinned_model_never_trips(self):
        self.assertFalse(provider_pin_violated(None, "DeepInfra", ["DeepInfra"]))
        self.assertFalse(provider_pin_violated("", "DeepInfra", ["DeepInfra"]))

    def test_the_guard_is_not_coreweave_specific(self):
        self.assertFalse(provider_pin_violated("Alibaba", "Alibaba", ["Alibaba"]))
        self.assertTrue(provider_pin_violated("Alibaba", "DeepInfra", ["DeepInfra"]))
        self.assertFalse(provider_pin_violated("Mistral", "Mistral", ["Mistral"]))


class TProviderRecordWiring(unittest.TestCase):
    """The predicate must reach the stored attempt record."""

    def test_1_pinned_provider_record_is_clean(self):
        rec = make_record("CoreWeave", ["CoreWeave"])
        self.assertFalse(rec["provider_mismatch"])
        self.assertFalse(rec["model_mismatch"])

    def test_2_other_provider_record_is_flagged(self):
        rec = make_record("DeepInfra", ["DeepInfra"])
        self.assertTrue(rec["provider_mismatch"])
        self.assertFalse(rec["model_mismatch"])

    def test_3_safety_intercept_record_is_not_flagged(self):
        rec = make_record(None, [], outcome=Transport.SAFETY_INTERCEPT)
        self.assertFalse(rec["provider_mismatch"])
        self.assertEqual(rec["outcome_class"], Transport.SAFETY_INTERCEPT.value)

    def test_4_several_providers_record_is_flagged(self):
        rec = make_record("CoreWeave", ["CoreWeave", "DeepInfra"])
        self.assertTrue(rec["provider_mismatch"])

    def test_5_model_mismatch_is_unchanged_and_independent(self):
        wrong_model = make_record("CoreWeave", ["CoreWeave"],
                                  model_actual="openrouter/meta-llama/llama-4-scout")
        self.assertTrue(wrong_model["model_mismatch"])
        self.assertFalse(wrong_model["provider_mismatch"])
        both = make_record("DeepInfra", ["DeepInfra"],
                           model_actual="openrouter/meta-llama/llama-4-scout")
        self.assertTrue(both["model_mismatch"])
        self.assertTrue(both["provider_mismatch"])


class TSupersedeStaysRestricted(unittest.TestCase):
    """The abort path passes allow_supersede. That must NOT widen SUPERSEDABLE."""

    @staticmethod
    def _index_record(outcome, assessment_uuid="u1"):
        return {"record_type": "assessment", "assessment_uuid": assessment_uuid,
                "experiment_id": "e", "cell_id": "c", "dataset": "d", "sample_id": "s",
                "attempts": [], "attempt_count": 1, "terminal_attempt_uuid": "t",
                "final_outcome_class": outcome, "retry_history": []}

    def test_ok_is_never_supersedable(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RunStore(Path(tmp) / "run")
            store.close_assessment(self._index_record("OK"))
            with self.assertRaises(DuplicateAssessment):
                store.close_assessment(self._index_record("OK", "u2"), allow_supersede=True)
            store.close()

    def test_safety_intercept_is_never_supersedable(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RunStore(Path(tmp) / "run")
            store.close_assessment(self._index_record("SAFETY_INTERCEPT"))
            with self.assertRaises(DuplicateAssessment):
                store.close_assessment(self._index_record("SAFETY_INTERCEPT", "u2"),
                                       allow_supersede=True)
            store.close()

    def test_retries_exhausted_is_supersedable_only_with_the_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RunStore(Path(tmp) / "run")
            store.close_assessment(self._index_record("RETRIES_EXHAUSTED"))
            with self.assertRaises(DuplicateAssessment):
                store.close_assessment(self._index_record("OK", "u2"))
            store.close_assessment(self._index_record("OK", "u3"), allow_supersede=True)
            store.close()

    def test_abort_path_passes_allow_supersede(self):
        """Regression: the abort path used to omit it and raise DuplicateAssessment
        on a --resume --retry-exhausted pass instead of the intended PreflightError."""
        source = (PKG_ROOT / "runner" / "run.py").read_text(encoding="utf-8")
        start = source.index('if rec["model_mismatch"] or rec["provider_mismatch"]:')
        self.assertIn("allow_supersede=superseding", source[start:start + 900])


if __name__ == "__main__":
    unittest.main(verbosity=2)
