"""recall(include_orphaned=True) must surface hidden rows even on the cold-encode
keyword fallback (save/recall hunt #3, 2026-06-14).

When the query-encode times out, recall delegates to search_facts, which used to
UNCONDITIONALLY hide orphaned/quarantined rows — so an audit/undo caller asking to
see hidden rows got ZERO when the embedding daemon was cold, diverging from the warm
path. Fix: search_facts gains include_orphaned; the cold fallback forwards it.
"""
from __future__ import annotations

import sqlite3

import verimem.semantic as S
from verimem.semantic import Fact, SemanticMemory


def _ids(res):
    return {(x[0] if isinstance(x, tuple) else x).id for x in res}


def _quarantine(db, fid):
    con = sqlite3.connect(db)
    con.execute("UPDATE facts SET status='quarantined' WHERE id=?", (fid,))
    con.commit()
    con.close()


def test_search_facts_include_orphaned_surfaces_hidden(tmp_path):
    db = tmp_path / "semantic" / "semantic.db"
    db.parent.mkdir(parents=True)
    sm = SemanticMemory(db_path=db)
    f_ok = Fact(proposition="visible audit target alpha", topic="t/a")
    f_q = Fact(proposition="hidden audit target alpha", topic="t/a")
    sm.store(f_ok, embed="sync")
    sm.store(f_q, embed="sync")
    _quarantine(db, f_q.id)

    default = {f.id for f in sm.search_facts("audit target alpha")}
    assert f_ok.id in default and f_q.id not in default, "default hides quarantined"
    opened = {f.id for f in sm.search_facts("audit target alpha", include_orphaned=True)}
    assert f_q.id in opened, "include_orphaned must surface quarantined rows"


def test_recall_cold_fallback_honours_include_orphaned(tmp_path, monkeypatch):
    # Force the cold-encode fallback: query-encode returns None.
    monkeypatch.setattr(S, "_encode_prepared_within_budget", lambda *a, **k: None)
    db = tmp_path / "semantic" / "semantic.db"
    db.parent.mkdir(parents=True)
    sm = SemanticMemory(db_path=db)
    f_q = Fact(proposition="hidden cold recall target beta", topic="t/b")
    sm.store(f_q, embed="sync")
    _quarantine(db, f_q.id)

    cold_default = sm.recall("hidden cold recall target beta", k=5)
    assert f_q.id not in _ids(cold_default), "cold path still hides by default"
    cold_open = sm.recall("hidden cold recall target beta", k=5, include_orphaned=True)
    assert f_q.id in _ids(cold_open), (
        "cold-encode fallback must surface orphaned/quarantined under include_orphaned"
    )
