"""Startup self-heal: on server boot, re-embed any stale (model/dim-mismatched)
rows so a corpus left inconsistent by any writer becomes recallable without a
manual `engram facts backfill` (structural-safety trigger, 2026-06-13).

backfill_pending_embeddings (the healing MECHANISM, PR #208) is only invoked
on-demand by the CLI and the hippo_backfill_embeddings tool — nothing runs it
periodically, so a mislabelled save stays unrecallable until a human notices.
This wires it as a best-effort, bounded, env-gated background pass at server
startup. It must NEVER block or crash boot, and must delegate to the shared
encode daemon (no in-process cold-load on the serving path).

Contract pinned here (the sync core; the thread wrapper just schedules it):
  - _run_self_heal(get_agent) calls agent.semantic.backfill_pending_embeddings
    with the configured limit and returns the heal count;
  - it NEVER raises (a broken agent / encode error yields 0);
  - HIPPO_STARTUP_SELFHEAL=0 disables it (returns 0, no call);
  - start_self_heal returns a daemon Thread (or None when disabled).
"""
from __future__ import annotations

import threading

import verimem.self_heal as sh


class _FakeSemantic:
    def __init__(self, *, ret=0, boom=False):
        self.ret = ret
        self.boom = boom
        self.calls: list[int | None] = []

    def backfill_pending_embeddings(self, *, limit=None):
        self.calls.append(limit)
        if self.boom:
            raise RuntimeError("encode exploded")
        return self.ret


class _FakeAgent:
    def __init__(self, sem):
        self.semantic = sem


def test_run_self_heal_calls_backfill_with_limit(monkeypatch):
    monkeypatch.delenv("HIPPO_STARTUP_SELFHEAL", raising=False)
    sem = _FakeSemantic(ret=7)
    n = sh._run_self_heal(lambda: _FakeAgent(sem), limit=200)
    assert n == 7
    assert sem.calls == [200], "must call backfill once with the bounded limit"


def test_run_self_heal_never_raises_on_error(monkeypatch):
    monkeypatch.delenv("HIPPO_STARTUP_SELFHEAL", raising=False)
    sem = _FakeSemantic(boom=True)
    # must swallow the encode error and report 0 — boot must never crash
    assert sh._run_self_heal(lambda: _FakeAgent(sem), limit=50) == 0


def test_run_self_heal_never_raises_on_bad_agent(monkeypatch):
    monkeypatch.delenv("HIPPO_STARTUP_SELFHEAL", raising=False)

    def _boom_agent():
        raise RuntimeError("agent build failed")

    assert sh._run_self_heal(_boom_agent, limit=50) == 0


def test_run_self_heal_disabled_by_env(monkeypatch):
    monkeypatch.setenv("HIPPO_STARTUP_SELFHEAL", "0")
    sem = _FakeSemantic(ret=3)
    n = sh._run_self_heal(lambda: _FakeAgent(sem), limit=200)
    assert n == 0
    assert sem.calls == [], "disabled gate must not touch the corpus"


def test_start_self_heal_returns_daemon_thread(monkeypatch):
    monkeypatch.delenv("HIPPO_STARTUP_SELFHEAL", raising=False)
    # don't actually wait for a real encode daemon in the test
    monkeypatch.setattr(sh, "_wait_daemon_warm", lambda *a, **k: True)
    sem = _FakeSemantic(ret=1)
    t = sh.start_self_heal(lambda: _FakeAgent(sem))
    assert isinstance(t, threading.Thread)
    assert t.daemon, "self-heal thread must be a daemon (never blocks shutdown)"
    t.join(timeout=5)
    assert sem.calls == [sh._DEFAULT_LIMIT]


def test_start_self_heal_none_when_disabled(monkeypatch):
    monkeypatch.setenv("HIPPO_STARTUP_SELFHEAL", "0")
    t = sh.start_self_heal(lambda: _FakeAgent(_FakeSemantic()))
    assert t is None


def test_startup_wires_self_heal_after_preload():
    """Pin the INTEGRATION, not just the module: mcp_server.main() must invoke
    start_self_heal AFTER preload_embedding. Without this, deleting the single
    wiring line leaves every other test green (the adversarial-review caveat) —
    the trigger would silently never fire on real server boot."""
    import inspect

    import verimem.mcp_server as srv

    src = inspect.getsource(srv.main)
    assert "start_self_heal" in src, "main() must wire the startup self-heal trigger"
    assert "preload_embedding" in src, "main() must preload before self-heal"
    assert src.index("preload_embedding") < src.index("start_self_heal"), (
        "self-heal must fire AFTER preload so heals delegate to the warm daemon"
    )
