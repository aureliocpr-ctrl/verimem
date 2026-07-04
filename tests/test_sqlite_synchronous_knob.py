"""ENGRAM_SQLITE_SYNCHRONOUS knob (production-scaling review 2026-06-20).

The 4 DB modules hard-coded synchronous=NORMAL in 5 places; this centralizes the one
durability/throughput knob a deployment may tune. Default NORMAL (unchanged); FULL
gives per-commit fsync durability.
"""
from __future__ import annotations

from engram._sqlite_pragma import synchronous_mode


def test_default_is_normal(monkeypatch):
    monkeypatch.delenv("ENGRAM_SQLITE_SYNCHRONOUS", raising=False)
    assert synchronous_mode() == "NORMAL"


def test_full_when_set(monkeypatch):
    monkeypatch.setenv("ENGRAM_SQLITE_SYNCHRONOUS", "full")
    assert synchronous_mode() == "FULL"


def test_garbage_falls_back_to_normal(monkeypatch):
    monkeypatch.setenv("ENGRAM_SQLITE_SYNCHRONOUS", "banana")
    assert synchronous_mode() == "NORMAL"


def test_connection_reflects_full(monkeypatch, tmp_path):
    """Integration: the live SemanticMemory connection applies the knob (2 == FULL)."""
    monkeypatch.setenv("ENGRAM_SQLITE_SYNCHRONOUS", "FULL")
    from engram.semantic import SemanticMemory
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    with sm._connect() as conn:
        level = conn.execute("PRAGMA synchronous").fetchone()[0]
    assert level == 2  # 0=OFF, 1=NORMAL, 2=FULL


def test_connection_default_normal(monkeypatch, tmp_path):
    monkeypatch.delenv("ENGRAM_SQLITE_SYNCHRONOUS", raising=False)
    from engram.semantic import SemanticMemory
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    with sm._connect() as conn:
        level = conn.execute("PRAGMA synchronous").fetchone()[0]
    assert level == 1  # NORMAL (default, unchanged)
