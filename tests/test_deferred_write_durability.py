"""P1 (audit 2026-06-07): deferred-write durability.

``semantic.store_within_budget()`` offloads a contended SQLite write to a
DAEMON thread and returns ``{"deferred": True}`` once the write budget elapses.
Two production-grade gaps closed here:

1. **No flush-on-exit.** Daemon threads are killed abruptly when the interpreter
   exits, so an in-flight deferred write was LOST at shutdown — the "the write
   is NOT lost" claim in the docstring only held while the process stayed alive.
   A ``_flush_pending_writes()`` ``atexit`` handler now waits (bounded) for them.
2. **Swallowed errors.** A deferred write that failed AFTER the budget set
   ``box["err"]`` but nobody ever observed it -> silent data loss with no log.
   The worker now logs the failure regardless.
"""
from __future__ import annotations

import logging
import threading
import time

import pytest

from engram import semantic


def test_flush_pending_writes_joins_inflight() -> None:
    """The atexit flush must actually WAIT for an in-flight deferred write."""
    done: list[int] = []

    def slow() -> None:
        time.sleep(0.3)
        done.append(1)

    t = threading.Thread(target=slow, name="hippo-store-budget", daemon=True)
    with semantic._PENDING_WRITES_LOCK:
        semantic._PENDING_WRITES.add(t)
    t.start()
    try:
        still = semantic._flush_pending_writes(timeout_s=5.0)
        assert still == 0, "flush returned before the in-flight write finished"
        assert done == [1], "flush did not actually wait for the write to land"
    finally:
        with semantic._PENDING_WRITES_LOCK:
            semantic._PENDING_WRITES.discard(t)


def test_flush_pending_writes_reports_unfinished() -> None:
    """A write still stuck past the timeout is reported (not silently dropped)."""
    stop = threading.Event()

    def stuck() -> None:
        stop.wait(10.0)

    t = threading.Thread(target=stuck, name="hippo-store-budget", daemon=True)
    with semantic._PENDING_WRITES_LOCK:
        semantic._PENDING_WRITES.add(t)
    t.start()
    try:
        still = semantic._flush_pending_writes(timeout_s=0.2)
        assert still == 1, "flush should report the still-running write"
    finally:
        stop.set()
        with semantic._PENDING_WRITES_LOCK:
            semantic._PENDING_WRITES.discard(t)


def test_deferred_store_error_is_not_swallowed(caplog: pytest.LogCaptureFixture) -> None:
    """A failing budgeted/deferred store must be logged, never silently dropped."""
    class _Boom:
        def store(self, fact, **kwargs):  # noqa: ANN001, ANN201, ARG002
            raise RuntimeError("disk full sim")

    with caplog.at_level(logging.WARNING, logger="engram.semantic"):
        with pytest.raises(RuntimeError):
            semantic.store_within_budget(_Boom(), object(), budget_s=5.0)
    assert any(
        "disk full sim" in r.getMessage() or "store failed" in r.getMessage()
        for r in caplog.records
    ), "deferred/budgeted store error was not logged (silently swallowed)"
