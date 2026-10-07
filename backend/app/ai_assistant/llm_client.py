"""Thin Anthropic client wrapper with safe offline fallback behavior."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("petro_dealer.ai")


class AnthropicClientError(RuntimeError):
    """Raised when the LLM client is unavailable or returns an API error."""


class LLMClient:
    """Minimal client wrapper around Anthropic's Messages API.

    The project is designed to work fully offline: if no API key is configured
    or the Anthropic SDK is unavailable, the caller should degrade to the rule-
    based fallback path instead of crashing.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
        self._client = None
        try:
            if self.api_key:
                import anthropic  # type: ignore

                self._client = anthropic.Anthropic(api_key=self.api_key)
        except Exception as exc:  # pragma: no cover - optional dependency path
            logger.warning("Anthropic SDK unavailable or misconfigured: %s", exc)
            self._client = None

    def is_available(self) -> bool:
        """Return True only when the SDK and credentials are present."""
        return bool(self._client and self.api_key)

    def generate(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generate a model response using Anthropic Messages API.

        Returns a dictionary shaped like:
        {
            "content": "final answer text",
            "tool_calls": [{"name":..., "arguments": {...}}],
        }
        """
        if not self.is_available():
            raise AnthropicClientError("Anthropic API not configured")

        try:
            tool_param = tools or None
            response = self._client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=messages,
                tools=tool_param,
            )
        except Exception as exc:  # pragma: no cover - network path
            logger.warning("Anthropic API call failed: %s", exc)
            raise AnthropicClientError(str(exc)) from exc

        content_blocks = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                content_blocks.append(getattr(block, "text", ""))

        tool_calls: List[Dict[str, Any]] = []
        for block in getattr(response, "content", []):
            if getattr(block, "type", None) == "tool_use":
                try:
                    arguments = dict(getattr(block, "input", {}) or {})
                except Exception:  # pragma: no cover - defensive
                    arguments = {}
                tool_calls.append({"name": getattr(block, "name", ""), "arguments": arguments})

        answer_text = "\n".join(content_blocks).strip()
        return {"content": answer_text, "tool_calls": tool_calls}
