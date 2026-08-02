"""
src/label_mapping.py

Maps raw dataset label columns to normalized labels used for metric computation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DREADDIT (RQ1 — binary stress classification)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
label column: "label"
Values: 0 (no stress) or 1 (stress). Already integers; cast from str if needed.

Two candidate mappings are documented; MAPPING_A is used by default.

  MAPPING_A — referralLevel (full-pipeline output, what the system recommends)
  ─────────────────────────────────────────────────────────────────────────────
  Predicted:  referralLevel from /evaluate: "low" | "moderate" | "urgent"
  Map:        "low"                    → predicted 0 (no stress detected)
              "moderate" or "urgent"   → predicted 1 (stress / elevated concern)
  Source:     report_parser.extract_stress_label()
  Validity:   Measures the end-to-end pipeline's ability to route stressed vs
              non-stressed texts to the appropriate referral tier. This is the
              most policy-relevant mapping: the system's actual output IS a
              referral recommendation, not a stress label.
  Limitation: referralLevel is derived from the Referral Agent's riskLevel
              AND from the safety check. A benign text could become "moderate"
              if the Referral Agent over-estimates risk, or "low" could be
              incorrect if the text is subtle. The mapping does not let us
              distinguish Referral Agent error from Report step error.

  MAPPING_B — Emotion Agent output (per-agent diagnostic)
  ─────────────────────────────────────────────────────────────────────────────
  Predicted:  first element of the "emotions" list in the Emotion Agent's raw
              JSON output (e.g. {"emotions": ["stress", "anxiety"], ...})
  Map:        "stress" or "anxiety" in emotions list → predicted 1
              empty list or no distress emotion       → predicted 0
  Source:     report_parser.extract_stress_label_from_emotion_json()
  Validity:   Directly tests whether the Emotion Agent identifies stress/anxiety
              without the Referral Agent's risk-level logic intervening. Useful
              for isolating which layer makes errors, but not the pipeline's
              actual output — the final referral decision also uses symptom,
              context, and retrieval evidence.
  Limitation: Emotion Agent outputs are not returned by the current /evaluate
              endpoint. Requires adding "emotion_agent_raw" to the server
              response (see task #51). This mapping should be treated as a
              secondary diagnostic measure until the server is updated.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GOEMOTIONS (RQ2 — emotion detection)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
label column: "emotion_names"
Values: stored as Python list-literal strings, e.g. "['nervousness']".
Parsed with ast.literal_eval → list of str → take first element.

The AnxioSense Emotion Agent outputs from this closed vocabulary:
    anxiety, stress, sadness, frustration, fear, hopelessness, loneliness

Design decision — include a NON-DISTRESS class
──────────────────────────────────────────────
The previous mapping excluded neutral/joy/relief rows entirely.  This is
methodologically incorrect: if the model predicts "anxiety" on a neutral or
joyful text, that is a false positive, and omitting such rows inflates
precision artificially.

The corrected mapping introduces "non_distress" as an explicit ground-truth
class for neutral, joy, and relief.  A false alarm (model predicts any distress
emotion on a non_distress text) now reduces precision.  Rows where the model
produces no emotions ("emotions": []) and the ground truth is non_distress are
counted as true negatives.

GOEMOTIONS_TO_ANXIOSENSE mapping (final):
    nervousness    → "anxiety"       (closest GoEmotions label to anxiety)
    fear           → "fear"          (direct)
    sadness        → "sadness"       (direct)
    grief          → "sadness"       (grief is extreme sadness)
    anger          → "frustration"   (anger → frustration in AnxioSense vocab)
    annoyance      → "frustration"   (mild anger)
    disappointment → "sadness"       (loss/unmet expectation)
    neutral        → "non_distress"  (model should produce [] or no distress emotion)
    joy            → "non_distress"  (positive affect — model should NOT predict distress)
    relief         → "non_distress"  (positive/neutral — model should NOT predict distress)

Evaluation logic for GoEmotions:
  ground_truth = map_goemotions_label(row["emotion_names"])
    → one of: "anxiety", "fear", "sadness", "frustration", "non_distress"
  predicted    = primary emotion from Emotion Agent JSON emotions list
    → one of: "anxiety", "stress", "sadness", "frustration", "fear",
              "hopelessness", "loneliness",  OR "non_distress" (when list is empty)
  Then: map predicted AnxioSense emotions to the same 5-class space for comparison.

Class alignment (ground-truth → evaluated class):
    "anxiety"      ← ground truth; Emotion Agent must output "anxiety"
    "fear"         ← ground truth; Emotion Agent must output "fear"
    "sadness"      ← ground truth; Emotion Agent must output "sadness"
    "frustration"  ← ground truth; Emotion Agent must output "frustration"
    "non_distress" ← ground truth; Emotion Agent must output [] / no distress emotion

Predicted "stress" → treated as "anxiety" for comparison (closest AnxioSense class).
Predicted "hopelessness" or "loneliness" → treated as "sadness" (no GoEmotions GT equiv).
"""

from __future__ import annotations

import ast
from typing import Optional


# ---------------------------------------------------------------------------
# Dreaddit
# ---------------------------------------------------------------------------

