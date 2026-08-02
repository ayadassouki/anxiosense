"""
src/emotion_payload.py

Robust, tri-state extraction of the Emotion Agent's structured payload from the
`emotion_agent_raw` string returned by /api/workflow/evaluate.

WHY THIS MODULE EXISTS
──────────────────────
The original implementation (report_parser.extract_emotion_label_from_agent_json)
called json.loads() directly on the raw string and returned Optional[str]. That
design had two defects that together invalidated the Stage C GoEmotions results:

  DEFECT 1 — Conflated "valid empty prediction" with "parse failure".
      Returning None meant BOTH:
        (a) the model correctly emitted {"emotions": []} on a non-distress text
            → a VALID prediction that maps to the "non_distress" eval class, and
        (b) the payload could not be parsed at all
            → a genuine failure that must be excluded from precision/recall.
      The caller (run_experiments.extract_predicted_label) treated every None as
      a failure, so correct non_distress predictions were discarded. Because 71%
      of the GoEmotions test sample is non_distress, this silently destroyed the
      majority of the evaluable data.

  DEFECT 2 — Zero tolerance for the model's actual output format.
      json.loads() fails on:
        - markdown code fences  ```json { ... } ```
        - chain-of-thought prose followed by the JSON object
        - a JSON object embedded anywhere in a longer response
      Two of the three prompting strategies under test are explicitly
      chain-of-thought, so prose-then-JSON is the EXPECTED behaviour, not an
      anomaly. Treating it as a parse failure measures the parser, not the model.

This module fixes both: it returns an explicit status alongside the payload, and
it applies a documented ladder of increasingly permissive extraction strategies.

DESIGN PRINCIPLE — recover, never invent
────────────────────────────────────────
Every strategy below extracts text that is *literally present* in the stored
payload. Nothing is inferred from context, ground truth, or the surrounding
report. When the "emotions" array cannot be read verbatim, the record is
reported as a failure rather than guessed. This is deliberate: an evaluation
harness that guesses on behalf of the model does not measure the model.

STATUS VALUES
─────────────
Success (payload readable):
    ok_json         strict json.loads() succeeded on the raw string
    ok_fence        succeeded after stripping markdown code fences
    ok_embedded     a balanced {...} object was located inside surrounding prose
    ok_repaired     a known transport corruption (dropped leading '{"') was undone
    ok_array_only   only the "emotions": [...] array survived (payload truncated
                    after it); the array itself was complete and parsed verbatim

Failure (payload NOT readable — exclude from precision/recall):
    fail_absent       emotion_agent_raw was None or empty
    fail_truncated    payload hit the storage cap and the array was cut mid-write
    fail_unparseable  present but no verbatim "emotions" array could be read
"""

from __future__ import annotations

import json
import logging
import re
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Storage cap historically applied by run_experiments.py when persisting
# emotion_agent_raw. Payloads at exactly this length are almost certainly
# truncated rather than genuinely short, which lets us report a precise cause.
LEGACY_STORAGE_CAP = 600

OK_STATUSES = frozenset(
    {"ok_json", "ok_fence", "ok_embedded", "ok_repaired", "ok_array_only"}
)

_FENCE_OPEN = re.compile(r"^```(?:json)?\s*", re.IGNORECASE)
_FENCE_CLOSE = re.compile(r"\s*```$")

# Matches a COMPLETE "emotions": [ ... ] array. The closing bracket is required,
# so a payload truncated mid-array will not match and is correctly reported as
# a failure instead of being silently read as empty.
_EMOTIONS_ARRAY = re.compile(r'"emotions"\s*:\s*\[([^\]]*)\]', re.DOTALL)

# Corruption signature observed in Stage C: a short contiguous run of characters
# is dropped from the response, most often the leading '{"' of the object.
_LOOKS_DECAPITATED = re.compile(r'^\s*"?emotions"\s*:')


def _strip_fences(text: str) -> str:
    """Remove a leading ```/```json fence and a trailing ``` fence."""
    out = _FENCE_OPEN.sub("", text.strip())
    return _FENCE_CLOSE.sub("", out).strip()


