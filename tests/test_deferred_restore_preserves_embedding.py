"""P0-3 (audit 2026-06-07): a deferred re-store must NOT clobber an existing
good embedding with a 0-byte blob.

Repro: store(embed='sync') -> good vector on disk; re-store SAME id with a
deferred embedding (emb=None, the production embed='auto' path when the encode
daemon is cold) -> the UPSERT used to overwrite embedding with b'' and
embedding_model with '', dropping the fact from semantic recall with no error.
Fix: the DO UPDATE SET preserves the existing embedding when the new one is empty.

Hermetic: tmp DB. embed='defer' triggers emb=None directly (no daemon mocking).
"""
from __future__ import annotations

import sqlite3

from verimem.semantic import Fact, SemanticMemory


def _emb_len(db, fact_id):
    c = sqlite3.connect(db)
    try:
        row = c.execute("SELECT length(embedding) FROM facts WHERE id = ?", (fact_id,)).fetchone()
        return row[0] if row else None
    finally:
        c.close()


def test_deferred_restore_preserves_existing_embedding(tmp_path):
    db = tmp_path / "s.db"
    sm = SemanticMemory(db_path=db)
    f = Fact(proposition="the deploy script lives in scripts/deploy.sh", topic="proj/x")

    sm.store(f, embed="sync")          # real vector persisted
    good = _emb_len(db, f.id)
    assert good and good > 0, f"setup: sync store should embed (got {good})"

    # Re-store the SAME fact with a DEFERRED embedding (emb=None) — e.g. updating
    # confidence/topic, a retry, or hippo_remember(embed='auto') under a cold daemon.
    sm.store(f, embed="defer")
    after = _emb_len(db, f.id)
    assert after and after > 0, (
        f"deferred re-store ZEROED the embedding ({after}) -> fact dropped from "
        f"recall (P0-3 recall-loss)"
    )
    assert after == good, "embedding changed on a content-identical deferred re-store"


def test_fresh_deferred_store_still_allows_empty(tmp_path):
    # A FIRST store with deferred embedding may legitimately be empty (backfilled
    # later); the preserve-on-conflict fix must not break the fresh-insert path.
    db = tmp_path / "s.db"
    sm = SemanticMemory(db_path=db)
    f = Fact(proposition="a brand new deferred fact with no prior vector", topic="proj/y")
    sm.store(f, embed="defer")
    # fresh deferred insert: 0-byte embedding is acceptable (will be backfilled)
    assert _emb_len(db, f.id) == 0
