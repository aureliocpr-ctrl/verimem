"""Cycle 169 (2026-05-20) — PreToolUse hook that consumes StepInjector.

Closes the cycle-168 critic finding from PR #108 ("StepInjector dead
code = no MCP wrapper / no consumer"). The hook reads the Claude Code
PreToolUse JSON payload on stdin, extracts a sub-goal "step text"
from the tool call, runs
:meth:`verimem.proactive_step_injector.StepInjector.inject` against the
local HippoAgent semantic store, and writes a short
``<engram-step-recall>…</engram-step-recall>`` banner to stdout so the
host LLM sees the relevant facts BEFORE the tool fires.

Design notes
------------
* **Fail-soft everywhere**: missing data dir, factory raising, embedding
  daemon offline, malformed stdin — every error path returns the empty
  banner / exit code 0. A broken hook must NEVER block a tool call.
* **Anti-loop**: any tool whose name starts with ``mcp__hippoagent__``
  is dropped at extraction time, otherwise an ``hippo_facts_search``
  call would itself trigger the hook → recall → emit → infinite
  cascade of MCP calls.
* **Latency budget**: ``StepInjector.inject`` is single-call; with the
  embedding daemon warm it returns in <100 ms on a 1.5k-fact corpus.
  With the daemon offline it short-circuits to ``[]`` and the hook
  returns silently.
* **Dependency injection seam**: ``run(payload, agent_factory=...)``
  takes a callable that returns an agent shim — pytest passes a
  tmp_path-backed fixture; the wrapper script passes the default
  factory that loads ``HIPPO_DATA_DIR`` / ``~/.engram``.

API
---
``extract_step_text(tool_name, tool_input) -> str``
    Pure function. Returns the per-tool sub-goal we recall against
    (Bash command, Edit/Write/Read file_path with a verb, Grep/Glob
    pattern). Returns ``""`` for unknown tools or hippoagent MCP self
    calls.

``run(payload, agent_factory=None) -> str``
    Pure function. Returns the banner string or ``""``. Never raises.

``main_stdin_stdout(stdin, stdout, agent_factory=None) -> int``
    CLI entry. Reads JSON from ``stdin``, writes banner to ``stdout``,
    returns 0 always (graceful on every error path).
"""
from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

# How many characters of the extracted "step text" to keep before
# passing it to the recall layer. Long Bash one-liners or copy-pasted
# file content would dilute keyword overlap and slow recall.
_STEP_TEXT_MAX_LEN = 500

# Below this length we treat the step as too generic to recall against.
# "ls", "pwd", "cd ..", short greps would otherwise emit noise.
_STEP_TEXT_MIN_LEN = 8

# Tool name prefixes we always skip — anti-loop guard so the hook does
# not call back into its own backing store and recurse via the LLM.
_SKIP_TOOL_PREFIXES: tuple[str, ...] = ("mcp__hippoagent__",)


def _bash_extractor(tool_input: Mapping[str, Any]) -> str:
    return str(tool_input.get("command", "") or "")


def _edit_extractor(tool_input: Mapping[str, Any]) -> str:
    fp = str(tool_input.get("file_path", "") or "")
    return f"edit {fp}".strip()


def _write_extractor(tool_input: Mapping[str, Any]) -> str:
    fp = str(tool_input.get("file_path", "") or "")
    return f"write {fp}".strip()


def _read_extractor(tool_input: Mapping[str, Any]) -> str:
    return str(tool_input.get("file_path", "") or "")


def _grep_extractor(tool_input: Mapping[str, Any]) -> str:
    return str(tool_input.get("pattern", "") or "")


def _glob_extractor(tool_input: Mapping[str, Any]) -> str:
    return str(tool_input.get("pattern", "") or "")


#: One extractor per Claude Code tool name we care about. Tools not in
#: this dict return ``""`` from :func:`extract_step_text`.
_EXTRACTORS: dict[str, Callable[[Mapping[str, Any]], str]] = {
    "Bash": _bash_extractor,
    "PowerShell": _bash_extractor,
    "Edit": _edit_extractor,
    "Write": _write_extractor,
    "Read": _read_extractor,
    "Grep": _grep_extractor,
    "Glob": _glob_extractor,
}


def extract_step_text(
    tool_name: str, tool_input: Mapping[str, Any] | None,
) -> str:
    """Return the "step text" we will recall facts against.

    Drops hippoagent MCP tool names up-front (anti-loop) and truncates
    the result to :data:`_STEP_TEXT_MAX_LEN` to keep downstream latency
    bounded.
    """
    if not isinstance(tool_name, str) or not tool_name:
        return ""
    if any(tool_name.startswith(p) for p in _SKIP_TOOL_PREFIXES):
        return ""
    if tool_input is None:
        return ""
    ext = _EXTRACTORS.get(tool_name)
    if ext is None:
        return ""
    try:
        raw = ext(tool_input) or ""
    except (AttributeError, TypeError):
        return ""
    return raw.strip()[:_STEP_TEXT_MAX_LEN]


