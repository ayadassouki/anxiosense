"""
tests/test_anxiosense_client.py

Offline unit tests for src/anxiosense_client.py.
All HTTP calls are mocked using unittest.mock — no network access required.
"""

from __future__ import annotations

import io
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "evaluation" / "llm-experiments"))

from src.anxiosense_client import call_anxiosense, AnxioSenseResult


# ---------------------------------------------------------------------------
# Helper: build a mock server response body
# ---------------------------------------------------------------------------

def _make_response_body(
    referral_level: str = "moderate",
    concern_pattern: str = "Elevated Concern Pattern",
    final_report: str = "# AnxioSense Report\n\n## Supporting Findings\n\nAnxiety indicators.",
    safety_override: bool = False,
    model_used: str = "groq/llama-3.3-70b-versatile",
    strategy_used: str = "one-shot-cot",
    latency_ms: int = 5000,
) -> bytes:
    """Build mock JSON response bytes from the /api/workflow/evaluate endpoint."""
    body = {
        "report": {
            "finalReport":    final_report,
            "concernPattern": concern_pattern,
            "referralLevel":  referral_level,
            "summary":        "Test summary.",
        },
        "metadata": {
            "model_used":      model_used,
            "strategy_used":   strategy_used,
            "latency_ms":      latency_ms,
            "token_usage":     {"prompt_tokens": 0, "completion_tokens": 0},
            "safety_override": safety_override,
        },
    }
    return json.dumps(body).encode("utf-8")


def _make_mock_http_response(body: bytes, status: int = 200):
    """Build a mock object that behaves like urllib's response context manager."""
    mock_response = MagicMock()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__  = MagicMock(return_value=False)
    mock_response.status    = status
    mock_response.read      = MagicMock(return_value=body)
    return mock_response


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------

class TestCallAnxioSenseSuccess:
    @patch("urllib.request.urlopen")
    def test_success_returns_report_dict(self, mock_urlopen):
        mock_urlopen.return_value = _make_mock_http_response(_make_response_body())
        result = call_anxiosense("I have been feeling anxious lately.", "model", "zero-shot")
        assert result.success
        assert result.error is None
        assert result.report_dict is not None

    @patch("urllib.request.urlopen")
    def test_success_status_is_200(self, mock_urlopen):
        mock_urlopen.return_value = _make_mock_http_response(_make_response_body(), status=200)
        result = call_anxiosense("Test text about stress.", "model", "zero-shot")
        assert result.status == 200

    @patch("urllib.request.urlopen")
    def test_referral_level_accessible(self, mock_urlopen):
        body = _make_response_body(referral_level="low")
        mock_urlopen.return_value = _make_mock_http_response(body)
        result = call_anxiosense("Feeling fine today.", "model", "zero-shot")
        assert result.get_referral_level() == "low"

    @patch("urllib.request.urlopen")
    def test_concern_pattern_accessible(self, mock_urlopen):
        body = _make_response_body(concern_pattern="High Concern Pattern")
        mock_urlopen.return_value = _make_mock_http_response(body)
        result = call_anxiosense("Severe anxiety symptoms.", "model", "zero-shot")
        assert result.get_concern_pattern() == "High Concern Pattern"

    @patch("urllib.request.urlopen")
    def test_final_report_accessible(self, mock_urlopen):
        body = _make_response_body(final_report="# Report\n\nContent here.")
        mock_urlopen.return_value = _make_mock_http_response(body)
        result = call_anxiosense("Some text.", "model", "zero-shot")
        assert "# Report" in (result.get_final_report() or "")

    @patch("urllib.request.urlopen")
    def test_token_usage_extracted_from_metadata(self, mock_urlopen):
        body = _make_response_body()
        mock_urlopen.return_value = _make_mock_http_response(body)
        result = call_anxiosense("Text.", "model", "zero-shot")
        assert isinstance(result.token_usage, dict)
        assert "prompt_tokens" in result.token_usage
        assert "completion_tokens" in result.token_usage

    @patch("urllib.request.urlopen")
    def test_latency_ms_is_positive(self, mock_urlopen):
        mock_urlopen.return_value = _make_mock_http_response(_make_response_body())
        result = call_anxiosense("Anxiety text.", "model", "zero-shot")
        assert result.latency_ms >= 0.0

    @patch("urllib.request.urlopen")
    def test_safety_override_response_parsed(self, mock_urlopen):
        body = _make_response_body(
            referral_level="urgent",
            concern_pattern="Urgent Safety Notice",
            safety_override=True,
        )
        mock_urlopen.return_value = _make_mock_http_response(body)
        result = call_anxiosense("Crisis text.", "model", "zero-shot")
        assert result.success
        assert result.get_referral_level() == "urgent"


# ---------------------------------------------------------------------------
# HTTP error path
# ---------------------------------------------------------------------------

