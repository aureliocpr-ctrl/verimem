"""Backpressure on the review queue (P0 ciclo 2, punto 4).

The gate holds borderline writes "for review". Nobody counts them. A queue
nobody measures is a queue nobody drains, and "held for review" quietly
becomes "silently dropped" — the exact failure the anti-confab promise cannot
afford, because the fact was neither admitted nor honestly refused.

So the write path reports pressure: when the quarantined backlog exceeds a
threshold, the receipt says so, on the write that is ADDING to it. That is the
only moment the operator is actually looking.

DECLARED LIMIT: there is no persisted per-fact quarantine reason (client.py
says so in restore_fact), so the depth counts the whole quarantined backlog,
not the L4-review class alone. Measuring the real thing coarsely beats
measuring a precise thing that does not exist; a `quarantine_reason` column is
the complete fix and it is not this cycle.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory
from verimem.review_queue import depth, pressure, threshold

CLAIM = "The migration was completed and all tests pass."


def _layers(warnings) -> set[str]:
    return {(w or {}).get("layer", "") for w in (warnings or [])}


def _quarantine(m: Memory, n: int) -> None:
    for i in range(n):
        m.add(f"{CLAIM} Batch {i} shipped and verified.", topic="t")


# --- the measure ----------------------------------------------------------

def test_depth_counts_the_quarantined_backlog(tmp_path):
    m = Memory(path=tmp_path / "m.db")
    assert depth(m.semantic.db_path) == 0
    _quarantine(m, 3)
    assert depth(m.semantic.db_path) == 3


def test_depth_ignores_admitted_facts(tmp_path):
    m = Memory(path=tmp_path / "m.db")
    m.add("The office is on the second floor.", topic="t")
    assert depth(m.semantic.db_path) == 0


def test_depth_ignores_superseded_rows(tmp_path):
    """A superseded fact left the queue: it has been answered by a newer one."""
    import sqlite3

    m = Memory(path=tmp_path / "m.db")
    _quarantine(m, 2)
    with sqlite3.connect(m.semantic.db_path) as c:
        c.execute("UPDATE facts SET superseded_by = 'newer' WHERE id = "
                  "(SELECT id FROM facts WHERE status = 'quarantined' LIMIT 1)")
    assert depth(m.semantic.db_path) == 1


def test_unreadable_store_reports_no_pressure(tmp_path):
    """Never crash a write over a telemetry read, and never invent a number."""
    p = pressure(tmp_path / "nope.db")
    assert p["depth"] == 0 and p["over"] is False


def test_threshold_comes_from_the_env(monkeypatch):
    monkeypatch.setenv("ENGRAM_REVIEW_QUEUE_MAX", "7")
    assert threshold() == 7
    monkeypatch.setenv("ENGRAM_REVIEW_QUEUE_MAX", "junk")
    assert threshold() > 0, "a bad value must fall back, never disable the check"


def test_zero_threshold_disables_the_signal(monkeypatch, tmp_path):
    monkeypatch.setenv("ENGRAM_REVIEW_QUEUE_MAX", "0")
    m = Memory(path=tmp_path / "m.db")
    _quarantine(m, 2)
    assert pressure(m.semantic.db_path)["over"] is False


# --- on the receipt -------------------------------------------------------

def test_backpressure_lands_on_the_write_that_adds_to_the_queue(
        tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_REVIEW_QUEUE_MAX", "2")
    m = Memory(path=tmp_path / "m.db")
    _quarantine(m, 3)                       # queue is now over the threshold
    r = m.add(f"{CLAIM} Batch 99 shipped and verified.", topic="t")
    assert r["status"] == "quarantined"
    note = next(w for w in r["warnings"]
                if w.get("layer") == "REVIEW_BACKPRESSURE")
    assert "3" in note["reason"] or "4" in note["reason"]
    assert "ENGRAM_REVIEW_QUEUE_MAX" in note["advice"]


def test_no_backpressure_below_the_threshold(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_REVIEW_QUEUE_MAX", "100")
    m = Memory(path=tmp_path / "m.db")
    r = m.add(f"{CLAIM} Batch 1 shipped and verified.", topic="t")
    assert "REVIEW_BACKPRESSURE" not in _layers(r["warnings"])


def test_admitted_writes_are_never_annotated(tmp_path, monkeypatch):
    """Pressure is reported to whoever is adding to the queue. A clean write
    is not — it would be noise on a page that has nothing to do with it."""
    monkeypatch.setenv("ENGRAM_REVIEW_QUEUE_MAX", "1")
    m = Memory(path=tmp_path / "m.db")
    _quarantine(m, 3)
    r = m.add("The office is on the second floor.", topic="t")
    assert r["status"] != "quarantined"
    assert "REVIEW_BACKPRESSURE" not in _layers(r["warnings"])


def test_the_count_is_cached_not_run_per_write(tmp_path, monkeypatch):
    """A COUNT on every quarantining write is a tax that grows with the store.
    One read per window is enough to notice a backlog."""
    import verimem.review_queue as rq

    monkeypatch.setenv("ENGRAM_REVIEW_QUEUE_MAX", "1")
    calls = []
    real = rq._count

    def _spy(db_path):
        calls.append(db_path)
        return real(db_path)

    monkeypatch.setattr(rq, "_count", _spy)
    rq.reset_cache()
    m = Memory(path=tmp_path / "m.db")
    _quarantine(m, 3)
    assert len(calls) == 1, f"counted {len(calls)} times for 3 writes"


@pytest.mark.parametrize("value", ["-5", "abc", ""])
def test_bad_threshold_values_never_disable_the_check(value, monkeypatch):
    monkeypatch.setenv("ENGRAM_REVIEW_QUEUE_MAX", value)
    assert threshold() > 0