DREADDIT_VALUES = {0, 1, "0", "1"}


class LabelMappingError(ValueError):
    """Raised when a label value cannot be mapped."""


def map_dreaddit_label(raw: object) -> int:
    """
    Map a raw Dreaddit label value to 0 or 1.

    Parameters
    ----------
    raw: int or str — the value from the 'label' column.

    Returns
    -------
    int: 0 (no stress) or 1 (stress).

    Raises
    ------
    LabelMappingError if the value is not a recognized Dreaddit label.
    """
    if raw in (0, "0"):
        return 0
    if raw in (1, "1"):
        return 1
    raise LabelMappingError(
        f"Unknown Dreaddit label: {raw!r}. Expected 0 or 1 (int or str)."
    )


# ---------------------------------------------------------------------------
# GoEmotions → AnxioSense (5-class space including non_distress)
# ---------------------------------------------------------------------------

# Full mapping. "non_distress" is an explicit class, not None.
# This ensures false positives on neutral/joy/relief reduce precision.
GOEMOTIONS_TO_ANXIOSENSE: dict[str, str] = {
    "nervousness":    "anxiety",
    "fear":           "fear",
    "sadness":        "sadness",
    "grief":          "sadness",
    "anger":          "frustration",
    "annoyance":      "frustration",
    "disappointment": "sadness",
    "neutral":        "non_distress",
    "joy":            "non_distress",
    "relief":         "non_distress",
}

# Mapping from AnxioSense predicted emotion → evaluation class.
# "stress" is the only AnxioSense emotion with no direct GoEmotions GT;
# it is closest to "anxiety". hopelessness/loneliness → "sadness".
ANXIOSENSE_TO_EVAL_CLASS: dict[str, str] = {
    "anxiety":      "anxiety",
    "stress":       "anxiety",        # closest AnxioSense class to nervousness
    "sadness":      "sadness",
    "frustration":  "frustration",
    "fear":         "fear",
    "hopelessness": "sadness",        # no GoEmotions GT equivalent; closest = sadness
    "loneliness":   "sadness",        # no GoEmotions GT equivalent; closest = sadness
}

# The full 5-class label space used for evaluation
EVAL_CLASSES = ("anxiety", "fear", "sadness", "frustration", "non_distress")


def parse_goemotions_label(raw: object) -> Optional[str]:
    """
    Parse the emotion_names column (stored as a Python list literal string)
    and return the first emotion name.

    Returns None for empty lists only.

    Examples
    --------
    >>> parse_goemotions_label("['nervousness']")
    'nervousness'
    >>> parse_goemotions_label("['neutral']")
    'neutral'
    >>> parse_goemotions_label("[]")
    None
    """
    text = str(raw).strip()
    try:
        parsed = ast.literal_eval(text)
    except (ValueError, SyntaxError) as exc:
        raise LabelMappingError(
            f"Cannot parse GoEmotions label: {raw!r}. Expected a Python list literal."
        ) from exc

    if not isinstance(parsed, list) or len(parsed) == 0:
        return None
    return str(parsed[0])


def map_goemotions_label(raw: object) -> str:
    """
    Parse GoEmotions emotion_names and map to the 5-class evaluation space.

    Returns one of: "anxiety", "fear", "sadness", "frustration", "non_distress".

    Unlike the previous version, this function NEVER returns None.
    neutral/joy/relief map to "non_distress" so that false positives on
    those texts reduce model precision.

    Raises LabelMappingError if the raw value cannot be parsed or the
    parsed emotion is not in the known mapping table.
    """
    emotion = parse_goemotions_label(raw)
    if emotion is None:
        # Empty emotion list in the dataset — treat as non_distress
        return "non_distress"
    if emotion not in GOEMOTIONS_TO_ANXIOSENSE:
        raise LabelMappingError(
            f"Unknown GoEmotions emotion: {emotion!r}. "
            f"Known emotions: {list(GOEMOTIONS_TO_ANXIOSENSE.keys())}"
        )
    return GOEMOTIONS_TO_ANXIOSENSE[emotion]


def map_anxiosense_prediction_to_eval_class(predicted_emotion: Optional[str]) -> str:
    """
    Map an AnxioSense Emotion Agent predicted emotion to the 5-class eval space.

    Parameters
    ----------
    predicted_emotion: str from the Emotion Agent's "emotions" list, or None
        if the list was empty (model detected no emotion).

    Returns
    -------
    str: one of EVAL_CLASSES. Empty / None prediction → "non_distress".
    """
    if predicted_emotion is None or str(predicted_emotion).strip() == "":
        return "non_distress"
    lower = str(predicted_emotion).lower().strip()
    if lower not in ANXIOSENSE_TO_EVAL_CLASS:
        # Unknown predicted emotion (model hallucinated a label not in its vocab)
        # Treat as a parse failure — caller should record as failure_reason
        raise LabelMappingError(
            f"Unknown AnxioSense predicted emotion: {predicted_emotion!r}. "
            f"Known: {list(ANXIOSENSE_TO_EVAL_CLASS.keys())}"
        )
    return ANXIOSENSE_TO_EVAL_CLASS[lower]
