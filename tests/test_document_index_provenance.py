"""Chunk provenance (P0 ciclo 2, punto 3) — the indexer's identity survives.

Ciclo 1 gave `DocumentStore.ingest` a `principal` so a snapshot records WHO
vouched for it. But `DocumentIndex` — the tier the MCP tool
`hippo_document_index_file` actually calls, named in the P0 design as the real
poison-then-cite vector — never passed one. So every document that entered
through the indexer landed unsigned, and the independence rule could never
speak about it: the stamp existed and the only path that mattered skipped it.

A chunk is what a search returns and what a promotion turns into a fact, so it
carries the identity too. Otherwise the provenance is one join away at the
exact moment a citation is being made.

Absence stays absence: an unsigned ingest records nothing, never a default
that could read as a vouch nobody made.
"""
from __future__ import annotations

import numpy as np
import pytest

from verimem.document_index import DocumentIndex

TEXT = "The API returns 429 on rate limit. Retries use exponential backoff."


class _E:
    """Deterministic stand-in embedder: no model, stable vectors."""

    def encode(self, texts):
        return np.asarray(
            [[float(len(t) % 7), float(sum(map(ord, t[:16])) % 11), 1.0]
             for t in texts], dtype=np.float32)


@pytest.fixture()
def ix(tmp_path):
    return DocumentIndex(db_path=tmp_path / "ix.db", embedder=_E(),
                         document_store=None)


def test_index_document_stamps_the_snapshot(ix):
    ix.index_document("spec-1", TEXT, principal="mcp:unbound")
    doc = ix.docs.get_latest("spec-1")
    assert doc.meta["indexed_by"] == "mcp:unbound"


def test_index_file_stamps_the_snapshot(ix, tmp_path):
    p = tmp_path / "spec.txt"
    p.write_text(TEXT, encoding="utf-8")
    ix.index_file(p, source_id="spec-2", principal="gw:team-alpha")
    assert ix.docs.get_latest("spec-2").meta["indexed_by"] == "gw:team-alpha"


def test_unsigned_index_records_nothing(ix):
    ix.index_document("spec-3", TEXT)
    assert "indexed_by" not in ix.docs.get_latest("spec-3").meta


def test_chunks_carry_the_indexer_identity(ix):
    ix.index_document("spec-4", TEXT, principal="cli:local")
    hits = ix.search("rate limit", k=3)
    assert hits and all(h["indexed_by"] == "cli:local" for h in hits)


def test_chunks_of_an_unsigned_document_report_none(ix):
    ix.index_document("spec-5", TEXT)
    hits = ix.search("rate limit", k=3)
    assert hits and all(h["indexed_by"] is None for h in hits)


def test_pre_provenance_index_migrates(tmp_path):
    """An index built before the column exists gains it; its old chunks read
    back as unsigned rather than exploding."""
    import sqlite3

    db = tmp_path / "old.db"
    with sqlite3.connect(db) as c:
        c.execute("""CREATE TABLE chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id TEXT NOT NULL,
            source_id TEXT NOT NULL, version INTEGER NOT NULL,
            idx INTEGER NOT NULL, start INTEGER NOT NULL, end INTEGER NOT NULL,
            text TEXT NOT NULL, uri TEXT, vec BLOB NOT NULL,
            flagged INTEGER NOT NULL DEFAULT 0)""")
    ix = DocumentIndex(db_path=db, embedder=_E())
    with sqlite3.connect(db) as c:
        cols = {r[1] for r in c.execute("PRAGMA table_info(chunks)")}
    assert "indexed_by" in cols
    ix.index_document("spec-6", TEXT, principal="sdk:local")
    assert ix.search("rate limit", k=1)[0]["indexed_by"] == "sdk:local"
