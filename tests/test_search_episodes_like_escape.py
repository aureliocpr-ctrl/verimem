"""search_episodes must escape LIKE wildcards (save/recall hunt #5, 2026-06-14).

Parity with the fact side (correctness-hunt #20): a query token containing '_' or
'%' must match literally, not as a SQL glob, so a degraded keyword recall doesn't
surface false positives that evict the genuinely-relevant episode.
"""
from __future__ import annotations

import sqlite3

from engram.memory import EpisodicMemory


def _insert(db, rows):
    """Insert minimal episode rows, filling any NOT-NULL-no-default column with a
    neutral value so the test doesn't depend on the full episode schema."""
    con = sqlite3.connect(db)
    cols = con.execute("PRAGMA table_info(episodes)").fetchall()  # cid,name,type,notnull,dflt,pk
    fixed = {"id": 0, "task_id": 0, "task_text": 1, "outcome": 2, "created_at": 3}
    special = {"skills_used": "[]"}  # JSON column → must be valid JSON, not ""
    for r in rows:
        vals = {}
        for _cid, name, ctype, notnull, dflt, _pk in cols:
            ct = (ctype or "").upper()
            if name in fixed:
                vals[name] = r[fixed[name]]
            elif name in special:
                vals[name] = special[name]
            elif notnull and dflt is None:
                if "BLOB" in ct:
                    vals[name] = b""
                elif any(t in ct for t in ("INT", "REAL", "NUM")):
                    vals[name] = 0
                else:
                    vals[name] = ""
        placeholders = ",".join("?" * len(vals))
        con.execute(
            f"INSERT INTO episodes ({','.join(vals)}) VALUES ({placeholders})",
            list(vals.values()),
        )
    con.commit()
    con.close()


def test_underscore_is_literal_not_glob(tmp_path):
    db = tmp_path / "ep.db"
    em = EpisodicMemory(db_path=db)  # creates the schema
    _insert(db, [
        ("a", "store_batch helper", "success", 1.0),
        ("b", "storeXbatch other", "success", 2.0),  # would glob-match 'store_batch'
    ])
    texts = [e.task_text for e in em.search_episodes("store_batch", limit=10)]
    assert "store_batch helper" in texts
    assert "storeXbatch other" not in texts, "'_' must be literal, not any-char glob"


def test_percent_is_literal_not_glob(tmp_path):
    db = tmp_path / "ep.db"
    em = EpisodicMemory(db_path=db)
    _insert(db, [
        ("a", "100% done milestone", "success", 1.0),
        ("b", "100 then anything done", "success", 2.0),  # would match '100%...done'
    ])
    texts = [e.task_text for e in em.search_episodes("100% done", limit=10)]
    assert "100% done milestone" in texts
    assert "100 then anything done" not in texts


def test_plain_substring_still_matches(tmp_path):
    db = tmp_path / "ep.db"
    em = EpisodicMemory(db_path=db)
    _insert(db, [("a", "refactor the recall path", "success", 1.0)])
    texts = [e.task_text for e in em.search_episodes("recall path", limit=10)]
    assert texts == ["refactor the recall path"]
