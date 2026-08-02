"""
tests/test_response_parser.py

Offline unit tests for src/response_parser.py.
No API calls. Tests parsing of simulated LLM response strings.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "evaluation" / "llm-experiments"))

from src.response_parser import (
    ParseResult,
    parse_binary,
    parse_multiclass,
    parse_response,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_emotion_json(emotions: list, intensity: str = "low") -> str:
    return json.dumps({
        "emotions": emotions,
        "emotional_intensity": intensity,
        "evidence_from_text": [],
    })


def _make_emotion_json_fenced(emotions: list) -> str:
    return "```json\n" + _make_emotion_json(emotions) + "\n```"


# ---------------------------------------------------------------------------
# Binary parser (Dreaddit)
# ---------------------------------------------------------------------------

class TestParseBinary:
    # JSON schema responses
    def test_stress_in_json_gives_label_1(self):
        raw = _make_emotion_json(["stress"])
        result = parse_binary(raw)
        assert result.label == 1
        assert result.success

    def test_anxiety_only_gives_label_0(self):
        raw = _make_emotion_json(["anxiety"])
        result = parse_binary(raw)
        assert result.label == 0
        assert result.success

    def test_stress_and_anxiety_gives_label_1(self):
        raw = _make_emotion_json(["anxiety", "stress"])
        result = parse_binary(raw)
        assert result.label == 1

    def test_empty_emotions_gives_label_0(self):
        raw = _make_emotion_json([])
        result = parse_binary(raw)
        assert result.label == 0

    def test_fenced_json_parsed(self):
        raw = _make_emotion_json_fenced(["stress"])
        result = parse_binary(raw)
        assert result.label == 1

    def test_stress_case_insensitive(self):
        raw = _make_emotion_json(["Stress", "FEAR"])
        result = parse_binary(raw)
        assert result.label == 1

    # Fallback keyword matching
    def test_literal_1_gives_label_1(self):
        result = parse_binary("1")
        assert result.label == 1

    def test_literal_0_gives_label_0(self):
        result = parse_binary("0")
        assert result.label == 0

    def test_literal_stressed_gives_label_1(self):
        result = parse_binary("stressed")
        assert result.label == 1

    def test_literal_not_stressed_gives_label_0(self):
        result = parse_binary("not stressed")
        assert result.label == 0

    # Failures
    def test_none_response_is_failure(self):
        result = parse_binary(None)
        assert result.label is None
        assert result.failure_reason is not None
        assert not result.success

    def test_garbage_response_is_failure(self):
        result = parse_binary("the model returned something completely unexpected xyz")
        assert result.label is None
        assert result.failure_reason is not None
        assert not result.success

    def test_empty_string_is_failure(self):
        result = parse_binary("")
        assert result.label is None

    def test_json_without_emotions_key_is_failure(self):
        result = parse_binary('{"other_key": "value"}')
        assert result.label is None
        assert result.failure_reason is not None

    # Result properties
    def test_success_property_true_on_valid(self):
        result = parse_binary(_make_emotion_json(["stress"]))
        assert result.success is True

    def test_success_property_false_on_failure(self):
        result = parse_binary(None)
        assert result.success is False


# ---------------------------------------------------------------------------
# Multiclass parser (GoEmotions)
# ---------------------------------------------------------------------------

class TestParseMulticlass:
    def test_extracts_primary_emotion(self):
        raw = _make_emotion_json(["anxiety"])
        result = parse_multiclass(raw)
        assert result.label == "anxiety"
        assert result.success

    def test_extracts_first_emotion_from_multiple(self):
        raw = _make_emotion_json(["fear", "sadness"])
        result = parse_multiclass(raw)
        assert result.label == "fear"

    def test_empty_emotions_is_not_success(self):
        raw = _make_emotion_json([])
        result = parse_multiclass(raw)
        assert result.label is None
        # Empty list is a valid model output — failure_reason is set but it's informational
        assert "empty" in (result.failure_reason or "").lower()

    def test_none_response_is_failure(self):
        result = parse_multiclass(None)
        assert result.label is None
        assert result.failure_reason is not None

    def test_garbage_response_is_failure(self):
        result = parse_multiclass("not json at all blah blah")
        assert result.label is None
        assert result.failure_reason is not None

    def test_fenced_json_parsed(self):
        raw = _make_emotion_json_fenced(["sadness"])
        result = parse_multiclass(raw)
        assert result.label == "sadness"

    def test_emotion_normalized_to_lowercase(self):
        raw = _make_emotion_json(["Anxiety"])
        result = parse_multiclass(raw)
        assert result.label == "anxiety"


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

class TestParseResponse:
    def test_binary_task_type(self):
        raw = _make_emotion_json(["stress"])
        result = parse_response(raw, "binary")
        assert result.label == 1

    def test_multiclass_task_type(self):
        raw = _make_emotion_json(["fear"])
        result = parse_response(raw, "multiclass")
        assert result.label == "fear"

    def test_multilabel_task_type(self):
        raw = _make_emotion_json(["sadness"])
        result = parse_response(raw, "multilabel")
        assert result.label == "sadness"

    def test_unknown_task_type_raises(self):
        with pytest.raises(ValueError, match="Unknown task_type"):
            parse_response("something", "invalid_type")
