"""Retention/prune del Tier C (TranscriptIndex.prune) — crescita bounded.

Invarianti:
  - prune(max_turns=K) tiene i K turni piu' recenti (ts desc) e cancella il resto.
  - prune(before_ts=T) cancella i turni con ts < T.
  - prune ritorna il numero di righe cancellate.
  - prune(session_id=S) e' SCOPED: non tocca le altre sessioni.

Hermetic: DB temporaneo.
"""
from __future__ import annotations

from verimem.transcript_index import TranscriptIndex, Turn


def _seed(db, n, session="S", base_ts=0.0):
    idx = TranscriptIndex(db_path=db)
    for i in range(n):
        idx.store(Turn(text=f"turno numero {i} con testo sufficiente lungo",
                       session_id=session, ts=base_ts + i, id=f"{session}-{i}"))
    return idx


def test_prune_max_turns_keeps_newest(tmp_path):
    db = tmp_path / "t.db"
    idx = _seed(db, 5)  # ts 0..4
    deleted = idx.prune(max_turns=2)
    assert deleted == 3
    assert idx.count() == 2
    kept = {t.id for t, _ in idx.recall("turno", k=10)}
    assert kept == {"S-3", "S-4"}, "devono restare i 2 piu' recenti"


def test_prune_before_ts(tmp_path):
    db = tmp_path / "t.db"
    idx = _seed(db, 5)  # ts 0..4
    deleted = idx.prune(before_ts=3.0)
    assert deleted == 3  # ts 0,1,2
    assert idx.count() == 2  # ts 3,4


def test_prune_scoped_by_session_does_not_touch_others(tmp_path):
    db = tmp_path / "t.db"
    idx = _seed(db, 3, session="A", base_ts=0.0)
    _seed(db, 3, session="B", base_ts=100.0)  # stessa db
    deleted = idx.prune(max_turns=1, session_id="A")
    assert deleted == 2
    assert idx.count(session_id="A") == 1
    assert idx.count(session_id="B") == 3, "B non deve essere toccata"


def test_prune_noop_when_under_cap(tmp_path):
    db = tmp_path / "t.db"
    idx = _seed(db, 2)
    assert idx.prune(max_turns=10) == 0
    assert idx.count() == 2
