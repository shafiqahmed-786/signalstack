"""
app/clients/anthropic_client.py

Thin, opinionated wrapper around the official Anthropic SDK.

Responsibilities:
  - Retry with exponential backoff on RateLimitError and APIStatusError 529
  - Per-call timeout enforcement
  - Input + output token counting and logging
  - Structured log emission for every API call (started, completed, failed)
  - Model pinning via config (single place to change model version)
  - Never raises Anthropic SDK exceptions directly — converts to typed errors

This client is the ONLY place in the codebase that imports anthropic.
All orchestration code (Planner, Synthesizer) calls this client.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

import anthropic
import structlog
from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncAnthropic,
    RateLimitError,
)

from app.config import get_settings

log = structlog.get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

# The model used for ALL LLM calls in this project.
# Planner and Synthesizer both use this. Override per-call if needed.
DEFAULT_MODEL = "claude-sonnet-4-20250514"

# Retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY_S = 1.0
MAX_RETRY_DELAY_S = 30.0
RETRY_MULTIPLIER = 2.0

# Status codes that warrant a retry
RETRYABLE_STATUS_CODES = {429, 529}


# ── Result types ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LLMResponse:
    """Typed result from a successful LLM call."""

    text: str                   # Concatenated text from all content blocks
    input_tokens: int
    output_tokens: int
    model: str
    stop_reason: str            # "end_turn" | "max_tokens" | "stop_sequence"
    duration_ms: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class LLMError(Exception):
    """
    Raised when the LLM call fails after all retries.

    Wraps the underlying Anthropic error for context without leaking
    SDK internals to the orchestration layer.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LLMTimeoutError(LLMError):
    """Raised when the LLM call exceeds the configured timeout."""

    pass


class LLMRateLimitError(LLMError):
    """Raised when rate limit is hit and retries are exhausted."""

    pass


# ── Client ────────────────────────────────────────────────────────────────────


