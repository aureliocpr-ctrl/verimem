"""RAM-footprint hardening (2026-07-10) — the real-usage incident.

Measured on the user's machine after a clean reboot: TWO encode_service
daemons at ~1.9 GB each (spawn race — both load the model before either
writes discovery; the loser lingers 8h) and five MCP servers at ~590 MB each
(the preload warms the CrossEncoder in EVERY server process, even ones that
never serve a recall). ~9 GB resident at idle → pagefile thrash → dead mouse.

Fixes pinned here:
  * encode_service daemon takes an ATOMIC pid lock BEFORE loading the model;
    a second daemon exits immediately (cheap, no model load). Dead-pid locks
    are stolen, own-pid locks are re-entrant.
  * the MCP preload no longer warms the reranker by default
    (HIPPO_RERANK_PRELOAD=1 restores it). The recall path already lazy-loads
    the CE with a cold budget (bi-encoder order until warm), so the only cost
    is the first recalls of a fresh server — not ~450 MB × N idle servers.
"""
from __future__ import annotations

import os
import subprocess
import sys

from engram import encode_service, preload


# ---- daemon singleton lock ---------------------------------------------------

def test_acquire_lock_on_free_path(tmp_path):
    lock = tmp_path / "d.lock"
    assert encode_service.acquire_daemon_lock(lock) is True
    assert lock.read_text(encoding="utf-8").strip() == str(os.getpid())


def test_acquire_lock_reentrant_for_own_pid(tmp_path):
    lock = tmp_path / "d.lock"
    lock.write_text(str(os.getpid()), encoding="utf-8")
    assert encode_service.acquire_daemon_lock(lock) is True


def test_acquire_lock_refused_when_live_other_pid_holds_it(tmp_path):
    lock = tmp_path / "d.lock"
    lock.write_text(str(os.getppid()), encoding="utf-8")  # parent: alive, not us
    assert encode_service.acquire_daemon_lock(lock) is False


def test_acquire_lock_steals_dead_pid(tmp_path):
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait(timeout=30)
    dead_pid = proc.pid
    # On Windows the live Popen object holds a process HANDLE that keeps the
    # dead pid queryable; a crashed real daemon leaves no such handle. Drop it.
    del proc
    import gc
    gc.collect()
    assert not encode_service._pid_alive(dead_pid), "helper pid should be dead"
    lock = tmp_path / "d.lock"
    lock.write_text(str(dead_pid), encoding="utf-8")
    assert encode_service.acquire_daemon_lock(lock) is True
    assert lock.read_text(encoding="utf-8").strip() == str(os.getpid())


def test_acquire_lock_empty_file_not_stolen_while_writer_lands(tmp_path):
    """The O_EXCL winner creates the file THEN writes its pid — a reader in
    that gap sees an EMPTY lock. It must wait out the grace, see the landed
    pid, and yield (the 2026-07-10 double-daemon root cause, observed live:
    both daemons at 1.9 GB, lock owned by the thief)."""
    import threading
    import time as _t
    lock = tmp_path / "d.lock"
    lock.write_text("", encoding="utf-8")  # winner mid-flight

    def _land():
        _t.sleep(0.05)
        lock.write_text(str(os.getppid()), encoding="utf-8")  # alive, not us

    t = threading.Thread(target=_land)
    t.start()
    got = encode_service.acquire_daemon_lock(lock)
    t.join()
    assert got is False, "empty lock must not be stolen while a writer lands"


def test_acquire_lock_empty_file_stolen_after_grace(tmp_path):
    """An empty lock with NO writer landing is garbage → steal after grace."""
    lock = tmp_path / "d.lock"
    lock.write_text("", encoding="utf-8")
    assert encode_service.acquire_daemon_lock(lock) is True
    assert lock.read_text(encoding="utf-8").strip() == str(os.getpid())


def test_release_lock_only_own_pid(tmp_path):
    lock = tmp_path / "d.lock"
    lock.write_text(str(os.getppid()), encoding="utf-8")
    encode_service.release_daemon_lock(lock)
    assert lock.exists(), "someone else's lock must not be removed"
    lock.write_text(str(os.getpid()), encoding="utf-8")
    encode_service.release_daemon_lock(lock)
    assert not lock.exists()


def test_daemon_main_exits_before_model_load_when_lock_held(monkeypatch):
    calls = []
    monkeypatch.setattr(encode_service, "acquire_daemon_lock",
                        lambda *a, **k: False)
    import engram.embedding as emb
    monkeypatch.setattr(emb, "_encode_local",
                        lambda *a, **k: calls.append("load"))
    monkeypatch.setattr(encode_service.EncodeServer, "serve_forever",
                        lambda self: calls.append("serve"))
    encode_service.main()
    assert calls == [], "with the lock held elsewhere main() must do NOTHING"


# ---- preload: reranker warm is opt-in ----------------------------------------

def _quiet_preload_env(monkeypatch):
    monkeypatch.setenv("HIPPO_EAGER_PRELOAD", "1")
    monkeypatch.setenv("HIPPO_PRELOAD_BACKGROUND", "0")   # sync → assertable
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "0")      # never spawn a daemon
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")  # never warm embedder


def test_preload_skips_reranker_by_default(monkeypatch):
    _quiet_preload_env(monkeypatch)
    monkeypatch.delenv("HIPPO_RERANK_PRELOAD", raising=False)
    from engram import semantic
    called = []
    monkeypatch.setattr(semantic, "_rerank_enabled", lambda: True)
    monkeypatch.setattr(semantic, "_load_reranker",
                        lambda: called.append("ce") or (lambda pairs: []))
    preload.preload_embedding()
    assert called == [], "default MUST NOT warm the CE in the server process"


def test_preload_warms_reranker_when_opted_in(monkeypatch):
    _quiet_preload_env(monkeypatch)
    monkeypatch.setenv("HIPPO_RERANK_PRELOAD", "1")
    from engram import semantic
    called = []
    monkeypatch.setattr(semantic, "_rerank_enabled", lambda: True)
    monkeypatch.setattr(semantic, "_load_reranker",
                        lambda: called.append("ce") or (lambda pairs: []))
    preload.preload_embedding()
    assert called == ["ce"]
