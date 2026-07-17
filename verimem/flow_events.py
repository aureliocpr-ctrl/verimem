"""Flow-event fan-out for the LIVE Engine Room — emitted at the CORE.

Every ``Memory.add`` / ``search`` / ``explain`` emits a ``flow.write`` /
``flow.recall`` event through :mod:`verimem.observability` (BUS + structlog +
``events.jsonl`` — the jsonl is the cross-process bus the live surfaces tail:
``/ui/engine`` in the gateway, ``verimem flow tail`` in a terminal).

Because the emission lives in the core, EVERY surface is covered: the REST
gateway, the MCP server (Claude Code, Cursor, or ANY other vendor's agent
that mounts it), plain SDK use, the CLI. Events carry flow METADATA only
(status/score/ids/topic) — never fact content.

Tagging:

* ``surface`` — where the call came from: ``sdk`` (default), ``mcp``,
  ``gateway``. Ambient default via env ``ENGRAM_FLOW_SURFACE`` (set once by
  the MCP server at bootstrap — env, not contextvar, so it survives thread
  pools); per-request override via :func:`set_flow_context`.
* ``actor`` — the agent's label, from env ``VERIMEM_ACTOR`` (or legacy
  ``ENGRAM_ACTOR``): a codex/gemini/gpt agent sets it in its MCP config and
  every one of its events arrives labeled — the single multi-agent panel.
* ``tenant`` — gateway only, via :func:`set_flow_context` (contextvar,
  per-request); the gateway's ``/v1/events/flow`` privacy filter matches on
  it, so core events without a tenant are never streamed to a tenant.

Best-effort by contract: :func:`emit_flow` NEVER raises into the caller's
write/read path.
"""
from __future__ import annotations

import contextvars
import os
from typing import Any

_CTX: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "verimem_flow_ctx", default=None)


def set_flow_context(**fields: Any) -> contextvars.Token:
    """Overlay ambient fields onto every flow event in this context
    (gateway: ``tenant`` + ``surface``). ``None`` values are dropped.
    Returns the token for :func:`reset_flow_context`."""
    cur = dict(_CTX.get() or {})
    cur.update({k: v for k, v in fields.items() if v is not None})
    return _CTX.set(cur)


def reset_flow_context(token: contextvars.Token | None = None) -> None:
    """Clear the overlay (or restore to ``token`` if given)."""
    if token is not None:
        _CTX.reset(token)
    else:
        _CTX.set(None)


def _ambient() -> dict[str, Any]:
    out: dict[str, Any] = {
        "surface": os.environ.get("ENGRAM_FLOW_SURFACE", "").strip() or "sdk",
    }
    actor = (os.environ.get("VERIMEM_ACTOR", "").strip()
             or os.environ.get("ENGRAM_ACTOR", "").strip())
    if actor:
        out["actor"] = actor
    out.update(_CTX.get() or {})
    return out


def emit_flow(name: str, **payload: Any) -> None:
    """Emit one flow event (ambient tags + ``payload``). Never raises."""
    try:
        from .observability import emit
        merged = _ambient()
        merged.update(payload)
        emit(name, **merged)
    except Exception:  # noqa: BLE001 — observability never breaks the path
        pass
