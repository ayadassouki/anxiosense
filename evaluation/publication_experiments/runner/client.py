"""Transport only. This module never parses a prediction and never sees ground truth."""
from __future__ import annotations
import json, time, urllib.error, urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class TransportResult:
    http_status: int | None
    body: dict[str, Any] | None
    raw_body_text: str | None
    error_kind: str | None      # timeout | connection | http | decode | None
    error_detail: str | None
    latency_ms: float


class Transport(Protocol):
    def post_evaluate(self, *, text: str, model: str, strategy: str) -> TransportResult: ...


class HttpTransport:
    """POST to the AnxioSense Express /evaluate endpoint."""

    def __init__(self, base_url: str, endpoint: str, timeout_seconds: int):
        self.url = base_url.rstrip("/") + endpoint
        self.timeout = timeout_seconds

    def post_evaluate(self, *, text: str, model: str, strategy: str) -> TransportResult:
        payload = {"text": text, "model": model, "strategy": strategy, "evaluation_mode": True}
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.url, data=data,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body_text = resp.read().decode("utf-8", errors="replace")
                ms = (time.perf_counter() - t0) * 1000
                try:
                    body = json.loads(body_text)
                except json.JSONDecodeError as exc:
                    return TransportResult(resp.status, None, body_text, "decode", str(exc), ms)
                return TransportResult(resp.status, body, body_text, None, None, ms)
        except urllib.error.HTTPError as exc:
            ms = (time.perf_counter() - t0) * 1000
            try:
                body_text = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body_text = None
            body = None
            if body_text:
                try:
                    body = json.loads(body_text)
                except json.JSONDecodeError:
                    body = None
            return TransportResult(exc.code, body, body_text, None, f"HTTP {exc.code}", ms)
        except urllib.error.URLError as exc:
            ms = (time.perf_counter() - t0) * 1000
            reason = str(getattr(exc, "reason", exc))
            kind = "timeout" if "timed out" in reason.lower() else "connection"
            return TransportResult(None, None, None, kind, reason, ms)
        except TimeoutError as exc:
            ms = (time.perf_counter() - t0) * 1000
            return TransportResult(None, None, None, "timeout", str(exc), ms)
        except Exception as exc:  # noqa: BLE001 - transport must never raise into the loop
            ms = (time.perf_counter() - t0) * 1000
            return TransportResult(None, None, None, "connection", repr(exc), ms)


# ── Server runtime probe ─────────────────────────────────────────────────────

def probe_server_runtime(base_url: str, timeout_seconds: float = 10.0) -> dict:
    """Read the server's EFFECTIVE runtime settings from GET /api/health.

    Returns the parsed body. Raises on any transport or decode failure so the
    caller can abort rather than record an assumed value.
    """
    import json as _json
    import urllib.request

    url = base_url.rstrip("/") + "/api/health"
    with urllib.request.urlopen(url, timeout=timeout_seconds) as resp:
        if resp.status != 200:
            raise RuntimeError(f"GET {url} -> HTTP {resp.status}")
        return _json.loads(resp.read().decode("utf-8"))
