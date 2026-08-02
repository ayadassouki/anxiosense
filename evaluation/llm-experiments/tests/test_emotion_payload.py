"""
tests/test_emotion_payload.py

Tests for the robust tri-state Emotion Agent payload parser.

The cases below are drawn from the ACTUAL malformed payloads observed in the
Stage C GoEmotions outputs, so this suite is a regression guard against the
specific defects that invalidated that run.

The central invariant under test:

    an empty emotions list is a VALID prediction, NOT a parse failure

Conflating the two is what collapsed the Stage C GoEmotions parse rate to
35/300, because 71% of that test sample's ground truth is non_distress.
"""

import pytest

from src.emotion_payload import (
    OK_STATUSES,
    extract_emotion_payload,
    primary_emotion,
)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_clean_json_with_emotions():
    status, emotions = extract_emotion_payload(
        '{"emotions": ["anxiety"], "emotional_intensity": "moderate", "evidence_from_text": []}'
    )
    assert status == "ok_json"
    assert emotions == ["anxiety"]
    assert primary_emotion(emotions) == "anxiety"


def test_clean_json_empty_list_is_success_not_failure():
    """The core regression: [] must parse successfully, not fail."""
    status, emotions = extract_emotion_payload(
        '{"emotions": [], "emotional_intensity": "low", "evidence_from_text": []}'
    )
    assert status in OK_STATUSES
    assert emotions == []
    # None here means "no emotion detected" → caller maps to non_distress.
    assert primary_emotion(emotions) is None


# ---------------------------------------------------------------------------
# Formatting the strict parser rejected
# ---------------------------------------------------------------------------

def test_markdown_code_fence():
    status, emotions = extract_emotion_payload(
        '```\n{\n  "emotions": ["sadness"],\n  "emotional_intensity": "high"\n}\n```'
    )
    assert status in OK_STATUSES
    assert emotions == ["sadness"]


def test_json_fence_with_language_tag():
    status, emotions = extract_emotion_payload(
        '```json\n{"emotions": ["fear"], "emotional_intensity": "high"}\n```'
    )
    assert status in OK_STATUSES
    assert emotions == ["fear"]


def test_chain_of_thought_prose_before_json():
    """Expected output shape for the two CoT strategies under test."""
    status, emotions = extract_emotion_payload(
        "Step 1 — Read the text carefully.\nThe user expresses irritation.\n\n"
        "Here is the analysis:\n\n"
        '{"emotions": ["frustration"], "emotional_intensity": "moderate"}'
    )
    assert status == "ok_embedded"
    assert emotions == ["frustration"]


def test_prose_before_and_after_json():
    status, emotions = extract_emotion_payload(
        'Based on the text:\n```\n{"emotions": [], "emotional_intensity": ""}\n```\n'
        "The text shows no emotional indicators."
    )
    assert status in OK_STATUSES
    assert emotions == []


def test_braces_inside_evidence_strings_do_not_break_extraction():
    status, emotions = extract_emotion_payload(
        'Here it is:\n{"emotions": ["stress"], "evidence_from_text": ["use {braces} here"]}'
    )
    assert status in OK_STATUSES
    assert emotions == ["stress"]


# ---------------------------------------------------------------------------
# Transport corruption repair
# ---------------------------------------------------------------------------

def test_repairs_dropped_leading_brace_quote():
    """Observed corruption: the leading '{"' is dropped from the payload."""
    status, emotions = extract_emotion_payload(
        'emotions":[],"emotional_intensity":"low","evidence_from_text":[]}'
    )
    assert status == "ok_repaired"
    assert emotions == []


def test_repairs_dropped_prefix_with_emotion_present():
    status, emotions = extract_emotion_payload(
        'emotions":["frustration"],"_intensity":"moderate","evidence_from_text":[]}'
    )
    assert status == "ok_repaired"
    assert primary_emotion(emotions) == "frustration"


# ---------------------------------------------------------------------------
# Genuine failures — must NOT be silently recovered
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload", [None, "", "   ", "null", "{}"])
def test_absent_payloads(payload):
    status, emotions = extract_emotion_payload(payload)
    assert status == "fail_absent"
    assert emotions is None


def test_model_refusal_is_a_failure():
    status, emotions = extract_emotion_payload("I can’t help with that.")
    assert status not in OK_STATUSES
    assert emotions is None


def test_markdown_bold_instead_of_json_is_a_failure():
    """A real Stage C case: the agent ignored the JSON contract entirely."""
    status, emotions = extract_emotion_payload(
        "Here is the analysis:\n\n**emotions**: []\n**emotional_intensity**: \"low\""
    )
    assert status not in OK_STATUSES


def test_truncated_mid_array_is_not_read_as_empty():
    """
    Critical: a payload cut off inside the emotions array must fail, never be
    mistaken for an empty list. Reading it as [] would fabricate a non_distress
    prediction the model never made.
    """
    payload = '{"emotions": ["anxi' + "x" * 600
    status, emotions = extract_emotion_payload(payload)
    assert status not in OK_STATUSES
    assert emotions is None


def test_truncated_payload_is_reported_as_truncated():
    payload = "Step 1 — reasoning about the text. " + "y" * 600
    status, _ = extract_emotion_payload(payload)
    assert status == "fail_truncated"


def test_array_only_salvage_requires_closing_bracket():
    """Complete array after truncation point → salvageable."""
    payload = '"emotions": [], "emotional_intensity": "lo' + "z" * 600
    status, emotions = extract_emotion_payload(payload)
    assert status in OK_STATUSES
    assert emotions == []


# ---------------------------------------------------------------------------
# primary_emotion behaviour
# ---------------------------------------------------------------------------

def test_primary_emotion_lowercases():
    assert primary_emotion(["Frustration"]) == "frustration"
    assert primary_emotion(["  Sadness  "]) == "sadness"


def test_primary_emotion_handles_empty_and_bad_types():
    assert primary_emotion([]) is None
    assert primary_emotion(None) is None
    assert primary_emotion([123]) is None


def test_out_of_vocab_emotion_is_returned_verbatim():
    """
    Vocabulary enforcement belongs to the caller, not the parser. The parser's
    job is faithful extraction; the caller decides how to count a contract
    violation.
    """
    status, emotions = extract_emotion_payload('{"emotions": ["nostalgia"]}')
    assert status in OK_STATUSES
    assert primary_emotion(emotions) == "nostalgia"
