"""Audit 3-round R1 #1 (CRITICAL): the skill-emergence detector hardcodes the
384-dim embedding shape, so it is silently dead on the 768-dim production default.

_embeddings_for_ids filtered `length(embedding) = 1536` (=384*4) and reshaped to
(-1, 384). The shipped default is 768-dim (3072-byte blobs), so EVERY row is
filtered out -> the SELECT returns nothing -> _embeddings_for_ids returns None ->
the whole emergent-skill discovery pipeline yields zero candidates without error.
Fix: derive the byte length from expected_embedding_bytes() (CONFIG.embedding_dim
* 4, the single source) and reshape dim-agnostically (len(ids), -1).
"""
from __future__ import annotations

import sqlite3

import numpy as np

from engram import skill_emergence_detector as sed


def _make_facts_db(path, dim: int, ids: list[str]):
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE facts (id TEXT PRIMARY KEY, embedding BLOB)")
    for fid in ids:
        blob = np.ones(dim, dtype=np.float32).tobytes()  # dim*4 bytes
        conn.execute("INSERT INTO facts VALUES (?, ?)", (fid, blob))
    conn.commit()
    conn.close()


def test_embeddings_for_ids_works_at_768_default_dim(tmp_path, monkeypatch):
    # configured dim = 768 (production default): expected byte-length 3072.
    monkeypatch.setattr(sed, "expected_embedding_bytes", lambda: 768 * 4,
                        raising=False)
    db = tmp_path / "s.db"
    _make_facts_db(db, 768, ["f1", "f2"])
    arr = sed._embeddings_for_ids(db, ["f1", "f2"])
    assert arr is not None, "768-dim rows must be fetched, not filtered out"
    assert arr.shape == (2, 768), arr.shape


def test_embeddings_for_ids_still_works_at_384_dim(tmp_path, monkeypatch):
    monkeypatch.setattr(sed, "expected_embedding_bytes", lambda: 384 * 4,
                        raising=False)
    db = tmp_path / "s.db"
    _make_facts_db(db, 384, ["f1"])
    arr = sed._embeddings_for_ids(db, ["f1"])
    assert arr is not None and arr.shape == (1, 384), arr
