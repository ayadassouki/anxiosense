"""
tests/test_report_parser.py

Offline unit tests for src/report_parser.py.
No API calls, no network access. All inputs are in-memory mock dicts.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "evaluation" / "llm-experiments"))

from src.report_parser import (
    extract_stress_label,
    extract_emotion_label,
    extract_emotion_label_from_agent_json,
)


# ---------------------------------------------------------------------------
# Helpers: factory functions for mock report_dict objects
# ---------------------------------------------------------------------------

def _make_evaluate_response(
    referral_level: str = "moderate",
    concern_pattern: str = "Elevated Concern Pattern",
    final_report: str = "",
    safety_override: bool = False,
) -> dict:
    """Build a mock /api/workflow/evaluate response dict."""
    return {
        "report": {
            "finalReport":    final_report,
            "concernPattern": concern_pattern,
            "referralLevel":  referral_level,
            "summary":        "Test summary.",
        },
        "metadata": {
            "model_used":      "groq/llama-3.3-70b-versatile",
            "strategy_used":   "one-shot-cot",
            "latency_ms":      5000,
            "token_usage":     {"prompt_tokens": 0, "completion_tokens": 0},
            "safety_override": safety_override,
        },
    }


def _make_report_with_findings(findings_text: str) -> str:
    """Build a minimal finalReport markdown string with a Supporting Findings section."""
    return (
        "# AnxioSense Screening Support Report\n\n"
        "## Assessment Overview\n\nSome overview text.\n\n"
        "## Supporting Findings\n\n"
        f"{findings_text}\n\n"
        "## Recommendation\n\nSome recommendation.\n\n"
        "## Limitations\n\nThis report is intended for screening support only, "
        "is not a clinical diagnosis, and cannot replace a comprehensive assessment "
        "by a qualified healthcare professional."
    )


# ---------------------------------------------------------------------------
# extract_stress_label — Dreaddit binary
# ---------------------------------------------------------------------------

class TestExtractStressLabel:
    def test_low_referral_gives_0(self):
        rd = _make_evaluate_response(referral_level="low", concern_pattern="Minimal Concern Pattern")
        assert extract_stress_label(rd) == 0

    def test_moderate_referral_gives_1(self):
        rd = _make_evaluate_response(referral_level="moderate", concern_pattern="Elevated Concern Pattern")
        assert extract_stress_label(rd) == 1

    def test_urgent_referral_gives_1(self):
        rd = _make_evaluate_response(referral_level="urgent", concern_pattern="Urgent Safety Notice",
                                     safety_override=True)
        assert extract_stress_label(rd) == 1

    def test_missing_report_block_returns_none(self):
        # Dict with no "report" or "referralLevel" key
        assert extract_stress_label({}) is None

    def test_none_input_returns_none(self):
        assert extract_stress_label(None) is None

    def test_unrecognised_referral_level_returns_none(self):
        rd = _make_evaluate_response(referral_level="elevated")  # not a valid value
        assert extract_stress_label(rd) is None

    def test_raw_run_response_shape_also_works(self):
        """Support the flat /api/workflow/run response shape as well."""
        raw_run = {
            "finalReport":    "Some report text",
            "concernPattern": "Elevated Concern Pattern",
            "referralLevel":  "moderate",
            "summary":        "Summary.",
        }
        assert extract_stress_label(raw_run) == 1

    def test_returns_int_type(self):
        rd = _make_evaluate_response(referral_level="low")
        result = extract_stress_label(rd)
        assert isinstance(result, int)

    def test_high_concern_pattern_still_maps_via_referral(self):
        # concernPattern "High Concern Pattern" maps to referralLevel "moderate" in the server
        rd = _make_evaluate_response(referral_level="moderate", concern_pattern="High Concern Pattern")
        assert extract_stress_label(rd) == 1

    def test_mild_concern_pattern_maps_via_referral(self):
        # Mild concern → server sets referralLevel="moderate" (pipeline can do this)
        rd = _make_evaluate_response(referral_level="moderate", concern_pattern="Mild Concern Pattern")
        assert extract_stress_label(rd) == 1

    def test_empty_string_referral_returns_none(self):
        rd = _make_evaluate_response(referral_level="")
        assert extract_stress_label(rd) is None


# ---------------------------------------------------------------------------
# extract_emotion_label — GoEmotions multiclass
# ---------------------------------------------------------------------------

class TestExtractEmotionLabel:
    # --- Supporting Findings section keyword detection ---

    def test_detects_anxiety_from_findings(self):
        fr = _make_report_with_findings(
            "The report identified the following experiences:\n"
            "- Persistent anxiety symptoms\n"
            "- Sleep disruption"
        )
        rd = _make_evaluate_response(final_report=fr, concern_pattern="Elevated Concern Pattern")
        assert extract_emotion_label(rd) == "anxiety"

    def test_detects_stress_from_findings(self):
        fr = _make_report_with_findings(
            "The report identified:\n"
            "- Significant stress indicators\n"
            "- Feeling overwhelmed"
        )
        rd = _make_evaluate_response(final_report=fr, concern_pattern="Elevated Concern Pattern")
        assert extract_emotion_label(rd) == "stress"

    def test_detects_sadness_from_findings(self):
        fr = _make_report_with_findings(
            "The report identified:\n"
            "- Sadness and low mood\n"
            "- Reduced motivation"
        )
        rd = _make_evaluate_response(
            final_report=fr,
            referral_level="low",
            concern_pattern="Mild Concern Pattern",
        )
        assert extract_emotion_label(rd) == "sadness"

    def test_detects_fear_from_findings(self):
        fr = _make_report_with_findings(
            "Indicators:\n"
            "- Persistent fear of harm\n"
            "- Dread of social situations"
        )
        rd = _make_evaluate_response(final_report=fr, concern_pattern="Elevated Concern Pattern")
        assert extract_emotion_label(rd) == "fear"

    def test_detects_frustration_from_findings(self):
        fr = _make_report_with_findings(
            "Indicators:\n"
            "- Marked frustration with daily tasks\n"
            "- Irritation with colleagues"
        )
        rd = _make_evaluate_response(final_report=fr, concern_pattern="Mild Concern Pattern")
        assert extract_emotion_label(rd) == "frustration"

    def test_detects_hopelessness_from_findings(self):
        fr = _make_report_with_findings(
            "Indicators:\n"
            "- Expressed feelings of hopelessness\n"
            "- Belief that nothing will improve"
        )
        rd = _make_evaluate_response(
            final_report=fr,
            referral_level="urgent",
            concern_pattern="Urgent Safety Notice",
        )
        assert extract_emotion_label(rd) == "hopelessness"

    def test_detects_loneliness_from_findings(self):
        fr = _make_report_with_findings(
            "Indicators:\n"
            "- Persistent loneliness\n"
            "- Social isolation"
        )
        rd = _make_evaluate_response(final_report=fr, concern_pattern="Mild Concern Pattern")
        assert extract_emotion_label(rd) == "loneliness"

    # --- "No indicators" phrasing → None ---

    def test_no_significant_indicators_returns_none(self):
        fr = _make_report_with_findings(
            "No significant anxiety-related indicators were identified in the provided text."
        )
        rd = _make_evaluate_response(
            final_report=fr,
            referral_level="low",
            concern_pattern="Minimal Concern Pattern",
        )
        assert extract_emotion_label(rd) is None

    def test_none_identified_returns_none(self):
        fr = _make_report_with_findings("none identified")
        rd = _make_evaluate_response(referral_level="low", concern_pattern="Minimal Concern Pattern",
                                     final_report=fr)
        assert extract_emotion_label(rd) is None

    # --- Fall back to concernPattern when no SF section ---

    def test_urgent_concern_pattern_fallback_gives_fear(self):
        rd = _make_evaluate_response(
            final_report="# Report\n\nNo SF section here.",
            referral_level="urgent",
            concern_pattern="Urgent Safety Notice",
        )
        assert extract_emotion_label(rd) == "fear"

    def test_high_concern_pattern_fallback_gives_anxiety(self):
        rd = _make_evaluate_response(
            final_report="# Report\n\nNo SF section here.",
            referral_level="moderate",
            concern_pattern="High Concern Pattern",
        )
        assert extract_emotion_label(rd) == "anxiety"

    def test_elevated_concern_pattern_fallback_gives_anxiety(self):
        rd = _make_evaluate_response(
            final_report="# Report\n\nNo SF section here.",
            referral_level="moderate",
            concern_pattern="Elevated Concern Pattern",
        )
        assert extract_emotion_label(rd) == "anxiety"

    def test_mild_concern_pattern_fallback_gives_anxiety(self):
        rd = _make_evaluate_response(
            final_report="",
            referral_level="moderate",
            concern_pattern="Mild Concern Pattern",
        )
        assert extract_emotion_label(rd) == "anxiety"

    def test_minimal_concern_pattern_fallback_gives_none(self):
        rd = _make_evaluate_response(
            final_report="",
            referral_level="low",
            concern_pattern="Minimal Concern Pattern",
        )
        assert extract_emotion_label(rd) is None

    # --- Edge cases ---

    def test_none_input_returns_none(self):
        assert extract_emotion_label(None) is None

    def test_empty_dict_returns_none(self):
        assert extract_emotion_label({}) is None

    def test_missing_report_block_returns_none(self):
        assert extract_emotion_label({"metadata": {}}) is None

    def test_hopelessness_detected_before_anxiety(self):
        # Report mentions both hopelessness and anxiety — hopelessness is more specific
        # and appears first in the keyword priority order.
        fr = _make_report_with_findings(
            "- Feelings of hopelessness and despair\n"
            "- Anxious thoughts about the future"
        )
        rd = _make_evaluate_response(final_report=fr, concern_pattern="High Concern Pattern")
        result = extract_emotion_label(rd)
        # hopelessness has higher priority than anxiety in _EMOTION_KEYWORDS
        assert result == "hopelessness"

    def test_raw_run_response_shape_also_works(self):
        """Support the flat /api/workflow/run response shape."""
        raw_run = {
            "finalReport": _make_report_with_findings("- Persistent anxiety indicators"),
            "concernPattern": "Elevated Concern Pattern",
            "referralLevel":  "moderate",
        }
        assert extract_emotion_label(raw_run) == "anxiety"

    # --- emotion_agent_raw primary path (task 51) ---

    def test_emotion_agent_raw_overrides_markdown(self):
        """When emotion_agent_raw is present, it is used instead of markdown parsing."""
        # Markdown would give 'anxiety', but the raw JSON says 'fear'.
        fr = _make_report_with_findings("- Persistent anxiety symptoms")
        rd = _make_evaluate_response(final_report=fr, concern_pattern="Elevated Concern Pattern")
        raw = '{"emotions": ["fear"], "emotional_intensity": "high", "evidence_from_text": []}'
        assert extract_emotion_label(rd, emotion_agent_raw=raw) == "fear"

    def test_emotion_agent_raw_empty_list_returns_none(self):
        """Empty emotions list → None (caller treats as non_distress)."""
        rd = _make_evaluate_response()
        raw = '{"emotions": [], "emotional_intensity": "low", "evidence_from_text": []}'
        assert extract_emotion_label(rd, emotion_agent_raw=raw) is None

    def test_emotion_agent_raw_none_falls_back_to_markdown(self):
        """When emotion_agent_raw is None, markdown fallback is used."""
        fr = _make_report_with_findings("- Significant stress indicators")
        rd = _make_evaluate_response(final_report=fr, concern_pattern="Elevated Concern Pattern")
        assert extract_emotion_label(rd, emotion_agent_raw=None) == "stress"

    def test_emotion_agent_raw_multiple_emotions_uses_first(self):
        """First element of emotions list is the primary prediction."""
        rd = _make_evaluate_response()
        raw = '{"emotions": ["sadness", "anxiety"], "emotional_intensity": "moderate", "evidence_from_text": []}'
        assert extract_emotion_label(rd, emotion_agent_raw=raw) == "sadness"


# ---------------------------------------------------------------------------
# extract_emotion_label_from_agent_json — standalone tests
# ---------------------------------------------------------------------------

class TestExtractEmotionLabelFromAgentJson:
    def test_returns_first_emotion(self):
        raw = '{"emotions": ["anxiety"], "emotional_intensity": "high", "evidence_from_text": []}'
        assert extract_emotion_label_from_agent_json(raw) == "anxiety"

    def test_returns_first_of_multiple_emotions(self):
        raw = '{"emotions": ["fear", "sadness"], "emotional_intensity": "high", "evidence_from_text": []}'
        assert extract_emotion_label_from_agent_json(raw) == "fear"

    def test_empty_list_returns_none(self):
        raw = '{"emotions": [], "emotional_intensity": "low", "evidence_from_text": []}'
        assert extract_emotion_label_from_agent_json(raw) is None

    def test_none_input_returns_none(self):
        assert extract_emotion_label_from_agent_json(None) is None

    def test_empty_string_returns_none(self):
        assert extract_emotion_label_from_agent_json("") is None

    def test_invalid_json_returns_none(self):
        assert extract_emotion_label_from_agent_json("{not valid json") is None

    def test_null_string_returns_none(self):
        assert extract_emotion_label_from_agent_json("null") is None

    def test_emotion_normalised_to_lowercase(self):
        raw = '{"emotions": ["Anxiety"], "emotional_intensity": "moderate", "evidence_from_text": []}'
        assert extract_emotion_label_from_agent_json(raw) == "anxiety"

    def test_stress_is_valid_vocab(self):
        raw = '{"emotions": ["stress"], "emotional_intensity": "moderate", "evidence_from_text": []}'
        assert extract_emotion_label_from_agent_json(raw) == "stress"

    def test_hopelessness_is_valid_vocab(self):
        raw = '{"emotions": ["hopelessness"], "emotional_intensity": "severe", "evidence_from_text": []}'
        assert extract_emotion_label_from_agent_json(raw) == "hopelessness"

    def test_loneliness_is_valid_vocab(self):
        raw = '{"emotions": ["loneliness"], "emotional_intensity": "moderate", "evidence_from_text": []}'
        assert extract_emotion_label_from_agent_json(raw) == "loneliness"

    def test_all_known_vocab_terms_accepted(self):
        from src.report_parser import _ANXIOSENSE_EMOTIONS
        for emotion in _ANXIOSENSE_EMOTIONS:
            raw = f'{{"emotions": ["{emotion}"], "emotional_intensity": "moderate", "evidence_from_text": []}}'
            result = extract_emotion_label_from_agent_json(raw)
            assert result == emotion, f"Failed for {emotion!r}: got {result!r}"

    def test_non_dict_json_returns_none(self):
        assert extract_emotion_label_from_agent_json('["anxiety"]') is None

    def test_missing_emotions_key_returns_none(self):
        raw = '{"emotional_intensity": "low", "evidence_from_text": []}'
        assert extract_emotion_label_from_agent_json(raw) is None
