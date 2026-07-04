"""Startup self-heal — re-embed stale rows on server boot (structural safety).

PR #208 made ``SemanticMemory.backfill_pending_embeddings`` heal ANY row that
is invisible to semantic recall (empty blob, wrong dim, or wrong/NULL
``embedding_model``), not just empty blobs. But that healing MECHANISM only
ran on demand (the ``engram facts backfill`` CLI / the
``hippo_backfill_embeddings`` tool). Nothing triggered it, so a corpus left
inconsistent by any writer (e.g. an old client that wrote the wrong model)
stayed silently unrecallable until a human noticed.

This module is the TRIGGER: a best-effort, bounded, env-gated background pass
fired once at MCP-server startup, right after the embedding preload. It is:
  - non-blocking — runs on a daemon thread, so boot/serving never waits;
  - delegate-friendly — waits for the shared encode daemon to warm first, so
    healing encodes go through the daemon, not an in-process cold load on the
    serving path;
  - bounded — at most ``limit`` rows per pass (default 200), and the underlying
    UPDATE commits per row, so it never holds the write lock across an O(N) loop
    (the historical save-hang root cause);
  - crash-proof — every error is swallowed; a broken heal must never break boot;
  - opt-out — set ``HIPPO_STARTUP_SELFHEAL=0`` to disable.

Idempotent by construction: once a row is at the active model/dim it no longer
matches the backfill SELECT, so steady-state passes are no-ops (return 0).
"""
from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from typing import Any

#: Max rows healed per startup pass. Bounded so a large legacy backlog can't
#: turn boot into an encode storm; the next restart picks up the remainder.
_DEFAULT_LIMIT = 200

#: Seconds the background thread waits for the shared encode daemon to warm
#: before giving up (it still heals via whatever encode() resolves to, but we
#: prefer the daemon so we never cold-load on this process).
_DAEMON_WARM_WAIT_S = 25.0

_FALSY = {"0", "false", "no", "off"}


def _enabled() -> bool:
    return os.environ.get("HIPPO_STARTUP_SELFHEAL", "1").strip().lower() not in _FALSY


def _run_self_heal(
    get_agent: Callable[[], Any],
    *,
    limit: int = _DEFAULT_LIMIT,
    log: Any = None,
) -> int:
    """Heal up to ``limit`` stale rows. Returns the heal count; never raises.

    ``get_agent`` is a zero-arg callable returning the agent (lazily built),
    kept as a callable so importing/scheduling this never forces agent
    construction. A None/sem-less agent or any encode error yields 0.
    """
    if not _enabled():
        return 0
    try:
        agent = get_agent()
        sm = getattr(agent, "semantic", None)
        if sm is None:
            return 0
        n = int(sm.backfill_pending_embeddings(limit=limit) or 0)
        if n and log is not None:
            log.info("startup_self_heal_reembedded", count=n)
        return n
    except Exception as exc:  # noqa: BLE001 — self-heal must NEVER crash boot
        if log is not None:
            log.warning("startup_self_heal_failed", error=str(exc))
        return 0


def _wait_daemon_warm(timeout_s: float = _DAEMON_WARM_WAIT_S) -> bool:
    """Best-effort wait until the shared encode daemon serves the active model.

    Returns True if it warmed within the window, False otherwise (we proceed
    either way — the heal is best-effort)."""
    try:
        from . import encode_service
    except Exception:  # noqa: BLE001 — encode service optional
        return False
    deadline = time.time() + max(0.0, timeout_s)
    while time.time() < deadline:
        try:
            if encode_service.daemon_usable():
                return True
        except Exception:  # noqa: BLE001 — probe failure is non-fatal
            return False
        time.sleep(1.0)
    return False


def start_self_heal(
    get_agent: Callable[[], Any],
    *,
    limit: int = _DEFAULT_LIMIT,
    log: Any = None,
) -> threading.Thread | None:
    """Fire the self-heal pass on a background daemon thread. Returns the
    thread, or None when disabled by env. Never blocks the caller."""
    if not _enabled():
        return None

    def _run() -> None:
        # Prefer the shared daemon so healing encodes don't cold-load this
        # process; proceed best-effort even if it never warms.
        _wait_daemon_warm()
        _run_self_heal(get_agent, limit=limit, log=log)

    thread = threading.Thread(target=_run, name="hippo-self-heal", daemon=True)
    thread.start()
    return thread


__all__ = ["start_self_heal", "_run_self_heal", "_wait_daemon_warm", "_DEFAULT_LIMIT"]
