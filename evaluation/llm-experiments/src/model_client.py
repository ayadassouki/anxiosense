"""
src/model_client.py

Unified LLM client for AnxioSense evaluation experiments.

Supports:
    OpenRouter (OpenAI-compatible endpoint):
        - meta-llama/llama-4-scout:free
        - google/gemma-3-27b-it:free
        - deepseek/deepseek-v4-flash
        - microsoft/phi-4:free

    Mistral La Plateforme (mistralai SDK):
        - mistral-small-2603

Each call returns a ModelResponse dataclass with:
    raw_response    str | None  — the full text returned by the model
    parsed_text     str | None  — same as raw_response (parsing is downstream)
    latency_ms      float       — wall-clock time for the API round-trip
    token_usage     dict        — {"prompt": int, "completion": int, "total": int}
    error           str | None  — error message if the call failed, else None

Retry policy:
    max 3 attempts, exponential backoff (base 2), 30s timeout per request.
    HTTP 429 → wait backoff seconds and retry.
    Other HTTP errors → retry up to max_attempts, then fail.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

@dataclass
class ModelResponse:
    raw_response: Optional[str]
    parsed_text: Optional[str]
    latency_ms: float
    token_usage: dict
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and self.raw_response is not None


# ---------------------------------------------------------------------------
# Model client
# ---------------------------------------------------------------------------

class ModelClient:
    """
    Unified client for all 5 evaluation models.

    Parameters
    ----------
    model_id:
        The model identifier string from experiment_config.yaml.
    provider:
        "openrouter" or "mistral".
    api_key:
        API key for the provider.
    max_tokens:
        Maximum tokens to request from the model.
    temperature:
        Sampling temperature. None = provider default.
    seed:
        Sampling seed. None = no seed.
    max_attempts:
        Maximum number of retry attempts.
    backoff_base:
        Exponential backoff base (seconds).
    timeout:
        Per-request timeout in seconds.
    """

    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        model_id: str,
        provider: str,
        api_key: str,
        max_tokens: int = 16384,
        temperature: Optional[float] = None,
        seed: Optional[int] = None,
        max_attempts: int = 3,
        backoff_base: int = 2,
        timeout: int = 30,
    ) -> None:
        self.model_id = model_id
        self.provider = provider
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.seed = seed
        self.max_attempts = max_attempts
        self.backoff_base = backoff_base
        self.timeout = timeout

        self._client = self._build_client()

    def _build_client(self):
        if self.provider == "openrouter":
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise ImportError(
                    "openai package is required for OpenRouter. "
                    "Install with: pip install openai"
                ) from exc
            return OpenAI(
                api_key=self.api_key,
                base_url=self.OPENROUTER_BASE_URL,
                timeout=self.timeout,
            )

        if self.provider == "mistral":
            try:
                from mistralai import Mistral
            except ImportError as exc:
                raise ImportError(
                    "mistralai package is required for Mistral. "
                    "Install with: pip install mistralai"
                ) from exc
            return Mistral(
                api_key=self.api_key,
            )

        raise ValueError(
            f"Unknown provider: {self.provider!r}. Expected 'openrouter' or 'mistral'."
        )

    def call(
        self,
        system_prompt: str,
        user_message: str,
    ) -> ModelResponse:
        """
        Call the model with retry / backoff.

        Parameters
        ----------
        system_prompt: system turn content
        user_message: user turn content (the raw dataset text)

        Returns
        -------
        ModelResponse — always returns; error field is set on failure.
        """
        last_error: Optional[str] = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                return self._call_once(system_prompt, user_message)
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                wait = self.backoff_base ** attempt

                # Check for rate-limit indicator in exception message
                exc_str = str(exc).lower()
                if "429" in exc_str or "rate limit" in exc_str or "too many requests" in exc_str:
                    logger.warning(
                        "Rate limit hit (attempt %d/%d). Waiting %ds.",
                        attempt, self.max_attempts, wait,
                    )
                else:
                    logger.warning(
                        "API call failed (attempt %d/%d): %s. Retrying in %ds.",
                        attempt, self.max_attempts, last_error, wait,
                    )

                if attempt < self.max_attempts:
                    time.sleep(wait)

        return ModelResponse(
            raw_response=None,
            parsed_text=None,
            latency_ms=0.0,
            token_usage={"prompt": 0, "completion": 0, "total": 0},
            error=f"All {self.max_attempts} attempts failed. Last error: {last_error}",
        )

    def _call_once(self, system_prompt: str, user_message: str) -> ModelResponse:
        """Single API call — raises on error."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ]

        # Build keyword arguments (omit None values)
        kwargs: dict = {"messages": messages, "model": self.model_id}
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        if self.seed is not None:
            kwargs["seed"] = self.seed

        t0 = time.perf_counter()

        if self.provider == "openrouter":
            response = self._client.chat.completions.create(**kwargs)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            raw = response.choices[0].message.content
            usage = response.usage
            token_usage = {
                "prompt":     usage.prompt_tokens     if usage else 0,
                "completion": usage.completion_tokens if usage else 0,
                "total":      usage.total_tokens      if usage else 0,
            }

        elif self.provider == "mistral":
            response = self._client.chat.complete(**kwargs)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            raw = response.choices[0].message.content
            usage = response.usage
            token_usage = {
                "prompt":     usage.prompt_tokens     if usage else 0,
                "completion": usage.completion_tokens if usage else 0,
                "total":      usage.total_tokens      if usage else 0,
            }

        else:
            raise ValueError(f"Unknown provider: {self.provider!r}")

        return ModelResponse(
            raw_response=raw,
            parsed_text=raw,
            latency_ms=latency_ms,
            token_usage=token_usage,
            error=None,
        )