def _first_balanced_object(text: str) -> Optional[str]:
    """
    Return the first brace-balanced {...} substring, or None.

    Brace counting is string-aware: braces inside JSON string literals and
    escaped characters do not affect depth. A naive greedy regex would break on
    payloads whose evidence quotes contain braces.
    """
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False

    for i in range(start, len(text)):
        ch = text[i]
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _emotions_from_obj(obj: object) -> Optional[List]:
    """Return the 'emotions' list from a parsed object, or None if absent/wrong type."""
    if not isinstance(obj, dict):
        return None
    emotions = obj.get("emotions")
    return emotions if isinstance(emotions, list) else None


def extract_emotion_payload(
    emotion_agent_raw: Optional[str],
) -> Tuple[str, Optional[List]]:
    """
    Extract the Emotion Agent's "emotions" list from a raw payload string.

    Returns
    -------
    (status, emotions)
        status   : one of the STATUS VALUES documented in the module docstring.
        emotions : the list when status is in OK_STATUSES (possibly empty, which
                   is a VALID prediction meaning "no emotion detected"), else None.

    An empty list and a failure are distinct outcomes and callers MUST treat
    them differently:
        ("ok_*", [])   → valid prediction → maps to the "non_distress" class
        ("fail_*", None) → no usable prediction → exclude from precision/recall
    """
    if emotion_agent_raw is None or not isinstance(emotion_agent_raw, str):
        return "fail_absent", None

    raw = emotion_agent_raw.strip()
    if not raw or raw in ("null", "{}"):
        return "fail_absent", None

    # 1. Strict parse — the happy path.
    try:
        emotions = _emotions_from_obj(json.loads(raw))
        if emotions is not None:
            return "ok_json", emotions
    except json.JSONDecodeError:
        pass

    # 2. Markdown code fences.
    unfenced = _strip_fences(raw)
    if unfenced != raw:
        try:
            emotions = _emotions_from_obj(json.loads(unfenced))
            if emotions is not None:
                return "ok_fence", emotions
        except json.JSONDecodeError:
            pass

    # 3. JSON object embedded in chain-of-thought prose. Expected for the two
    #    CoT strategies, which narrate their reasoning before emitting JSON.
    for candidate in (raw, unfenced):
        obj_text = _first_balanced_object(candidate)
        if obj_text:
            try:
                emotions = _emotions_from_obj(json.loads(obj_text))
                if emotions is not None:
                    return "ok_embedded", emotions
            except json.JSONDecodeError:
                pass

    # 4. Repair the observed transport corruption: a dropped leading '{"'.
    #    Only attempted when the payload begins exactly at the "emotions" key,
    #    so we are restoring a known-missing delimiter, not inventing content.
    if _LOOKS_DECAPITATED.match(raw):
        body = raw.lstrip()
        repaired = ("{" + body) if body.startswith('"') else ('{"' + body)
        obj_text = _first_balanced_object(repaired) or repaired
        try:
            emotions = _emotions_from_obj(json.loads(obj_text))
            if emotions is not None:
                return "ok_repaired", emotions
        except json.JSONDecodeError:
            pass

    # 5. Array-only salvage. The regex requires a closing ']', so this fires only
    #    when the complete array survived and the payload was cut after it.
    match = _EMOTIONS_ARRAY.search(raw)
    if match:
        inner = match.group(1).strip()
        if not inner:
            return "ok_array_only", []
        try:
            parsed = json.loads("[" + inner + "]")
            if isinstance(parsed, list):
                return "ok_array_only", parsed
        except json.JSONDecodeError:
            pass

    # Nothing readable. Distinguish storage truncation from a malformed response
    # so the two causes can be reported and remediated separately.
    if len(emotion_agent_raw) >= LEGACY_STORAGE_CAP:
        return "fail_truncated", None

    logger.debug("Unparseable emotion payload: %.160r", raw)
    return "fail_unparseable", None


def primary_emotion(emotions: Optional[List]) -> Optional[str]:
    """
    Return the first emotion as a lowercased string, or None for an empty list.

    None here means "the model detected no emotion" — a valid prediction that the
    caller maps to "non_distress". It does NOT mean a parse failure; the status
    returned by extract_emotion_payload() is the only source of truth for that.
    """
    if not emotions:
        return None
    first = emotions[0]
    if not isinstance(first, str):
        return None
    return first.lower().strip() or None
