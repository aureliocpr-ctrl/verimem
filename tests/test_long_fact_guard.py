"""S2 (F1 adversarial map) — non-silent guard for over-window facts.

F1 measured: QuALITY articles are 115/115 over the e5 512-token window
(median ~6.8k tokens). A direct ``Memory.add(long_document)`` embeds only the
head (~7%) and SILENTLY drops the rest — a user querying page 20 of a 30-page
PDF gets nothing, with no signal that anything was lost. The chunker
(``chunking.py`` / ``DocumentIndex``) is the right home for long docs, but a
raw store must not fail silently.

The guard is a WARNING (non-breaking, like L1.x): the fact is still stored,
but the ledger records that recall will only see the head, names the
attribution (whose content is this), and points at the document tier. Env
``ENGRAM_LONG_FACT_WARN_CHARS`` (default 2000 ≈ conservative 512-token
head; a heuristic — CJK packs more tokens per char, so this warns EARLY not
late). ``0`` disables.
"""
from __future__ import annotations

import logging

from verimem.semantic import Fact, SemanticMemory

SHORT = "The Eiffel Tower is in Paris."
LONG = "word " * 800  # ~4000 chars >> 2000 default


def _store(tmp_path, monkeypatch, prop, **kw):
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", "0")
    monkeypatch.setenv("ENGRAM_INJECTION_SCREEN", "0")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    f = Fact(proposition=prop, topic="doc/len", **kw)
    sm.store(f, embed="defer")
    return sm, f


def test_long_fact_warns_non_silent(tmp_path, monkeypatch, caplog):
    with caplog.at_level(logging.WARNING, logger="verimem.semantic"):
        _store(tmp_path, monkeypatch, LONG, writer_role="external_content")
    msgs = [r.message for r in caplog.records]
    assert any("embedder window" in m and "external_content" in m for m in msgs), (
        "an over-window fact must leave a ledger trace naming the truncation "
        "and the attribution (S2 non-silent)")


def test_short_fact_is_silent(tmp_path, monkeypatch, caplog):
    with caplog.at_level(logging.WARNING, logger="verimem.semantic"):
        _store(tmp_path, monkeypatch, SHORT)
    assert not any("embedder window" in r.message for r in caplog.records)


def test_long_fact_is_still_stored(tmp_path, monkeypatch):
    import sqlite3
    sm, f = _store(tmp_path, monkeypatch, LONG)
    with sqlite3.connect(sm.db_path) as conn:
        row = conn.execute(
            "SELECT proposition FROM facts WHERE id=?", (f.id,)).fetchone()
    assert row and len(row[0]) == len(LONG), (
        "the guard is a warning, never a truncation of the stored text")


def test_guard_disabled_with_zero(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("ENGRAM_LONG_FACT_WARN_CHARS", "0")
    with caplog.at_level(logging.WARNING, logger="verimem.semantic"):
        _store(tmp_path, monkeypatch, LONG)
    assert not any("embedder window" in r.message for r in caplog.records)
