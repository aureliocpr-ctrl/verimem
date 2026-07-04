"""Non-blocking store: decouple persistence from embedding (TDD, RED first).

Root cause (measured 2026-06-05): SemanticMemory.store() and recall() call
embedding.encode() synchronously. With the embedding daemon down, encode
cold-loads the model = ~22s -> a save/recall "hangs". With the daemon warm =
40ms. The robust fix: a save must NEVER block on a cold embed.

This adds an opt-in ``embed`` mode to store():
  - "sync"  (DEFAULT) = current behaviour, byte-identical (embed now).
  - "defer"           = persist the row immediately with a NULL embedding;
                        a background ``backfill_pending_embeddings()`` (or the
                        daemon) computes it later. Save is always fast.
  - "auto"            = embed now IFF the daemon is warm, else defer.

A NULL-embedding row is invisible to SEMANTIC recall (cosine needs a vector)
but still findable by KEYWORD search immediately, and becomes recallable once
backfilled. recall() must stay robust (never crash) with pending rows present.
"""
from __future__ import annotations

import pytest

from engram.semantic import Fact, SemanticMemory


def _ids(results) -> list[str]:
    """Normalise recall output (Fact or (Fact, score)) to a list of ids."""
    out: list[str] = []
    for r in results or []:
        f = r[0] if isinstance(r, (tuple, list)) else r
        fid = getattr(f, "id", None)
        if fid is not None:
            out.append(fid)
    return out


def _kw_ids(results) -> list[str]:
    out: list[str] = []
    for r in results or []:
        f = r[0] if isinstance(r, (tuple, list)) else r
        fid = getattr(f, "id", None)
        if fid is not None:
            out.append(fid)
    return out


def test_store_sync_default_is_recallable(tmp_path):
    m = SemanticMemory(db_path=tmp_path / "s.db")
    f = Fact(proposition="The cache holds 1024 entries.", topic="eng/cache")
    m.store(f)  # default = sync, unchanged behaviour
    assert f.id in _ids(m.recall("cache entries bounded", k=5))


def test_store_defer_excluded_from_semantic_recall_but_keyword_findable(tmp_path):
    m = SemanticMemory(db_path=tmp_path / "s.db")
    f = Fact(proposition="Deferred fact about 4096 widgets.", topic="eng/x")
    m.store(f, embed="defer")
    # no embedding yet -> NOT in semantic recall
    assert f.id not in _ids(m.recall("widgets deferred", k=10))
    # but immediately findable by keyword (no embedding needed)
    assert f.id in _kw_ids(m.search_facts("widgets"))


def test_backfill_makes_deferred_recallable(tmp_path):
    m = SemanticMemory(db_path=tmp_path / "s.db")
    f = Fact(proposition="Backfill me, 777 tokens please.", topic="eng/y")
    m.store(f, embed="defer")
    n = m.backfill_pending_embeddings()
    assert n == 1
    assert f.id in _ids(m.recall("backfill tokens", k=10))
    # idempotent: nothing left pending
    assert m.backfill_pending_embeddings() == 0


def test_store_auto_defers_when_daemon_unusable(tmp_path, monkeypatch):
    import engram.encode_service as es
    monkeypatch.setattr(es, "daemon_usable", lambda: False)
    _heal = []
    # spy: must NOT spawn a real daemon in tests, and must self-heal (kick it).
    monkeypatch.setattr(es, "ensure_running", lambda: _heal.append(1) or False)
    m = SemanticMemory(db_path=tmp_path / "s.db")
    f = Fact(proposition="Auto-mode fact, 55 ms latency.", topic="eng/z")
    m.store(f, embed="auto")
    assert f.id not in _ids(m.recall("latency auto", k=10))  # deferred
    assert _heal  # auto-defer woke the daemon (self-heal for backfill/next)
    assert m.backfill_pending_embeddings() == 1


def test_store_auto_embeds_when_daemon_usable(tmp_path, monkeypatch):
    import engram.encode_service as es
    monkeypatch.setattr(es, "daemon_usable", lambda: True)
    m = SemanticMemory(db_path=tmp_path / "s.db")
    f = Fact(proposition="Auto-mode warm fact, 99 widgets.", topic="eng/w")
    m.store(f, embed="auto")
    # daemon warm -> embedded now -> immediately recallable, nothing pending
    assert f.id in _ids(m.recall("warm widgets", k=10))
    assert m.backfill_pending_embeddings() == 0


def test_recall_robust_with_pending_rows_present(tmp_path):
    m = SemanticMemory(db_path=tmp_path / "s.db")
    a = Fact(proposition="Synced fact has 12 apples.", topic="eng/a")
    b = Fact(proposition="Pending fact has 12 apples.", topic="eng/b")
    m.store(a)                  # sync
    m.store(b, embed="defer")   # pending (NULL embedding)
    got = _ids(m.recall("apples", k=10))  # must NOT crash
    assert a.id in got
    assert b.id not in got
