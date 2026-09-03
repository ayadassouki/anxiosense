"""Deterministic mock transport. No network, no provider, no cost.

Scenarios are chosen by sample_id so a mock run is byte-reproducible.
Every fixture is a realistic /evaluate response or transport failure.
"""
from __future__ import annotations
import itertools
from .client import TransportResult

SCENARIOS = (
    "valid_prediction", "valid_empty_emotions", "malformed_complete",
    "truncated_emotion", "oov_emotion", "http_429_then_ok",
    "http_500", "timeout", "referral_unreadable", "model_mismatch",
)


def _ok_body(*, referral_level, referral_raw, emotion_raw,
             model="microsoft/phi-4", unreadable=False, safety=False):
    return {
        "report": {
            "finalReport": "## Supporting Findings\n- placeholder\n",
            "concernPattern": "Elevated Concern Pattern",
            "referralLevel": referral_level,
            "summary": "placeholder",
        },
        "referral_unreadable": unreadable,
        "emotion_agent_raw": emotion_raw,
        "referral_agent_raw": referral_raw,
        "symptom_agent_raw": '{"possible_anxiety_indicators":[]}',
        "context_agent_raw": '{"contextual_stressors":[]}',
        "mastra_run_id": "mock-run-0001",
        "metadata": {
            "model_requested": model, "model_actual": model,
            "provider_actual": "openrouter", "upstream_provider": "DeepInfra",
            "upstream_providers": ["DeepInfra"], "strategy_used": "zero-shot",
            "evaluation_mode": True, "latency_ms": 1200,
            "token_usage": {"input_tokens": 5200, "output_tokens": 410},
            "safety_override": safety, "safety_category": None,
            "quality_flags": {"agent_json_parse_failed": False,
                              "fallback_claim_injected": False,
                              "referral_risk_fallback_used": unreadable,
                              "recommendation_rejected": False},
        },
    }


FIXTURES = {
    "valid_prediction": lambda: TransportResult(
        200, _ok_body(referral_level="moderate",
                      referral_raw='{"risk_level":"moderate","reasoning":"x"}',
                      emotion_raw='{"emotions":["anxiety"],"emotional_intensity":"high","evidence_from_text":[]}'),
        None, None, None, 1200.0),
    "valid_empty_emotions": lambda: TransportResult(
        200, _ok_body(referral_level="low",
                      referral_raw='{"risk_level":"low","reasoning":"x"}',
                      emotion_raw='{"emotions":[],"emotional_intensity":"low","evidence_from_text":[]}'),
        None, None, None, 900.0),
    "malformed_complete": lambda: TransportResult(
        200, _ok_body(referral_level=None, unreadable=True,
                      referral_raw='{"risk_level":"low","reasoning\\":\\"broken escaping',
                      emotion_raw='not json at all, just prose about feelings'),
        None, None, None, 1500.0),
    "truncated_emotion": lambda: TransportResult(
        200, _ok_body(referral_level="low",
                      referral_raw='{"risk_level":"low","reasoning":"x"}',
                      emotion_raw='{"emotions":["anx' + ("y" * 700)),
        None, None, None, 1500.0),
    "oov_emotion": lambda: TransportResult(
        200, _ok_body(referral_level="moderate",
                      referral_raw='{"risk_level":"moderate","reasoning":"x"}',
                      emotion_raw='{"emotions":["worried"],"emotional_intensity":"moderate","evidence_from_text":[]}'),
        None, None, None, 1100.0),
    "referral_unreadable": lambda: TransportResult(
        200, _ok_body(referral_level=None, unreadable=True,
                      referral_raw='Here is my assessment in prose, no JSON object at all.',
                      emotion_raw='{"emotions":["stress"],"emotional_intensity":"moderate","evidence_from_text":[]}'),
        None, None, None, 1300.0),
    "http_500": lambda: TransportResult(500, None, '{"error":"upstream"}', None, "HTTP 500", 400.0),
    "http_429": lambda: TransportResult(429, None, '{"error":"rate limited"}', None, "HTTP 429", 120.0),
    "timeout": lambda: TransportResult(None, None, None, "timeout", "timed out", 90000.0),
    "http_400": lambda: TransportResult(400, None, '{"error":"too short"}', None, "HTTP 400", 60.0),
    "model_mismatch": lambda: TransportResult(
        200, _ok_body(referral_level="low", model="groq/llama-3.3-70b-versatile",
                      referral_raw='{"risk_level":"low","reasoning":"x"}',
                      emotion_raw='{"emotions":[],"emotional_intensity":"low","evidence_from_text":[]}'),
        None, None, None, 800.0),
    "safety_intercept": lambda: TransportResult(
        200, _ok_body(referral_level="urgent", safety=True, referral_raw=None, emotion_raw=None),
        None, None, None, 15.0),
}


class MockTransport:
    """Serves a scripted scenario per sample_id.

    `scripts` maps sample_id -> list of fixture names, consumed one per attempt,
    so retry behaviour (e.g. 429 then success) is exercised deterministically.
    """

    def __init__(self, scripts: dict[str, list[str]], default: str = "valid_prediction"):
        self.scripts = {k: itertools.chain(v) for k, v in scripts.items()}
        self._remaining = {k: list(v) for k, v in scripts.items()}
        self.default = default
        self.calls: list[dict] = []

    def post_evaluate(self, *, text: str, model: str, strategy: str) -> TransportResult:
        sid = getattr(self, "_current_sample_id", None)
        self.calls.append({"sample_id": sid, "model": model, "strategy": strategy,
                           "text_len": len(text)})
        queue = self._remaining.get(sid)
        name = queue.pop(0) if queue else self.default
        return FIXTURES[name]()

    def set_sample(self, sample_id: str) -> None:
        self._current_sample_id = sample_id