class AnthropicClient:
    """
    Async wrapper around the Anthropic SDK.

    Usage:
        client = AnthropicClient()
        response = await client.complete(
            system="You are a financial analyst.",
            user_message="Analyse NVIDIA's revenue trends.",
            max_tokens=1000,
            temperature=0.0,
            timeout_s=30.0,
            call_name="synthesizer",
        )
        print(response.text)

    The call_name parameter is purely for logging context — it appears
    in every log entry so you can distinguish planner calls from synthesizer calls.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncAnthropic(
            api_key=settings.clerk_secret_key,  # placeholder — see _get_api_key()
            timeout=60.0,                        # SDK-level timeout (overridden per call)
            max_retries=0,                       # We handle retries ourselves for observability
        )
        # Re-initialise with the correct API key
        self._client = AsyncAnthropic(
            api_key=self._get_api_key(),
            timeout=60.0,
            max_retries=0,
        )
        log.info("anthropic_client.initialised", model=DEFAULT_MODEL)

    @staticmethod
    def _get_api_key() -> str:
        import os

        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Add it to your .env file."
            )
        return key

    async def complete(
        self,
        system: str,
        user_message: str,
        max_tokens: int,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.0,
        timeout_s: float = 60.0,
        call_name: str = "llm_call",
    ) -> LLMResponse:
        """
        Send a single-turn message and return the LLMResponse.

        Parameters
        ----------
        system       : System prompt string
        user_message : User turn content
        max_tokens   : Maximum output tokens (hard cap)
        model        : Claude model identifier
        temperature  : 0.0 for deterministic synthesis, 0.1–0.3 for planner
        timeout_s    : Per-call timeout in seconds (enforced by asyncio.wait_for)
        call_name    : Label for log events ("planner" | "synthesizer" | ...)

        Raises
        ------
        LLMTimeoutError     : Call exceeded timeout_s after MAX_RETRIES
        LLMRateLimitError   : Rate limited after MAX_RETRIES
        LLMError            : Any other non-retryable failure
        """
        attempt = 0
        last_error: Exception | None = None

        while attempt < MAX_RETRIES:
            attempt += 1
            call_id = f"{call_name}.attempt_{attempt}"
            start = time.monotonic()

            log.info(
                "llm.call.started",
                call_name=call_name,
                attempt=attempt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout_s=timeout_s,
            )

            try:
                message = await asyncio.wait_for(
                    self._client.messages.create(
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        system=system,
                        messages=[{"role": "user", "content": user_message}],
                    ),
                    timeout=timeout_s,
                )

                # Extract text from content blocks
                text_parts = [
                    block.text
                    for block in message.content
                    if hasattr(block, "text")
                ]
                full_text = "\n".join(text_parts)

                duration_ms = int((time.monotonic() - start) * 1000)

                response = LLMResponse(
                    text=full_text,
                    input_tokens=message.usage.input_tokens,
                    output_tokens=message.usage.output_tokens,
                    model=message.model,
                    stop_reason=message.stop_reason or "end_turn",
                    duration_ms=duration_ms,
                )

                log.info(
                    "llm.call.completed",
                    call_name=call_name,
                    attempt=attempt,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    total_tokens=response.total_tokens,
                    stop_reason=response.stop_reason,
                    duration_ms=duration_ms,
                )

                if response.stop_reason == "max_tokens":
                    log.warning(
                        "llm.max_tokens_reached",
                        call_name=call_name,
                        max_tokens=max_tokens,
                        output_tokens=response.output_tokens,
                    )

                return response

            except asyncio.TimeoutError:
                duration_ms = int((time.monotonic() - start) * 1000)
                log.warning(
                    "llm.call.timeout",
                    call_name=call_name,
                    attempt=attempt,
                    timeout_s=timeout_s,
                    duration_ms=duration_ms,
                )
                last_error = asyncio.TimeoutError(
                    f"LLM call '{call_name}' timed out after {timeout_s}s"
                )
                # Timeouts: retry with backoff
                await self._backoff(attempt)
                continue

            except RateLimitError as exc:
                duration_ms = int((time.monotonic() - start) * 1000)
                log.warning(
                    "llm.call.rate_limited",
                    call_name=call_name,
                    attempt=attempt,
                    status_code=exc.status_code,
                    duration_ms=duration_ms,
                )
                last_error = exc
                await self._backoff(attempt, multiplier=3.0)  # Longer backoff for rate limits
                continue

            except APIStatusError as exc:
                duration_ms = int((time.monotonic() - start) * 1000)
                log.warning(
                    "llm.call.api_error",
                    call_name=call_name,
                    attempt=attempt,
                    status_code=exc.status_code,
                    message=str(exc),
                    duration_ms=duration_ms,
                )
                last_error = exc
                if exc.status_code in RETRYABLE_STATUS_CODES:
                    await self._backoff(attempt)
                    continue
                # Non-retryable API error
                raise LLMError(
                    f"Anthropic API error {exc.status_code}: {exc.message}",
                    status_code=exc.status_code,
                ) from exc

            except APIConnectionError as exc:
                duration_ms = int((time.monotonic() - start) * 1000)
                log.warning(
                    "llm.call.connection_error",
                    call_name=call_name,
                    attempt=attempt,
                    error=str(exc),
                    duration_ms=duration_ms,
                )
                last_error = exc
                await self._backoff(attempt)
                continue

            except APITimeoutError as exc:
                duration_ms = int((time.monotonic() - start) * 1000)
                log.warning(
                    "llm.call.sdk_timeout",
                    call_name=call_name,
                    attempt=attempt,
                    duration_ms=duration_ms,
                )
                last_error = exc
                await self._backoff(attempt)
                continue

        # All retries exhausted
        log.error(
            "llm.call.all_retries_exhausted",
            call_name=call_name,
            max_retries=MAX_RETRIES,
            last_error=str(last_error),
        )

        if isinstance(last_error, asyncio.TimeoutError):
            raise LLMTimeoutError(
                f"LLM call '{call_name}' timed out after {MAX_RETRIES} attempts ({timeout_s}s each)"
            )
        if isinstance(last_error, RateLimitError):
            raise LLMRateLimitError(
                f"Rate limited on '{call_name}' after {MAX_RETRIES} attempts"
            )

        raise LLMError(
            f"LLM call '{call_name}' failed after {MAX_RETRIES} attempts: {last_error}"
        )

    @staticmethod
    async def _backoff(attempt: int, multiplier: float = RETRY_MULTIPLIER) -> None:
        """Exponential backoff with jitter."""
        import random

        delay = min(
            INITIAL_RETRY_DELAY_S * (multiplier ** (attempt - 1)),
            MAX_RETRY_DELAY_S,
        )
        jitter = random.uniform(0, delay * 0.1)
        await asyncio.sleep(delay + jitter)


# ── Module-level singleton ────────────────────────────────────────────────────

_client_instance: AnthropicClient | None = None


def get_anthropic_client() -> AnthropicClient:
    """
    Returns the module-level AnthropicClient singleton.
    Initialised lazily on first call.
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = AnthropicClient()
    return _client_instance