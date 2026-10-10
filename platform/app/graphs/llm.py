"""Synchronous LLM helper for graph nodes.

Wraps the Anthropic SDK for simple text completions (no tool use).
All failures converge to ``None`` so callers can fall back to
deterministic behaviour without propagating exceptions.

The sync/async boundary is handled by running ``asyncio.run`` in a
daemon thread with a deadline, following the same pattern as
:func:`app.plan_ai_adapter.build_anthropic_proposer`.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any


class GraphLLM:
    """Synchronous text-completion helper backed by the Anthropic SDK."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 256,
        timeout_s: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must be non-empty")
        self._api_key = api_key
        self._model = model
        self._max_tokens = min(max_tokens, 512)
        self._timeout_s = timeout_s
        self._client: Any = None

    def complete(self, prompt: str) -> str | None:
        """Send *prompt* and return the text response, or ``None`` on any failure."""
        if not prompt or not prompt.strip():
            return None

        result: list[str | None] = [None]

        def _run() -> None:
            try:
                result[0] = asyncio.run(self._async_complete(prompt))
            except Exception:
                result[0] = None

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=self._timeout_s + 5.0)
        return result[0]

    async def _async_complete(self, prompt: str) -> str | None:
        client = self._get_client()
        if client is None:
            return None
        try:
            message = await client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[{"role": "user", "content": prompt}],
                timeout=self._timeout_s,
            )
            text = _extract_text(message)
            if not text:
                return None
            return text.strip()
        except Exception:
            return None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import anthropic

            self._client = anthropic.AsyncAnthropic(
                api_key=self._api_key,
                max_retries=0,
                timeout=self._timeout_s,
            )
            return self._client
        except Exception:
            return None


def _extract_text(message: Any) -> str:
    content = getattr(message, "content", None)
    if content is None:
        return ""
    parts: list[str] = []
    for block in content:
        if getattr(block, "type", None) == "text":
            text = getattr(block, "text", None)
            if isinstance(text, str):
                parts.append(text)
    return "".join(parts)
