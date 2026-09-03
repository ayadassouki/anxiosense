"""Failure taxonomy.

Two independent axes, deliberately kept apart:

  TRANSPORT outcome  - decided at dispatch time from HTTP/network signals ONLY.
                       This is the ONLY input to the retry decision, so retry can
                       never depend on what the model said.

  PARSE outcome      - decided later, offline, from the stored raw response.
                       A parse failure is MODEL BEHAVIOUR and is never retried.
"""
from __future__ import annotations
from enum import Enum


class Transport(str, Enum):
    OK = "OK"                              # response received and well-formed HTTP
    SAFETY_INTERCEPT = "SAFETY_INTERCEPT"   # deterministic crisis path, no model call
    INFRA_TRANSIENT = "INFRA_TRANSIENT"     # retryable
    INFRA_TERMINAL = "INFRA_TERMINAL"       # not retryable, not the model's fault
    PRECONDITION = "PRECONDITION"           # abort the experiment


class ParseOutcome(str, Enum):
    VALID = "VALID"
    MODEL_BEHAVIOUR = "MODEL_BEHAVIOUR"     # complete response, unusable answer
    NOT_APPLICABLE = "NOT_APPLICABLE"       # transport never produced a response


RETRYABLE = frozenset({Transport.INFRA_TRANSIENT})

_TRANSIENT_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504, 522, 524})
_TRANSIENT_ERROR_KINDS = frozenset({"timeout", "connection", "network", "dns", "reset"})


def classify_transport(*, error_kind: str | None, http_status: int | None,
                       body: dict | None) -> tuple[Transport, str | None]:
    """Classify one dispatch attempt. Sees transport signals only - never a prediction."""
    if error_kind:
        if error_kind in _TRANSIENT_ERROR_KINDS:
            return Transport.INFRA_TRANSIENT, error_kind
        return Transport.INFRA_TERMINAL, error_kind

    if http_status is None:
        return Transport.INFRA_TERMINAL, "no_http_status"

    if http_status in _TRANSIENT_STATUS:
        return Transport.INFRA_TRANSIENT, f"HTTP {http_status}"
    if http_status >= 500:
        return Transport.INFRA_TRANSIENT, f"HTTP {http_status}"
    if http_status != 200:
        # 400 (input rejected by the server gate), 401/403 (auth), 404, 422 ...
        return Transport.INFRA_TERMINAL, f"HTTP {http_status}"

    meta = (body or {}).get("metadata") or {}
    if meta.get("safety_override"):
        return Transport.SAFETY_INTERCEPT, "deterministic_crisis_path"
    return Transport.OK, None


def is_retryable(outcome: Transport) -> bool:
    return outcome in RETRYABLE
