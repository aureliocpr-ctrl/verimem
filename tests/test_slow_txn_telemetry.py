"""Transaction-duration telemetry on the core DB connections.

Concurrency finding 2026-06-10: deferred saves and `clp save` died on
"database is locked" because SOME process held the write lock longer than
every client's busy timeout — but nothing in the system says WHO. The
dream was exonerated (works on a shadow copy); the embedding daemon is
the suspect. Step 1 of the plan item is measurement: every long-held
`_connect()` context on the semantic/episodic DBs must leave a log line
with the duration and the db file, so one day of logs names the culprit.

Contract (RED pre-fix):
  - a `_connect()` context held longer than ENGRAM_SLOW_TXN_WARN_S
    (default 2.0s) logs a WARNING naming the db path and the elapsed s;
  - fast transactions stay silent;
  - the threshold is env-tunable per process.
"""
from __future__ import annotations

import logging
import time

from verimem.memory import EpisodicMemory
from verimem.semantic import SemanticMemory


def _hold_connection(store, seconds: float) -> None:
    with store._connect() as conn:
        conn.execute("SELECT 1").fetchone()
        time.sleep(seconds)


def test_semantic_slow_txn_logs_warning(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("ENGRAM_SLOW_TXN_WARN_S", "0.05")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    with caplog.at_level(logging.WARNING, logger="verimem.semantic"):
        _hold_connection(sm, 0.12)
    hits = [r for r in caplog.records if "slow sqlite txn" in r.getMessage()]
    assert hits, "a >threshold connection hold must log 'slow sqlite txn'"
    msg = hits[0].getMessage()
    assert "s.db" in msg, "warning must name the db file"


def test_semantic_fast_txn_is_silent(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("ENGRAM_SLOW_TXN_WARN_S", "5")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    with caplog.at_level(logging.WARNING, logger="verimem.semantic"):
        _hold_connection(sm, 0.0)
    assert not [r for r in caplog.records
                if "slow sqlite txn" in r.getMessage()], (
        "fast transactions must not spam the log"
    )


def test_episodic_slow_txn_logs_warning(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("ENGRAM_SLOW_TXN_WARN_S", "0.05")
    em = EpisodicMemory(db_path=tmp_path / "e.db")
    with caplog.at_level(logging.WARNING, logger="verimem.memory"):
        _hold_connection(em, 0.12)
    hits = [r for r in caplog.records if "slow sqlite txn" in r.getMessage()]
    assert hits, "episodic _connect must carry the same telemetry"
    assert "e.db" in hits[0].getMessage()


def test_threshold_garbage_falls_back_to_default(monkeypatch):
    from verimem import semantic as semantic_mod
    monkeypatch.setenv("ENGRAM_SLOW_TXN_WARN_S", "garbage")
    assert semantic_mod._slow_txn_warn_s() == 2.0
