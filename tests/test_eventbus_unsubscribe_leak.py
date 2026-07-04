"""Regression: EventBus wildcard-subscriber leak via the SSE memory-map endpoint.

Bug (found 2026-06-01): ``GET /api/memory-map/events`` calls
``BUS.subscribe("*", listener)`` but the SSE generator never unsubscribes, and
``EventBus`` had **no** ``unsubscribe`` method at all. So every SSE connect — and
every forced browser reconnect (the route itself closes the stream every
``max_seconds`` = 3600s) — permanently appended a closure to ``BUS._wildcards``.

The list only grew. Every process-wide ``emit()`` iterates it
(``observability.EventBus.emit``), so emission slowed linearly over the
dashboard's lifetime, and each closure (capturing a ``queue.Queue``) was never
GC'd.

Fix under test:
  1. ``EventBus.unsubscribe(event_name, fn)`` — removes ``fn`` from
     ``_wildcards`` (event_name == "*") or ``_subs[event_name]`` under the lock,
     tolerant of an already-removed / never-subscribed ``fn``.
  2. ``memory_map_events`` wraps the SSE generator body in ``try/finally`` that
     calls ``BUS.unsubscribe("*", listener)`` — so the listener is removed on
     normal ``max_seconds`` timeout, on ``CancelledError`` (client disconnect),
     and on any exception.
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from engram import settings as user_settings
from engram.observability import BUS, Event

# ---------------------------------------------------------------------------
# Unit: EventBus.unsubscribe
# ---------------------------------------------------------------------------


def test_unsubscribe_wildcard_returns_to_baseline() -> None:
    baseline = len(BUS._wildcards)

    def listener(evt: Event) -> None:  # pragma: no cover - never invoked
        pass

    BUS.subscribe("*", listener)
    assert len(BUS._wildcards) == baseline + 1

    BUS.unsubscribe("*", listener)
    assert len(BUS._wildcards) == baseline, (
        "unsubscribe('*', fn) must remove the wildcard subscriber"
    )


def test_unsubscribe_tolerant_of_already_removed() -> None:
    baseline = len(BUS._wildcards)

    def listener(evt: Event) -> None:  # pragma: no cover
        pass

    BUS.subscribe("*", listener)
    BUS.unsubscribe("*", listener)
    # Second removal of the same fn must NOT raise (tolerant of missing fn).
    BUS.unsubscribe("*", listener)
    # A never-subscribed fn is a no-op too.
    BUS.unsubscribe("*", lambda evt: None)
    assert len(BUS._wildcards) == baseline


def test_unsubscribe_named_subscriber() -> None:
    name = "regression_named_event_unsubscribe"
    baseline = len(BUS._subs.get(name, []))

    def listener(evt: Event) -> None:  # pragma: no cover
        pass

    BUS.subscribe(name, listener)
    assert len(BUS._subs[name]) == baseline + 1

    BUS.unsubscribe(name, listener)
    assert len(BUS._subs[name]) == baseline, (
        "unsubscribe(name, fn) must remove the named subscriber"
    )


# ---------------------------------------------------------------------------
# Integration: the SSE endpoint must unsubscribe its listener on close
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(
        user_settings, "SETTINGS_FILE", tmp_path / "user_settings.json"
    )
    return tmp_path


async def _wait_until(predicate, timeout: float = 3.0, interval: float = 0.02) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        await asyncio.sleep(interval)
    return predicate()


async def test_sse_connection_unsubscribes_listener_on_close(
    isolated_settings: Path,
) -> None:
    """One SSE request must leave ``BUS._wildcards`` at its pre-connect length.

    Pre-fix this fails: the per-connection ``listener`` closure stays appended
    to ``BUS._wildcards`` forever — that is the leak.
    """
    user_settings.save(user_settings.UserSettings(onboarded=True))
    from engram.dashboard import app

    baseline = len(BUS._wildcards)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with ac.stream(
            "GET",
            "/api/memory-map/events",
            params={"max_seconds": 0.5},
            timeout=10.0,
        ) as resp:
            assert resp.status_code == 200
            # Drain the stream to its natural end (max_seconds elapses).
            async for _line in resp.aiter_lines():
                pass

    ok = await _wait_until(lambda: len(BUS._wildcards) == baseline)
    assert ok, (
        f"SSE listener leaked: _wildcards={len(BUS._wildcards)} "
        f"expected baseline={baseline}. The generator must unsubscribe in finally."
    )


async def test_events_stream_unsubscribes_on_disconnect(
    isolated_settings: Path,
) -> None:
    """audit#3-r3 R0: the twin /api/events/stream endpoint had the SAME leak
    (subscribe('*') with no finally/unsubscribe) AND drove its generator with a
    blocking ``q.get(timeout=15)`` that froze the event loop and never
    self-terminated. After the fix it mirrors memory_map.py: a ``max_seconds``
    cap self-terminates the generator and the finally unsubscribes — so one full
    stream lifecycle must leave BUS._wildcards at its pre-connect length.
    """
    user_settings.save(user_settings.UserSettings(onboarded=True))
    from engram.dashboard import app

    baseline = len(BUS._wildcards)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with ac.stream(
            "GET",
            "/api/events/stream",
            params={"max_seconds": 0.5},
            timeout=10.0,
        ) as resp:
            assert resp.status_code == 200
            # Drain to the stream's natural end (max_seconds elapses). Pre-fix
            # this hung: the sync q.get(timeout=15) blocked the event loop and
            # there was no server-side cap to ever close the stream.
            async for _line in resp.aiter_lines():
                pass

    ok = await _wait_until(lambda: len(BUS._wildcards) == baseline)
    assert ok, (
        f"/api/events/stream leaked: _wildcards={len(BUS._wildcards)} "
        f"expected baseline={baseline}. gen() must unsubscribe in finally."
    )
