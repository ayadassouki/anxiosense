"""Deterministic, bounded retry. No jitter - two identical runs retry identically."""
from __future__ import annotations
from dataclasses import dataclass

from .failures import Transport, is_retryable


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3          # total attempts, not extra attempts
    backoff_base_ms: int = 2000
    backoff_factor: int = 2
    backoff_cap_ms: int = 30000

    def backoff_ms(self, attempt_number: int) -> int:
        """Delay AFTER attempt n fails. attempt_number is 1-based."""
        raw = self.backoff_base_ms * (self.backoff_factor ** (attempt_number - 1))
        return min(raw, self.backoff_cap_ms)


@dataclass(frozen=True)
class RetryDecision:
    retry: bool
    wait_ms: int
    reason: str


def next_action(policy: RetryPolicy, outcome: Transport, attempt_number: int) -> RetryDecision:
    """Given the transport outcome of attempt n, decide whether to attempt n+1.

    A completed model response is NEVER retried: Transport.OK and
    Transport.SAFETY_INTERCEPT are terminal regardless of what the model said,
    and the parser (which alone can call a response unusable) is not consulted.
    """
    if not is_retryable(outcome):
        return RetryDecision(False, 0, f"terminal:{outcome.value}")
    if attempt_number >= policy.max_attempts:
        return RetryDecision(False, 0, "retries_exhausted")
    return RetryDecision(True, policy.backoff_ms(attempt_number), "transient_retry")
