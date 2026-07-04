"""BM25/FTS5 lexical ranking (competitor-gap step 3a, 2026-06-14).

Fixes exact-token recall (commit SHA / file path / API name the bi-encoder smears):
BM25 ranks the rare token first where pure-cosine does not. Leaf, fail-soft, the
FTS index stays synced to the curated facts.
"""
from __future__ import annotations

from engram.bm25_rank import bm25_fact_ids
from engram.semantic import Fact, SemanticMemory


def test_bm25_ranks_exact_rare_token_first(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    target = Fact(proposition="recall hang fixed in commit deadbeef1234 on main branch",
                  topic="t/x")
    sm.store(target, embed="auto")
    for i in range(4):
        sm.store(Fact(proposition=f"unrelated planning note number {i} about budgets",
                      topic="t/d"), embed="auto")
    ids = bm25_fact_ids("deadbeef1234", str(sm.db_path))
    assert ids and ids[0] == target.id, "the exact rare token must rank first under BM25"


def test_bm25_failsoft_paths(tmp_path):
    assert bm25_fact_ids("", str(tmp_path / "x.db")) == []          # empty query
    assert bm25_fact_ids(None, str(tmp_path / "x.db")) == []        # None query
    # a db with no facts table → fail-soft [], no crash
    assert bm25_fact_ids("anything", str(tmp_path / "missing.db")) == []


def test_bm25_resyncs_on_new_fact(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    sm.store(Fact(proposition="alpha baseline note", topic="t"), embed="auto")
    bm25_fact_ids("alpha", str(sm.db_path))  # builds + populates the FTS index
    new = Fact(proposition="gamma carrying a uniquetokenxyz marker", topic="t")
    sm.store(new, embed="auto")
    ids = bm25_fact_ids("uniquetokenxyz", str(sm.db_path))  # trigger-synced -> finds it
    assert new.id in ids, "a newly stored fact must be (re)indexed and found"


def test_bm25_curated_filter_excludes_quarantined(tmp_path):
    """The FTS index mirrors every row (via triggers), but the query-time JOIN
    applies the curated filter — a quarantined fact must NOT be returned."""
    import sqlite3

    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    f = Fact(proposition="secret marker tokenq8x7 in a note", topic="t")
    sm.store(f, embed="auto")
    assert f.id in bm25_fact_ids("tokenq8x7", str(sm.db_path))  # visible while curated

    con = sqlite3.connect(sm.db_path)
    con.execute("UPDATE facts SET status='quarantined' WHERE id=?", (f.id,))
    con.commit()
    con.close()
    assert f.id not in bm25_fact_ids("tokenq8x7", str(sm.db_path)), (
        "a quarantined fact must be excluded by the query-time curated filter"
    )
