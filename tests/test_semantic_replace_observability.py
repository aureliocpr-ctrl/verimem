"""Cycle #46 — observability for INSERT OR REPLACE on SemanticMemory.

Critic-found 2026-05-14 (cycle #45, job 134acf1446994a76): SemanticMemory.store
uses `INSERT OR REPLACE INTO facts` on `id PRIMARY KEY`. When a caller passes
a Fact whose id already exists, the old row is silently overwritten. No
exception, no log, no metric — only the new row remains.

Bench `facts_collision` mode confirmed empirically: 20 procs × 100 writes
on shared id space → 100/2000 rows in DB, 95% silent overwrites, 0 errors.

Cycle #45 decision-trajectory 685d31c9d85b: KEEP idempotency (genuinely
needed by sleep dedup + hippo_remember idempotent re-call) but ADD
observability so the caller / audit can SEE when overwrites happen.

This cycle adds an opt-in `return_replaced=True` kwarg to
`SemanticMemory.store()`:
  - default: backwards-compatible (returns None as before)
  - opt-in: returns bool — True if a row with the same id existed
    BEFORE this write (i.e., the new write overwrote), False if it was
    a fresh insert.

The hippo_remember MCP handler uses the flag and emits a distinct audit
outcome (`ok_replaced` vs `ok_new`) so `hippo_audit_summary` (fixed in
cycle #43) reflects the actual rate of overwrites in production.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from engram.semantic import Fact, SemanticMemory


@pytest.fixture
def store(tmp_path):
    return SemanticMemory(db_path=tmp_path / "semantic.db")


# ---------------------------------------------------------------------------
# return_replaced contract — RED first
# ---------------------------------------------------------------------------


def test_store_returns_false_for_fresh_insert(store: SemanticMemory) -> None:
    """First write with a new id must report replaced=False."""
    fact = Fact(id="abc", proposition="hello", topic="t/a", confidence=0.9)
    replaced = store.store(fact, return_replaced=True)
    assert replaced is False


def test_store_returns_true_when_overwriting(store: SemanticMemory) -> None:
    """Second write with same id MUST report replaced=True."""
    f1 = Fact(id="abc", proposition="first", topic="t/a", confidence=0.9)
    f2 = Fact(id="abc", proposition="second", topic="t/a", confidence=0.9)
    r1 = store.store(f1, return_replaced=True)
    r2 = store.store(f2, return_replaced=True)
    assert r1 is False
    assert r2 is True


def test_store_default_returns_none(store: SemanticMemory) -> None:
    """Backwards compat: without return_replaced, store returns None
    (same behavior as before — no caller breakage)."""
    fact = Fact(id="abc", proposition="hello", topic="t/a", confidence=0.9)
    result = store.store(fact)  # no return_replaced kwarg
    assert result is None


def test_store_overwrites_propagate_to_count(store: SemanticMemory) -> None:
    """Replacing with same id MUST NOT increment row count."""
    f1 = Fact(id="abc", proposition="first", topic="t/a")
    f2 = Fact(id="abc", proposition="second", topic="t/a")
    f3 = Fact(id="xyz", proposition="third", topic="t/a")
    store.store(f1)
    store.store(f2)  # overwrites f1
    store.store(f3)  # new row
    assert store.count() == 2  # not 3 — f2 replaced f1


def test_store_overwrite_keeps_new_proposition(store: SemanticMemory) -> None:
    """The body after overwrite must be the NEW proposition (not stale)."""
    f1 = Fact(id="abc", proposition="OLD", topic="t/a")
    f2 = Fact(id="abc", proposition="NEW", topic="t/a")
    store.store(f1)
    store.store(f2)
    rows = store.all()
    assert len(rows) == 1
    assert rows[0].proposition == "NEW"


# ---------------------------------------------------------------------------
# Multi-write sequence — useful for audit aggregation
# ---------------------------------------------------------------------------


def test_replace_count_over_sequence(store: SemanticMemory) -> None:
    """Across a sequence of writes, count the True returns."""
    facts = [
        Fact(id="a", proposition="1"),
        Fact(id="b", proposition="2"),
        Fact(id="a", proposition="3"),  # overwrite
        Fact(id="c", proposition="4"),
        Fact(id="b", proposition="5"),  # overwrite
        Fact(id="a", proposition="6"),  # overwrite again
    ]
    flags = [store.store(f, return_replaced=True) for f in facts]
    assert flags == [False, False, True, False, True, True]
    # In DB: 3 unique ids (a, b, c)
    assert store.count() == 3