class TestCallAnxioSenseHTTPErrors:
    @patch("urllib.request.urlopen")
    def test_http_500_returns_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://localhost:3001/api/workflow/evaluate",
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=io.BytesIO(b'{"error": "Mastra not running"}'),
        )
        result = call_anxiosense("Text.", "model", "zero-shot")
        assert not result.success
        assert result.error is not None
        assert "500" in result.error
        assert result.status == 500
        assert result.report_dict is None

    @patch("urllib.request.urlopen")
    def test_http_400_returns_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://localhost:3001/api/workflow/evaluate",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=io.BytesIO(b'{"error": "text too short"}'),
        )
        result = call_anxiosense("Hi.", "model", "zero-shot")
        assert not result.success
        assert result.status == 400

    @patch("urllib.request.urlopen")
    def test_http_429_returns_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://localhost:3001/api/workflow/evaluate",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=io.BytesIO(b'{"message": "Too many requests"}'),
        )
        result = call_anxiosense("Text.", "model", "zero-shot")
        assert not result.success
        assert result.status == 429


# ---------------------------------------------------------------------------
# Connection error path
# ---------------------------------------------------------------------------

class TestCallAnxioSenseConnectionErrors:
    @patch("urllib.request.urlopen")
    def test_connection_refused_returns_error(self, mock_urlopen):
        import socket
        mock_urlopen.side_effect = urllib.error.URLError(
            reason=ConnectionRefusedError(111, "Connection refused")
        )
        result = call_anxiosense("Text.", "model", "zero-shot")
        assert not result.success
        assert result.error is not None
        assert "connection" in result.error.lower() or "refused" in result.error.lower()
        assert result.status == 0

    @patch("urllib.request.urlopen")
    def test_timeout_returns_error(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("timed out")
        result = call_anxiosense("Text.", "model", "zero-shot", timeout=1)
        assert not result.success
        assert result.error is not None
        assert "timeout" in result.error.lower() or "timed out" in result.error.lower()
        assert result.status == 0


# ---------------------------------------------------------------------------
# JSON parse failure path
# ---------------------------------------------------------------------------

class TestCallAnxioSenseJSONParsure:
    @patch("urllib.request.urlopen")
    def test_non_json_response_returns_error(self, mock_urlopen):
        mock_urlopen.return_value = _make_mock_http_response(b"this is not json", status=200)
        result = call_anxiosense("Text.", "model", "zero-shot")
        assert not result.success
        assert result.error is not None
        assert "json" in result.error.lower() or "parse" in result.error.lower()

    @patch("urllib.request.urlopen")
    def test_html_error_page_returns_error(self, mock_urlopen):
        html = b"<html><body>502 Bad Gateway</body></html>"
        mock_urlopen.return_value = _make_mock_http_response(html, status=200)
        result = call_anxiosense("Text.", "model", "zero-shot")
        assert not result.success

    @patch("urllib.request.urlopen")
    def test_json_array_response_returns_error(self, mock_urlopen):
        # Server returns a JSON array instead of an object
        mock_urlopen.return_value = _make_mock_http_response(b"[1, 2, 3]", status=200)
        result = call_anxiosense("Text.", "model", "zero-shot")
        assert not result.success
        assert result.error is not None


# ---------------------------------------------------------------------------
# Server-side error field
# ---------------------------------------------------------------------------

class TestCallAnxioSenseServerError:
    @patch("urllib.request.urlopen")
    def test_server_error_field_sets_error(self, mock_urlopen):
        body = json.dumps({"error": "Mastra workflow timed out."}).encode()
        mock_urlopen.return_value = _make_mock_http_response(body, status=200)
        result = call_anxiosense("Text.", "model", "zero-shot")
        assert not result.success
        assert "Mastra workflow timed out" in (result.error or "")
        # report_dict is None on error; raw_response holds the error dict
        assert result.report_dict is None
        assert result.raw_response is not None
        assert result.raw_response.get("error") == "Mastra workflow timed out."


# ---------------------------------------------------------------------------
# AnxioSenseResult properties
# ---------------------------------------------------------------------------

class TestAnxioSenseResultProperties:
    @patch("urllib.request.urlopen")
    def test_success_property_true_on_success(self, mock_urlopen):
        mock_urlopen.return_value = _make_mock_http_response(_make_response_body())
        result = call_anxiosense("Feeling very anxious.", "model", "zero-shot")
        assert result.success is True

    @patch("urllib.request.urlopen")
    def test_success_property_false_on_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError(reason="refused")
        result = call_anxiosense("Text.", "model", "zero-shot")
        assert result.success is False

    @patch("urllib.request.urlopen")
    def test_get_referral_level_on_failure_returns_none(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError(reason="refused")
        result = call_anxiosense("Text.", "model", "zero-shot")
        assert result.get_referral_level() is None

    @patch("urllib.request.urlopen")
    def test_get_final_report_on_failure_returns_none(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError(reason="refused")
        result = call_anxiosense("Text.", "model", "zero-shot")
        assert result.get_final_report() is None
