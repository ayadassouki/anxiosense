"""
src/report_parser.py

Extract comparable evaluation labels from an AnxioSense pipeline response.

The AnxioSense /api/workflow/evaluate endpoint returns a structured response
with these top-level fields:

    {
        "report": {
            "finalReport":    str,   # Markdown report string
            "concernPattern": str,   # "Minimal Concern Pattern" | "Mild Concern Pattern"
                                     # | "Elevated Concern Pattern" | "High Concern Pattern"
                                     # | "Urgent Safety Notice"
            "referralLevel":  str,   # "low" | "moderate" | "urgent"
            "summary":        str,
        },
        "emotion_agent_raw": str | None,  # Raw JSON from Emotion Agent (added in task #51)
        "metadata": {
            "model_used":      str,
            "strategy_used":   str,
            "latency_ms":      float,
            "token_usage":     dict,
            "safety_override": bool,
        },
    }

Three extraction functions are provided:

extract_stress_label(report_dict) -> int | None
    For Dreaddit (binary stress detection, RQ1/RQ2/RQ3).

    Mapping from referralLevel:
        "low"      → 0  (no stress / minimal concern)
        "moderate" → 1  (stress present — elevated or high concern pattern)
        "urgent"   → 1  (crisis level — safety override or urgent safety pattern)

    Rationale: the AnxioSense referral agent classifies texts with
    elevated/persistent anxiety symptoms as "moderate" risk. In the Dreaddit
    dataset, label=1 means "stressed", which corresponds to the presence of
    meaningful anxiety/stress signals — consistent with the "moderate" or higher
    referral level. The "low" label indicates minimal concern, consistent with
    Dreaddit label=0 (not stressed).

    Returns None if the referralLevel field is missing or unrecognised.

extract_emotion_label_from_agent_json(emotion_agent_raw) -> str | None
    PRIMARY GoEmotions prediction source.

    Parses the raw Emotion Agent JSON string (shape below) and returns the
    first element of the "emotions" list, or None if the list is empty.

        {"emotions": ["anxiety", "stress"], "emotional_intensity": "...",
         "evidence_from_text": [...]}

    Returns None on empty list, JSON parse failure, or None input.
    The caller must treat None as "non_distress" for evaluation purposes.

extract_emotion_label(report_dict, emotion_agent_raw=None) -> str | None
    For GoEmotions (multiclass emotion classification, RQ1/RQ2/RQ3).

    When emotion_agent_raw is provided, it is used as the PRIMARY source
    (via extract_emotion_label_from_agent_json). The markdown report is
    used only as a fallback when emotion_agent_raw is absent or unparseable.

    Emotion vocabulary (AnxioSense → returned label):
        anxiety      → "anxiety"
        stress       → "stress"
        sadness      → "sadness"
        fear         → "fear"
        frustration  → "frustration"
        hopelessness → "hopelessness"
        loneliness   → "loneliness"

    Ground-truth labels from GoEmotions are already mapped to this vocabulary
    by label_mapping.map_goemotions_label() before comparison, so labels are
    directly comparable.

    Fallback logic (markdown path, used only when emotion_agent_raw absent):
        1. Scan Supporting Findings section for emotion keyword clusters.
        2. If no specific emotion found, infer from concernPattern:
               "Urgent Safety Notice"     → "fear"
               "High Concern Pattern"     → "anxiety"
               "Elevated Concern Pattern" → "anxiety"
               "Mild Concern Pattern"     → "anxiety"
               "Minimal Concern Pattern"  → None  (no emotion detected)
        3. Return None if the report is missing or cannot be parsed.

    Returns None when no mappable emotion is found (treated as parse failure
    in the experiment runner — excluded from precision/recall, counted toward
    failure rate).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stress label extraction (Dreaddit binary)
# ---------------------------------------------------------------------------

def extract_stress_label(report_dict: Optional[dict]) -> Optional[int]:
    """
    Extract a binary stress label (0 or 1) from an AnxioSense response dict.

    Parameters
    ----------
    report_dict:
        The full JSON response from /api/workflow/evaluate, or None.

    Returns
    -------
    int: 1 (stressed) or 0 (not stressed).
    None if the response is missing or the referralLevel field is unrecognised.
    """
    if not report_dict or not isinstance(report_dict, dict):
        return None

    # Support both /api/evaluate response shape and raw /run response shape
    report_block = report_dict.get("report")
    if isinstance(report_block, dict):
        referral_level = report_block.get("referralLevel")
    else:
        # Raw /run shape: { "referralLevel": "...", "finalReport": "...", ... }
        referral_level = report_dict.get("referralLevel")

    if referral_level is None:
        return None

    referral_level = str(referral_level).strip().lower()

    if referral_level == "low":
        return 0
    if referral_level in ("moderate", "urgent"):
        return 1

    return None


# ---------------------------------------------------------------------------
# Emotion label extraction (GoEmotions multiclass)
# ---------------------------------------------------------------------------

# Known AnxioSense Emotion Agent output vocabulary
_ANXIOSENSE_EMOTIONS = frozenset({
    "anxiety", "stress", "sadness", "frustration",
    "fear", "hopelessness", "loneliness",
})


def extract_emotion_label_from_agent_json(
    emotion_agent_raw: Optional[str],
) -> Optional[str]:
    """
    PRIMARY source for GoEmotions evaluation.

    Parses the raw Emotion Agent JSON string returned in the /evaluate response
    as 'emotion_agent_raw', and returns the first element of the "emotions" list.

    The raw JSON has this shape:
        {
            "emotions":           ["anxiety", "stress"],   # may be empty
            "emotional_intensity": "moderate",
            "evidence_from_text":  [...]
        }

    Parameters
    ----------
    emotion_agent_raw:
        The raw JSON string from the Emotion Agent, or None.

    Returns
    -------
    str: the first emotion from the list (e.g. "anxiety"), or None when:
         - emotion_agent_raw is None or empty
         - the "emotions" list is empty (model detected no emotion)
         - JSON parsing fails
         - the parsed value is not a string in the known emotion vocabulary

    None is treated as "non_distress" by the caller for evaluation purposes.
    """
    if not emotion_agent_raw or not isinstance(emotion_agent_raw, str):
        return None

    raw = emotion_agent_raw.strip()
    if not raw or raw in ("null", "{}"):
        return None

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.debug("emotion_agent_raw JSON parse failure: %s | raw: %.120s", exc, raw)
        return None

    if not isinstance(parsed, dict):
        logger.debug("emotion_agent_raw is not a dict: %r", type(parsed).__name__)
        return None

    emotions = parsed.get("emotions")
    if not isinstance(emotions, list) or len(emotions) == 0:
        return None  # empty list → model detected no emotion → caller maps to non_distress

    first = emotions[0]
    if not isinstance(first, str):
        logger.debug("emotion_agent_raw emotions[0] is not a str: %r", first)
        return None

    lower = first.lower().strip()
    if lower not in _ANXIOSENSE_EMOTIONS:
        logger.debug(
            "emotion_agent_raw emotions[0] not in known vocab: %r", lower
        )
        # Return it anyway — label_mapping will raise LabelMappingError upstream
        # so the result is stored as a failure, not silently dropped.
        return lower

    return lower

# Keyword clusters for each AnxioSense emotion.
# Keys are in priority order: hopelessness/loneliness first (more specific),
# anxiety/stress last (most generic, avoid false positives).
_EMOTION_KEYWORDS: dict[str, list[str]] = {
    "hopelessness": [
        "hopeless", "worthless", "despair", "despairing", "no hope",
    ],
    "loneliness": [
        "lonely", "loneliness", "isolated", "isolation", "alone",
    ],
    "fear": [
        "fear", "fearful", "dread", "dreading", "scared", "terror",
        "terrifying", "phob",
    ],
    "sadness": [
        "sadness", "sad", "grief", "grieving", "low mood", "crying",
        "cried", "emotional pain", "depressed feelings",
    ],
    "frustration": [
        "frustration", "frustrated", "annoyance", "annoyed",
        "irritat", "anger", "angry",
    ],
    "stress": [
        "stress", "stressed", "strain", "overwhelmed", "overwhelm",
        "pressur", "burnout",
    ],
    "anxiety": [
        "anxiet", "anxious", "worry", "worri", "nervous", "unease",
        "restless", "panic", "persistent concern",
    ],
}

# Regex to extract the Supporting Findings section of the markdown report
_SF_RE = re.compile(
    r"##\s*Supporting\s+Findings\s*\n+(.*?)(?=\n##|\Z)",
    re.DOTALL | re.IGNORECASE,
)

# Phrases that indicate no emotion was detected in the report
_NO_INDICATOR_PHRASES = (
    "no significant anxiety-related indicators",
    "no significant indicators",
    "none identified",
    "no indicators were identified",
    "positive emotional tone",
    "stable functioning",
)


def extract_emotion_label(
    report_dict: Optional[dict],
    emotion_agent_raw: Optional[str] = None,
) -> Optional[str]:
    """
    Extract the primary emotion label from an AnxioSense response.

    Parameters
    ----------
    report_dict:
        The full JSON response from /api/workflow/evaluate, or None.
    emotion_agent_raw:
        Raw JSON string from the Emotion Agent (AnxioSenseResult.emotion_agent_raw).
        When provided, it is used as the PRIMARY prediction source.
        When absent/None, falls back to markdown report parsing.

    Returns
    -------
    str: one of {"anxiety", "stress", "sadness", "fear", "frustration",
                  "hopelessness", "loneliness"}.
    None if no mappable emotion was identified in the report.
    """
    # PRIMARY PATH — use raw Emotion Agent JSON when available.
    # This is the correct source: the Emotion Agent directly outputs its emotion
    # list in structured JSON, whereas the markdown report is a human-readable
    # synthesis that may rephrase or omit the primary emotion.
    if emotion_agent_raw is not None:
        result = extract_emotion_label_from_agent_json(emotion_agent_raw)
        # result is str or None; both are valid — None means empty emotions list.
        # We return here whether or not result is None; the fallback markdown path
        # should NOT be used when emotion_agent_raw was present but returned [].
        # A model that outputs [] on a non-distress text is CORRECT, not a failure.
        return result

    # FALLBACK PATH — markdown report parsing (used when emotion_agent_raw is absent,
    # i.e. old server builds without the emotion_agent_raw field).
    if not report_dict or not isinstance(report_dict, dict):
        return None

    # Support both /api/evaluate and raw /run response shapes
    report_block = report_dict.get("report")
    if isinstance(report_block, dict):
        final_report   = report_block.get("finalReport", "") or ""
        concern_pattern = report_block.get("concernPattern", "") or ""
    else:
        final_report   = report_dict.get("finalReport", "") or ""
        concern_pattern = report_dict.get("concernPattern", "") or ""

    if not isinstance(final_report, str):
        final_report = ""
    if not isinstance(concern_pattern, str):
        concern_pattern = ""

    # Step 1: Scan Supporting Findings section
    sf_match = _SF_RE.search(final_report)
    if sf_match:
        sf_text = sf_match.group(1).lower()

        # Check for "no indicators" phrases — no emotion detected
        for phrase in _NO_INDICATOR_PHRASES:
            if phrase in sf_text:
                return None

        # Scan for emotion keyword clusters
        for emotion, keywords in _EMOTION_KEYWORDS.items():
            for kw in keywords:
                if kw in sf_text:
                    return emotion

    # Step 2: Fall back to concernPattern inference
    cp_lower = concern_pattern.lower()

    if "urgent" in cp_lower:
        return "fear"
    if "high concern" in cp_lower:
        return "anxiety"
    if "elevated concern" in cp_lower:
        return "anxiety"
    if "mild concern" in cp_lower:
        return "anxiety"
    if "minimal concern" in cp_lower:
        return None   # No emotion detected (maps to GoEmotions "neutral")

    return None
