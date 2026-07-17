"""Detect cross-LLM call-telemetry episodes.

The bridge auto-saves every ask_agy / ask_gemini / ask_claude / … as an episode
whose ``task_text`` opens with ``[<llm>-call …]``. These are machine telemetry,
not user tasks: 2026-06-13 they were 123/554 (22%) of the live episode store,
polluting recall and diluting the emerging/correction/risk quartet.

Shared single source of truth for the WRITE-time episode gate (verimem.memory
routes them to a separate ``episode_telemetry`` table) and the READ-time briefing
filter. Leaf module: imports nothing from ``engram`` → no import cycle.
"""
from __future__ import annotations

import re

_CALL_TELEMETRY_RE = re.compile(
    r"^\s*\[(?:agy|gemini|claude|kimi|deepseek|grok|gpt|qwen|llama|mistral)-call\b",
    re.IGNORECASE,
)


def is_call_telemetry(task_text: str | None) -> bool:
    """True when the episode's ``task_text`` is a cross-LLM call record, not a task."""
    return bool(_CALL_TELEMETRY_RE.match(task_text or ""))


__all__ = ["is_call_telemetry"]
