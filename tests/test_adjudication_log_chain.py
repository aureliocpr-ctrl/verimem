"""Tamper-evidence hash-chain over the adjudication log (task #24, anchor-A wiring).

Each row chains to the previous by hash, so an in-place edit / delete / reorder of a
past row is detectable by ``verify()``. The EXTERNAL anchor — archiving ``head()``
off-box so the DB-writer cannot rewrite the whole chain and re-hash it — is the
operator's step (anchor-A); this layer provides the DETECTION and the head to archive.
"""
from __future__ import annotations

import sqlite3

from verimem.adjudication_log import AdjudicationLog


def _log(tmp_path):
    return AdjudicationLog(tmp_path / "adj.db")


def _rec(log, prop, disp="admitted"):
    return log.record(disposition=disp, topic="t", proposition=prop)


def test_intact_chain_verifies(tmp_path):
    log = _log(tmp_path)
    _rec(log, "a"); _rec(log, "b"); _rec(log, "c")
    assert log.verify() is None                       # intact → None


def test_head_advances_and_is_64_hex(tmp_path):
    log = _log(tmp_path)
    assert log.head() is None                          # empty chain
    _rec(log, "a")
    h1 = log.head()
    _rec(log, "b")
    h2 = log.head()
    assert h1 and h2 and h1 != h2 and len(h2) == 64


def test_edit_of_a_past_row_is_detected(tmp_path):
    log = _log(tmp_path)
    _rec(log, "a"); _rec(log, "b"); _rec(log, "c")
    con = sqlite3.connect(log.db_path)
    con.execute("UPDATE adjudications SET disposition='rejected' WHERE proposition='a'")
    con.commit(); con.close()
    assert log.verify() is not None                    # tamper detected


def test_delete_of_a_row_is_detected(tmp_path):
    log = _log(tmp_path)
    _rec(log, "a"); _rec(log, "b"); _rec(log, "c")
    con = sqlite3.connect(log.db_path)
    con.execute("DELETE FROM adjudications WHERE proposition='b'")
    con.commit(); con.close()
    assert log.verify() is not None                    # broken link detected


def test_verify_returns_the_first_tampered_row_id(tmp_path):
    log = _log(tmp_path)
    _rec(log, "a")
    bad = _rec(log, "b")
    _rec(log, "c")
    con = sqlite3.connect(log.db_path)
    con.execute("UPDATE adjudications SET reason='forged' WHERE id=?", (bad,))
    con.commit(); con.close()
    assert log.verify() == bad                          # points at the edited row


def test_null_evasion_of_tail_row_is_detected(tmp_path):
    """FIX 1 (opus critic): NULLing a chained row's entry_hash to make verify() skip it
    (the tail row has no successor to catch a broken link) must be caught — a NULL AFTER
    the chain started is tampering, not 'intact'."""
    log = _log(tmp_path)
    _rec(log, "a"); _rec(log, "b"); tail = _rec(log, "c")
    con = sqlite3.connect(log.db_path)
    con.execute("UPDATE adjudications SET disposition='admitted', entry_hash=NULL "
                "WHERE id=?", (tail,))
    con.commit(); con.close()
    assert log.verify() == tail                         # not None


def test_int_ts_does_not_false_alarm(tmp_path):
    """FIX 2 (opus critic): an int epoch ts (allowed by the signature) must not poison
    the chain — SQLite REAL affinity would otherwise make verify() recompute a float and
    flag intact data as tampered forever."""
    log = _log(tmp_path)
    log.record(disposition="admitted", topic="t", proposition="x", ts=1721370000)
    log.record(disposition="admitted", topic="t", proposition="y", ts=1721370001)
    assert log.verify() is None                         # intact despite int ts


def test_memory_audit_verify_and_head(tmp_path, monkeypatch):
    """The public Memory surface: audit_verify() detects tampering, audit_head() gives
    the head to archive off-box."""
    monkeypatch.setenv("VERIMEM_AUDIT_LOG", "1")
    from verimem import Memory
    mem = Memory(path=tmp_path / "sem" / "sem.db")
    mem.add("the sky is blue", topic="t")
    mem.add("grass is green", topic="t")
    assert mem.audit_verify() is None                   # intact
    h = mem.audit_head()
    assert h and len(h) == 64
    con = sqlite3.connect(str(tmp_path / "sem" / "adjudications.db"))
    con.execute("UPDATE adjudications SET disposition='rejected' "
                "WHERE proposition='the sky is blue'")
    con.commit(); con.close()
    assert mem.audit_verify() is not None               # tamper detected


def test_memory_audit_verify_none_when_off(tmp_path, monkeypatch):
    monkeypatch.delenv("VERIMEM_AUDIT_LOG", raising=False)
    from verimem import Memory
    mem = Memory(path=tmp_path / "sem" / "sem.db")
    mem.add("x", topic="t")
    assert mem.audit_verify() is None                   # no chain → None, no db created
    assert mem.audit_head() is None
    assert not (tmp_path / "sem" / "adjudications.db").exists()
