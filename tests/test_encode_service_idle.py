"""Encode-daemon idle timeout — keep the embedding model warm (TDD, RED first).

Root cause of the save/recall "hang" (2026-06-05): the shared encode daemon
self-exits after IDLE_TIMEOUT_S with no requests. The legacy default was
30 min, so during a normal work session the daemon idle-died and the next
store()/recall() cold-loaded the model in-process (~22s). Fix: a much longer,
env-configurable idle window (survive a work session; clean up overnight),
so the daemon stays warm and encodes stay ~40ms.
"""
from __future__ import annotations

import verimem.encode_service as es


def test_idle_timeout_default_is_long_enough_to_survive_a_session(monkeypatch):
    monkeypatch.delenv("ENGRAM_ENCODE_IDLE_S", raising=False)
    # The 30-min (=1800s) legacy default was the bug. The new default must be
    # comfortably longer than any realistic gap between memory operations.
    assert es._idle_timeout_s() >= 3600.0


def test_idle_timeout_env_override(monkeypatch):
    monkeypatch.setenv("ENGRAM_ENCODE_IDLE_S", "123")
    assert es._idle_timeout_s() == 123.0


def test_idle_timeout_env_zero_disables(monkeypatch):
    # 0 = never idle-exit (explicit opt-in to a permanent daemon).
    monkeypatch.setenv("ENGRAM_ENCODE_IDLE_S", "0")
    assert es._idle_timeout_s() == 0.0


def test_idle_timeout_ignores_garbage_env(monkeypatch):
    monkeypatch.setenv("ENGRAM_ENCODE_IDLE_S", "not-a-number")
    assert es._idle_timeout_s() >= 3600.0  # falls back to the safe default
