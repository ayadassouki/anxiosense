"""
src/response_parser.py

Parse LLM responses from the AnxioSense emotion agent prompt into
structured labels for metric computation.

The emotion agent always returns JSON in this shape:
    {
        "emotions": ["stress", "anxiety", ...],
        "emotional_intensity": "low | moderate | high",
        "evidence_from_text": ["...", ...]
    }

Two task types are supported:

    binary (Dreaddit stress detection)
    -----------------------------------
    Returns 1 if "stress" appears in emotions[], else 0.
    Also accepts literal "1"/"stressed" / "0"/"not stressed" if the model
    deviates from the schema.

    multiclass (GoEmotions emotion classification)
    -----------------------------------------------
    Returns the primary emotion string from emotions[] (first element),
    or None if the list is empty.

Parse failures:
    - label is set to None
    - failure_reason is a non-empty string describing what went wrong
    - Failures are NEVER silently converted to 0 or any default label
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class ParseResult:
    label: Optional[object]      # int (binary) | str (multiclass) | None (failure)
    raw_emotions: Optional[list] # the "emotions" list if parsing succeeded
    failure_reason: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.label is not None and self.failure_reason is None


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_INLINE_JSON_RE = re.compile(r"\{[^{}]*\"emotions\"[^{}]*\}", re.DOTALL)


def _extract_json(text: str) -> Optional[dict]:
    """
    Try to extract and parse a JSON object from text.
    Tries: fenced code block → bare inline JSON → full text.
    Returns the parsed dict or None on failure.
    """
    candidates = []

    # 1. Fenced block
    m = _JSON_BLOCK_RE.search(text)
    if m:
        candidates.append(m.group(1))

    # 2. Inline JSON containing "emotions"
    m2 = _INLINE_JSON_RE.search(text)
    if m2:
        candidates.append(m2.group(0))

    # 3. Full text (model may return bare JSON)
    candidates.append(text.strip())

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    return None


# ---------------------------------------------------------------------------
# Binary parser (Dreaddit)
# ---------------------------------------------------------------------------

_STRESSED_WORDS = {"stress", "stressed", "overwhelmed"}
_NOT_STRESSED_WORDS = {"not stressed", "not_stressed", "no stress"}


def parse_binary(raw_response: Optional[str]) -> ParseResult:
    """
    Parse the model response for binary Dreaddit stress detection.

    Decision logic:
        1. Try to parse JSON and check if "stress" is in emotions[].
        2. Fall back to keyword matching on the raw text.
        3. If neither works, return failure.

    Returns
    -------
    ParseResult with label=1 (stressed) or label=0 (not stressed) or label=None.
    """
    if raw_response is None:
        return ParseResult(
            label=None,
            raw_emotions=None,
            failure_reason="No response from model (API error or timeout)",
        )

    # --- Try JSON parsing first ---
    parsed = _extract_json(raw_response)
    if parsed is not None:
        emotions = parsed.get("emotions")
        if isinstance(emotions, list):
            # Normalize all emotion strings to lowercase
            lower_emotions = [str(e).lower() for e in emotions]
            has_stress = "stress" in lower_emotions
            return ParseResult(
                label=int(has_stress),
                raw_emotions=lower_emotions,
                failure_reason=None,
            )
        else:
            return ParseResult(
                label=None,
                raw_emotions=None,
                failure_reason=(
                    f"JSON parsed but 'emotions' key is missing or not a list. "
                    f"Got: {parsed}"
                ),
            )

    # --- Fallback: direct binary keywords ---
    normalized = raw_response.strip().lower()

    if normalized in ("1", "stressed"):
        return ParseResult(label=1, raw_emotions=None)
    if normalized in ("0", "not stressed", "not_stressed"):
        return ParseResult(label=0, raw_emotions=None)

    # Keyword scan
    for kw in _STRESSED_WORDS:
        if kw in normalized:
            return ParseResult(
                label=1,
                raw_emotions=None,
                failure_reason=f"JSON parse failed; fell back to keyword '{kw}' in raw text",
            )
    for kw in _NOT_STRESSED_WORDS:
        if kw in normalized:
            return ParseResult(
                label=0,
                raw_emotions=None,
                failure_reason=f"JSON parse failed; fell back to keyword '{kw}' in raw text",
            )

    return ParseResult(
        label=None,
        raw_emotions=None,
        failure_reason=(
            f"Could not extract binary label from response. "
            f"JSON parse failed and no fallback keyword matched. "
            f"Raw (truncated): {raw_response[:200]!r}"
        ),
    )


# ---------------------------------------------------------------------------
# Multiclass parser (GoEmotions)
# ---------------------------------------------------------------------------

def parse_multiclass(raw_response: Optional[str]) -> ParseResult:
    """
    Parse the model response for GoEmotions multiclass emotion classification.

    Returns the first element of the emotions[] list (the primary emotion),
    normalized to lowercase.

    Returns ParseResult with label=str (emotion name) or label=None on failure.
    """
    if raw_response is None:
        return ParseResult(
            label=None,
            raw_emotions=None,
            failure_reason="No response from model (API error or timeout)",
        )

    parsed = _extract_json(raw_response)
    if parsed is not None:
        emotions = parsed.get("emotions")
        if isinstance(emotions, list):
            if len(emotions) == 0:
                # Model detected no emotions — valid result, not a failure
                return ParseResult(
                    label=None,
                    raw_emotions=[],
                    failure_reason="Model returned empty emotions list (no emotion detected)",
                )
            primary = str(emotions[0]).lower()
            return ParseResult(
                label=primary,
                raw_emotions=[str(e).lower() for e in emotions],
                failure_reason=None,
            )
        else:
            return ParseResult(
                label=None,
                raw_emotions=None,
                failure_reason=(
                    f"JSON parsed but 'emotions' key is missing or not a list. "
                    f"Got: {parsed}"
                ),
            )

    return ParseResult(
        label=None,
        raw_emotions=None,
        failure_reason=(
            f"Could not parse JSON from response. "
            f"Raw (truncated): {raw_response[:200]!r}"
        ),
    )


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def parse_response(raw_response: Optional[str], task_type: str) -> ParseResult:
    """
    Parse a model response for the given task type.

    Parameters
    ----------
    raw_response: the raw string returned by the model.
    task_type: "binary" | "multiclass" | "multilabel"

    Returns ParseResult.
    """
    if task_type == "binary":
        return parse_binary(raw_response)
    if task_type in ("multiclass", "multilabel"):
        return parse_multiclass(raw_response)
    raise ValueError(
        f"Unknown task_type: {task_type!r}. Expected 'binary', 'multiclass', or 'multilabel'."
    )
