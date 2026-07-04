"""Embedding model load must NEVER hang the agent (TDD, RED first).

Root cause of the 2026-06-05 4-hour save/recall hang (confirmed):
- `_load_model()` tries `SentenceTransformer(model, local_files_only=True)`
  and, on ANY exception, falls back to `SentenceTransformer(model)` WITH the
  network. A flaky / rate-limited HF Hub can make that network load STALL
  indefinitely.
- That load runs inside `with _MODEL_LOCK:` (non-bounded). A stalled loader
  holds the lock forever, so EVERY other thread calling `_model()` blocks on
  the lock forever -> the whole process can no longer embed = infinite hang.

Two guarantees pinned here:
1. When an offline flag is set (the production config), `_load_model` must NOT
   fall back to the network — re-raise instead (fail fast, never stall).
2. `_model()` must not wait on `_MODEL_LOCK` forever — a wedged loader makes
   waiters raise after a bounded timeout, never hang.
"""
from __future__ import annotations

import pytest

import engram.embedding as emb

_OFFLINE_VARS = ("HIPPO_OFFLINE", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE",
                 "ENGRAM_OFFLINE")


def _clear_offline(monkeypatch):
    for v in _OFFLINE_VARS:
        monkeypatch.delenv(v, raising=False)


def test_load_model_offline_reraises_instead_of_network(monkeypatch):
    calls = []

    class _FakeST:
        def __init__(self, model, local_files_only=False):
            calls.append("local" if local_files_only else "network")
            if local_files_only:
                raise OSError("simulated: not in local cache")
            # network path — must NOT be reached when offline

    monkeypatch.setattr("sentence_transformers.SentenceTransformer", _FakeST)
    _clear_offline(monkeypatch)
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")

    with pytest.raises(Exception):
        emb._load_model()
    assert "network" not in calls, (
        "offline -> _load_model must NOT fall back to the network (that stall "
        "under _MODEL_LOCK was the 4h hang)"
    )


def test_load_model_online_may_fall_back_to_network(monkeypatch):
    calls = []

    class _FakeST:
        def __init__(self, model, local_files_only=False):
            calls.append("local" if local_files_only else "network")
            if local_files_only:
                raise OSError("simulated: not in local cache")
            # network path returns a dummy "model"

    monkeypatch.setattr("sentence_transformers.SentenceTransformer", _FakeST)
    _clear_offline(monkeypatch)  # fully online

    emb._load_model()  # must not raise — network fallback allowed when online
    assert calls == ["local", "network"]


def test_model_does_not_hang_when_lock_is_wedged():
    """A wedged loader holding _MODEL_LOCK must make a caller RAISE after the
    timeout, never block forever (the 4h-hang failure mode).

    Run in a FRESH subprocess: the conftest autouse fixture stubs
    ``embedding._model`` in-process, so the genuine lock logic can only be
    exercised out-of-process (also the realistic setting — the hang was a
    process-wide model lock).
    """
    import subprocess
    import sys
    import textwrap

    script = textwrap.dedent(
        """
        import threading
        import engram.embedding as emb
        emb._MODEL_LOCK_TIMEOUT_S = 0.3
        emb._MODEL = None
        emb._MODEL_LOCK.acquire()  # simulate a wedged loader holding the lock
        res = {}
        def call():
            try:
                emb._model()
                res['r'] = 'no-raise'
            except RuntimeError:
                res['r'] = 'RuntimeError'
            except Exception as exc:  # noqa: BLE001
                res['r'] = type(exc).__name__
        t = threading.Thread(target=call)
        t.start()
        t.join(5)
        print('ALIVE' if t.is_alive() else 'DONE', res.get('r'))
        """
    )
    out = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=40,
    )
    assert "DONE RuntimeError" in out.stdout, (
        "real _model() must RAISE (not hang) when _MODEL_LOCK is wedged.\n"
        f"stdout={out.stdout!r}\nstderr={out.stderr[-400:]!r}"
    )
