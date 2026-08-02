"""
src/anxiosense_client.py

HTTP client for the AnxioSense evaluation API.

Calls POST /api/workflow/evaluate on the running AnxioSense server and returns
a structured result. Does NOT implement any LLM logic — that all lives inside
the AnxioSense server and Mastra workflow.

Usage
-----
    from src.anxiosense_client import call_anxiosense, AnxioSenseResult

    result = call_anxiosense(
        text="I've been really stressed about work lately.",
        model="groq/llama-3.3-70b-versatile",
        strategy="one-shot-cot",
        base_url="http://localhost:3001",
        timeout=60,
    )

    if result.error:
        print("Error:", result.error)
    else:
        print("referralLevel:", result.report_dict["report"]["referralLevel"])

AnxioSenseResult fields
-----------------------
    raw_response   dict | None   — full JSON response body from the server
    report_dict    dict | None   — same as raw_response when successful
    latency_ms     float         — wall-clock ms for the HTTP round-trip
    token_usage    dict          — {"prompt_tokens": int, "completion_tokens": int}
    error          str | None    — error message on failure, else None
    status         int           — HTTP status code (0 if connection failed)

Error cases handled
-------------------
    - HTTP errors (4xx, 5xx)
    - Connection refused / timeout
    - Non-JSON response body
    - Server returns JSON but lacks expected fields
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class AnxioSenseResult:
    raw_response: Optional[dict]        # Full JSON response body from server
    report_dict: Optional[dict]         # Alias for raw_response (same object)
    latency_ms: float                   # Wall-clock ms for the HTTP call
    token_usage: dict                   # {"input_tokens": int, "output_tokens": int}
    emotion_agent_raw: Optional[str] = None  # Raw JSON string from Emotion Agent (GoEmotions primary)
    error: Optional[str] = None         # Error message if the call failed
    status: int = 0                     # HTTP status code (0 = connection failed)

    @property
    def success(self) -> bool:
        return self.error is None and self.raw_response is not None

    def get_referral_level(self) -> Optional[str]:
        """Convenience: return the referralLevel field from the report."""
        if not self.report_dict:
            return None
        return self.report_dict.get("report", {}).get("referralLevel")

    def get_concern_pattern(self) -> Optional[str]:
        """Convenience: return the concernPattern field from the report."""
        if not self.report_dict:
            return None
        return self.report_dict.get("report", {}).get("concernPattern")

    def get_final_report(self) -> Optional[str]:
        """Convenience: return the finalReport markdown string."""
        if not self.report_dict:
            return None
        return self.report_dict.get("report", {}).get("finalReport")


# ---------------------------------------------------------------------------
# Client function
# ---------------------------------------------------------------------------

def call_anxiosense(
    text: str,
    model: str,
    strategy: str,
    base_url: str = "http://localhost:3001",
    timeout: int = 60,
) -> AnxioSenseResult:
    """
    POST text to the AnxioSense /api/workflow/evaluate endpoint.

    Parameters
    ----------
    text:
        The raw text to analyse (dataset example text).
    model:
        Model identifier string — recorded in server metadata, does NOT override
        the pipeline's actual model unless the server was started with GROQ_MODEL
        set to this value.
    strategy:
        Prompting strategy string — recorded in metadata only. The pipeline uses
        whatever strategy is compiled into the agent instructions.
    base_url:
        Base URL of the AnxioSense Express server (default: http://localhost:3001).
    timeout:
        Per-request timeout in seconds (default: 60).

    Returns
    -------
    AnxioSenseResult — always returns; error field is set on failure.
    """
    url = base_url.rstrip("/") + "/api/workflow/evaluate"

    payload = {
        "text":            text,
        "model":           model,
        "strategy":        strategy,
        "evaluation_mode": True,
    }

    body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.perf_counter()

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.status
            latency_ms = (time.perf_counter() - t0) * 1000.0
            raw_bytes = response.read()

    except urllib.error.HTTPError as exc:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        status = exc.code
        try:
            body_text = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body_text = "(unreadable response body)"
        return AnxioSenseResult(
            raw_response=None,
            report_dict=None,
            latency_ms=latency_ms,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0},
            error=f"HTTP {status}: {body_text[:300]}",
            status=status,
        )

    except urllib.error.URLError as exc:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        reason = str(exc.reason) if exc.reason else str(exc)
        return AnxioSenseResult(
            raw_response=None,
            report_dict=None,
            latency_ms=latency_ms,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0},
            error=f"Connection error: {reason}",
            status=0,
        )

    except TimeoutError:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return AnxioSenseResult(
            raw_response=None,
            report_dict=None,
            latency_ms=latency_ms,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0},
            error=f"Request timed out after {timeout}s",
            status=0,
        )

    # Parse JSON body
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return AnxioSenseResult(
            raw_response=None,
            report_dict=None,
            latency_ms=latency_ms,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0},
            error=f"JSON parse failure: {exc}. Raw (truncated): {raw_bytes[:200]!r}",
            status=status,
        )

    if not isinstance(data, dict):
        return AnxioSenseResult(
            raw_response=None,
            report_dict=None,
            latency_ms=latency_ms,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0},
            error=f"Unexpected response type: {type(data).__name__}. Expected dict.",
            status=status,
        )

    # Check for server-side error field
    if "error" in data:
        return AnxioSenseResult(
            raw_response=data,
            report_dict=None,
            latency_ms=latency_ms,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0},
            error=f"Server error: {data['error']}",
            status=status,
        )

    # Extract token usage from metadata if present
    metadata = data.get("metadata", {})
    token_usage = metadata.get("token_usage", {"input_tokens": 0, "output_tokens": 0})

    # Extract raw Emotion Agent JSON (added to /evaluate response for GoEmotions evaluation).
    # Shape: '{"emotions":[...],"emotional_intensity":"...","evidence_from_text":[...]}'
    # None when absent (safety-override path, or server not yet updated).
    emotion_agent_raw = data.get("emotion_agent_raw")  # str | None

    return AnxioSenseResult(
        raw_response=data,
        report_dict=data,
        latency_ms=latency_ms,
        token_usage=token_usage,
        emotion_agent_raw=emotion_agent_raw,
        error=None,
        status=status,
    )
