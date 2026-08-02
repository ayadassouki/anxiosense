"""
tests/test_label_mapping.py

Offline unit tests for src/label_mapping.py.
No API calls, no disk I/O.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "evaluation" / "llm-experiments"))

from src.label_mapping import (
    LabelMappingError,
    GOEMOTIONS_TO_ANXIOSENSE,
    map_dreaddit_label,
    map_goemotions_label,
    parse_goemotions_label,
)


# ---------------------------------------------------------------------------
# Dreaddit
# ---------------------------------------------------------------------------

class TestMapDreaddditLabel:
    def test_int_zero_maps_to_zero(self):
        assert map_dreaddit_label(0) == 0

    def test_int_one_maps_to_one(self):
        assert map_dreaddit_label(1) == 1

    def test_string_zero_maps_to_zero(self):
        assert map_dreaddit_label("0") == 0

    def test_string_one_maps_to_one(self):
        assert map_dreaddit_label("1") == 1

    def test_unknown_string_raises(self):
        with pytest.raises(LabelMappingError, match="Unknown Dreaddit label"):
            map_dreaddit_label("stress")

    def test_unknown_int_raises(self):
        with pytest.raises(LabelMappingError, match="Unknown Dreaddit label"):
            map_dreaddit_label(2)

    def test_none_raises(self):
        with pytest.raises(LabelMappingError):
            map_dreaddit_label(None)

    def test_float_1_accepted_due_to_python_numeric_equality(self):
        # In Python, 1.0 == 1 and hash(1.0) == hash(1), so 1.0 is treated as 1.
        # When pandas reads CSV integer labels, they may come as float. Accept them.
        assert map_dreaddit_label(1.0) == 1

    def test_float_0_accepted_due_to_python_numeric_equality(self):
        assert map_dreaddit_label(0.0) == 0

    def test_returns_int_not_bool(self):
        result = map_dreaddit_label(1)
        assert type(result) is int


# ---------------------------------------------------------------------------
# GoEmotions label parsing
# ---------------------------------------------------------------------------

class TestParseGoEmotionsLabel:
    def test_single_element_list(self):
        assert parse_goemotions_label("['nervousness']") == "nervousness"

    def test_fear(self):
        assert parse_goemotions_label("['fear']") == "fear"

    def test_neutral(self):
        assert parse_goemotions_label("['neutral']") == "neutral"

    def test_empty_list_returns_none(self):
        assert parse_goemotions_label("[]") is None

    def test_invalid_string_raises(self):
        with pytest.raises(LabelMappingError):
            parse_goemotions_label("not_a_list")

    def test_takes_first_element_for_multi(self):
        # Multi-label should not appear in single-label dataset,
        # but parser should still take first if given one.
        result = parse_goemotions_label("['fear', 'sadness']")
        assert result == "fear"


# ---------------------------------------------------------------------------
# GoEmotions → AnxioSense mapping
# ---------------------------------------------------------------------------

class TestMapGoEmotionsLabel:
    def test_nervousness_maps_to_anxiety(self):
        assert map_goemotions_label("['nervousness']") == "anxiety"

    def test_fear_maps_to_fear(self):
        assert map_goemotions_label("['fear']") == "fear"

    def test_sadness_maps_to_sadness(self):
        assert map_goemotions_label("['sadness']") == "sadness"

    def test_grief_maps_to_sadness(self):
        assert map_goemotions_label("['grief']") == "sadness"

    def test_anger_maps_to_frustration(self):
        assert map_goemotions_label("['anger']") == "frustration"

    def test_annoyance_maps_to_frustration(self):
        assert map_goemotions_label("['annoyance']") == "frustration"

    def test_disappointment_maps_to_sadness(self):
        assert map_goemotions_label("['disappointment']") == "sadness"

    def test_neutral_maps_to_non_distress(self):
        # Corrected mapping (task 50): neutral/joy/relief → "non_distress" (explicit class).
        # Previous design mapped these to None, which inflated precision by excluding
        # false positives on non-distress texts from evaluation.
        assert map_goemotions_label("['neutral']") == "non_distress"

    def test_joy_maps_to_non_distress(self):
        assert map_goemotions_label("['joy']") == "non_distress"

    def test_relief_maps_to_non_distress(self):
        assert map_goemotions_label("['relief']") == "non_distress"

    def test_empty_list_returns_non_distress(self):
        # Empty emotion list → "non_distress" (model detected no emotion in a non-distress text)
        assert map_goemotions_label("[]") == "non_distress"

    def test_unknown_emotion_raises(self):
        # Inject a label not in the mapping table
        with pytest.raises(LabelMappingError, match="Unknown GoEmotions emotion"):
            map_goemotions_label("['envy']")

    def test_all_known_labels_are_handled(self):
        """Every label in GOEMOTIONS_TO_ANXIOSENSE should not raise and should return a str."""
        for emotion in GOEMOTIONS_TO_ANXIOSENSE:
            raw = f"['{emotion}']"
            result = map_goemotions_label(raw)
            # All known labels must map to a string (never None)
            assert isinstance(result, str), f"Expected str for {emotion!r}, got {result!r}"
