"""P0 cold-start reliability: model-aware daemon readiness + thread-safe agent
singleton + a no-load warmth probe.

Root cause of the observed MCP "cold hang": a 20s in-process embedding load runs
(triggered by preload / a first semantic encode) and starves the request thread.
Two concrete, provable bugs feed it:

  1. `preload` decided "a daemon is up, skip warming THIS process" using a
     MODEL-BLIND reachability check (`is_reachable`), while `embedding.encode`
     REJECTS a daemon whose model != CONFIG (model-aware). So a stale/wrong-model
     daemon (e.g. left over across the e5 flip) made preload skip the local warm
     AND made every encode cold-load in-process. Fixed by a model-aware
     `encode_service.daemon_usable()` used on both sides.

  2. `_ag()` lazy-built the agent with NO lock: concurrent first calls each ran
     `HippoAgent.build()`. Fixed with double-checked locking.

Plus `embedding.is_loaded()` — a pure, no-load readiness probe so callers can
tell whether a semantic call will be warm or pay the cold cliff.

Hermetic: no model load, no MCP server, no real daemon socket.
"""
from __future__ import annotations

import threading

from engram import embedding, encode_service
from engram.config import CONFIG

# --- model-aware daemon readiness -----------------------------------------

def test_daemon_usable_false_when_model_mismatch(monkeypatch):
    # A daemon is reachable but advertises a DIFFERENT model than CONFIG ->
    # not usable (encode would reject it; preload must not trust it).
    monkeypatch.setattr(encode_service, "is_reachable", lambda *a, **k: True)
    info = {"host": "127.0.0.1", "port": 5555, "model": "some/other-model", "dim": 999}
    assert encode_service.daemon_usable(info) is False


def test_daemon_usable_true_when_model_matches_and_reachable(monkeypatch):
    monkeypatch.setattr(encode_service, "is_reachable", lambda *a, **k: True)
    info = {"host": "127.0.0.1", "port": 5555,
            "model": CONFIG.embedding_model, "dim": CONFIG.embedding_dim}
    assert encode_service.daemon_usable(info) is True


def test_daemon_usable_false_when_matching_model_but_unreachable(monkeypatch):
    # Right model on paper but the port is dead -> not usable.
    monkeypatch.setattr(encode_service, "is_reachable", lambda *a, **k: False)
    info = {"host": "127.0.0.1", "port": 5555, "model": CONFIG.embedding_model}
    assert encode_service.daemon_usable(info) is False


def test_daemon_usable_false_when_no_discovery(monkeypatch):
    monkeypatch.setattr(encode_service, "read_discovery", lambda *a, **k: None)
    assert encode_service.daemon_usable() is False


# --- preload is model-aware (THE bug) --------------------------------------

def _run_preload_sync(monkeypatch):
    """Run preload synchronously and report whether the local warm fired."""
    import engram.preload as preload
    warmed = {"local": False}
    monkeypatch.setattr(preload, "_warm", lambda: warmed.__setitem__("local", True))
    monkeypatch.setattr(preload, "_DAEMON_WARM_WAIT_S", 0.0)  # no 25s wait in test
    monkeypatch.setenv("HIPPO_EAGER_PRELOAD", "1")
    monkeypatch.setenv("HIPPO_PRELOAD_BACKGROUND", "0")  # synchronous
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "1")
    preload.preload_embedding(log=None)
    return warmed["local"]


def test_preload_warms_local_when_daemon_mismatched(monkeypatch):
    # daemon present but wrong model -> preload MUST warm this process locally
    # (otherwise the server has no warm model and the first encode cold-loads).
    monkeypatch.setattr(encode_service, "daemon_usable", lambda *a, **k: False)
    monkeypatch.setattr(encode_service, "ensure_running", lambda *a, **k: False)
    assert _run_preload_sync(monkeypatch) is True


def test_preload_skips_local_when_daemon_usable(monkeypatch):
    # matching warm daemon -> skip local warm (RAM saved, no cold load needed).
    monkeypatch.setattr(encode_service, "daemon_usable", lambda *a, **k: True)
    monkeypatch.setattr(encode_service, "ensure_running", lambda *a, **k: True)
    assert _run_preload_sync(monkeypatch) is False


# --- no-load readiness probe ----------------------------------------------

def test_is_loaded_is_pure_no_load(monkeypatch):
    # Probe must NOT trigger a model load. Force the model slot empty and make
    # _load_model explode if anyone calls it.
    monkeypatch.setattr(embedding, "_MODEL", None)
    monkeypatch.setattr(embedding, "_load_model",
                        lambda: (_ for _ in ()).throw(AssertionError("must not load")))
    assert embedding.is_loaded() is False  # no exception => no load happened


def test_is_loaded_true_when_model_present(monkeypatch):
    monkeypatch.setattr(embedding, "_MODEL", object())
    assert embedding.is_loaded() is True


# --- thread-safe agent singleton -------------------------------------------

def test_ag_builds_exactly_once_under_concurrency(monkeypatch):
    import engram.mcp_server as srv

    calls = {"n": 0}

    class _Fake:
        pass

    def _slow_build():
        calls["n"] += 1
        # widen the race window so an unlocked _ag would build N times
        import time as _t
        _t.sleep(0.05)
        return _Fake()

    monkeypatch.setattr(srv, "_agent", None)
    monkeypatch.setattr(srv.HippoAgent, "build", staticmethod(_slow_build))

    results = []
    barrier = threading.Barrier(8)

    def worker():
        barrier.wait()  # release all threads at once
        results.append(srv._ag())

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    assert calls["n"] == 1, f"build() ran {calls['n']}x — _ag() is not locked"
    assert len({id(r) for r in results}) == 1  # all got the same instance
    monkeypatch.setattr(srv, "_agent", None)  # don't leak the fake to other tests