def _default_agent_factory() -> Any | None:
    """Best-effort agent loader: opens the local SemanticMemory under
    ``HIPPO_DATA_DIR`` (or ``~/.engram``) and returns a minimal shim
    with the ``semantic`` attribute :class:`StepInjector` requires.

    Returns ``None`` if the data dir is missing — the hook then degrades
    to silent.
    """
    data_dir = None
    for env_key in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR"):
        v = os.environ.get(env_key)
        if v:
            p = Path(v)
            if p.exists():
                data_dir = p
                break
    if data_dir is None:
        for cand in (
            Path.home() / ".engram",
            Path.home() / ".hippoagent" / "data",
        ):
            if cand.exists():
                data_dir = cand
                break
    if data_dir is None:
        return None
    # Try common DB names — match the SessionStart hook layout.
    sem_db: Path | None = None
    for name in ("semantic.db", "semantic/semantic.db"):
        c = data_dir / name
        if c.exists():
            sem_db = c
            break
    if sem_db is None:
        return None
    try:
        from verimem.semantic import SemanticMemory  # noqa: PLC0415
        sm = SemanticMemory(db_path=sem_db)
    except Exception:  # noqa: BLE001 — never crash the host tool
        return None

    class _AgentShim:
        semantic = sm
    return _AgentShim()


def _render_banner(tool_name: str, hits: list[dict[str, Any]]) -> str:
    """Render the ``<engram-step-recall>`` banner. Same shape style
    as :mod:`hippo_proactive_briefing` for visual consistency.
    """
    lines = [f"<engram-step-recall tool={tool_name} hits={len(hits)}>"]
    for h in hits:
        prop = (h.get("proposition") or "")[:120]
        topic = h.get("topic") or ""
        sim = float(h.get("similarity") or 0.0)
        lines.append(f"- [sim {sim:.2f}] {topic} — {prop}")
    lines.append("</engram-step-recall>")
    return "\n".join(lines)


def run(
    payload: Mapping[str, Any],
    *,
    agent_factory: Callable[[], Any | None] | None = None,
) -> str:
    """Apply the hook logic to one PreToolUse payload.

    Returns the banner string (possibly empty). Never raises.

    Parameters
    ----------
    payload:
        The Claude Code PreToolUse JSON. Keys we use:
        ``tool_name`` (str), ``tool_input`` (dict). Other keys ignored.
    agent_factory:
        Callable that returns the agent shim. When ``None``, falls
        back to :func:`_default_agent_factory`. Tests inject an
        in-memory shim so they don't depend on a live data dir.
    """
    if not isinstance(payload, Mapping):
        return ""
    tool_name = str(payload.get("tool_name", "") or "")
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, Mapping):
        return ""
    step = extract_step_text(tool_name, tool_input)
    if len(step) < _STEP_TEXT_MIN_LEN:
        return ""

    factory = agent_factory or _default_agent_factory
    try:
        agent = factory()
    except Exception:  # noqa: BLE001 — fail soft, never block tool
        return ""
    if agent is None:
        return ""

    # Lazy import: keeps the hook script import light when the host
    # turns it off via env var (a non-test caller can do
    # `HIPPO_HOOK_DISABLE=1` and skip the whole machinery).
    try:
        from verimem.proactive_step_injector import (  # noqa: PLC0415
            StepInjector,
        )
        injector = StepInjector(agent)
        hits = injector.inject(step, top_k=3, min_similarity=0.30)
    except Exception:  # noqa: BLE001
        return ""

    if not hits:
        return ""
    return _render_banner(tool_name, hits)


def main_stdin_stdout(
    stdin: Any | None = None,
    stdout: Any | None = None,
    *,
    agent_factory: Callable[[], Any | None] | None = None,
) -> int:
    """CLI entry point. Reads JSON from ``stdin`` (default ``sys.stdin``),
    writes banner to ``stdout`` (default ``sys.stdout``). Returns 0
    on every path so the hook never blocks a tool call.
    """
    src = stdin if stdin is not None else sys.stdin
    sink = stdout if stdout is not None else sys.stdout
    try:
        raw = src.read()
    except Exception:  # noqa: BLE001
        return 0
    raw = (raw or "").strip()
    if not raw:
        return 0
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return 0
    if not isinstance(payload, Mapping):
        return 0
    banner = run(payload, agent_factory=agent_factory)
    if banner:
        try:
            sink.write(banner)
            sink.write("\n")
        except Exception:  # noqa: BLE001
            return 0
    return 0
