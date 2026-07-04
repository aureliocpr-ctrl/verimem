"""Cycle #78 — fact_supersede tests (TDD strict RED before any implementation).

P3 from cycle 2026-05-16 stress-test (fact 17eeb807d2d6):
fact obsoleti rimangono in memoria con confidence alta. Mancano:
  - API per dichiarare "old fact superseded by new fact"
  - Filter automatico in recall/search/list (no double-recall of stale truth)
  - Walk forward chain (A→B→C)

Design decisions documented before tests:

(1) **No down-confidence on supersede.** The historical fact stays
    truthful at the time it was written. Supersession says "for the
    current state, use the new fact." Recovering the historical fact
    is still useful for lineage/audit/post-mortem.

(2) **Chains allowed.** A→B→C is valid (e.g. iterative refinement of
    a measurement over multiple cycles). `get_supersession_chain` walks
    forward until None.

(3) **Idempotent.** Same (old, new, reason) twice = no-op. Different
    reason on second call = silently updates the reason (last writer
    wins for the reason field — no merge semantics).

(4) **Conflict detection.** A already superseded by B; new call says
    "A superseded by C" (C != B) → raise SupersedeConflict with both
    new_ids in the message. Caller decides chain (A→B→C if B→C is also
    declared) vs explicit reassignment.

(5) **Self-supersede rejected.** old_id == new_id → SupersedeError.

(6) **Default exclude in retrieval.** `recall`, `list_facts`,
    `search_facts` get optional `include_superseded=False` (default).
    Counts (`count`) get a separate `count_superseded()` accessor.

(7) **Backwards compatible storage.** Schema v1 → v2 adds 3 nullable
    columns; existing fact rows have NULL superseded_by, behave as
    "live" (the default filter is `WHERE superseded_by IS NULL`).
"""
from __future__ import annotations

import pytest

from engram.semantic import Fact, SemanticMemory

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mem(tmp_path):
    return SemanticMemory(db_path=tmp_path / "semantic.db")


@pytest.fixture
def fact_pair(mem):
    """Two facts: 'old' (will be superseded) and 'new' (the replacement)."""
    old = Fact(
        id="old_aaa111",
        proposition="NEXUS has 25 phases (from docstring count 9-33)",
        topic="project/nexus/L2-DEEP-1",
        confidence=0.98,
    )
    new = Fact(
        id="new_bbb222",
        proposition="NEXUS has 60+ phases (from code invocation count incl. 7.94-7.131)",
        topic="project/nexus/L2-DEEP-1",
        confidence=1.0,
    )
    mem.store(old)
    mem.store(new)
    return old, new


# ---------------------------------------------------------------------------
# Basic supersede
# ---------------------------------------------------------------------------

class TestSupersedeBasic:
    def test_supersede_marks_old_with_new_id_and_ts(self, mem, fact_pair):
        old, new = fact_pair
        result = mem.supersede(old.id, new.id, reason="docstring vs code count")

        assert result["ok"] is True
        assert result["old_id"] == old.id
        assert result["new_id"] == new.id
        assert result["reason"] == "docstring vs code count"
        assert result["superseded_at"] > 0  # epoch

        # Old fact is still retrievable by get() with the marker fields populated
        old_after = mem.get(old.id)
        assert old_after is not None
        assert old_after.superseded_by == new.id
        assert old_after.superseded_at >= result["superseded_at"] - 0.01
        assert old_after.superseded_reason == "docstring vs code count"

        # New fact is untouched
        new_after = mem.get(new.id)
        assert new_after is not None
        assert new_after.superseded_by is None

    def test_old_confidence_preserved(self, mem, fact_pair):
        """Design decision (1): supersede does NOT down-confidence the old fact.
        Historical truth at write-time stays truthful for lineage/audit."""
        old, new = fact_pair
        mem.supersede(old.id, new.id, reason="X")
        old_after = mem.get(old.id)
        assert old_after.confidence == 0.98  # unchanged from fixture


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestSupersedeValidation:
    def test_self_supersede_rejected(self, mem, fact_pair):
        from engram.semantic import SupersedeError
        old, _new = fact_pair
        with pytest.raises(SupersedeError, match="self"):
            mem.supersede(old.id, old.id, reason="oops")

    def test_unknown_old_id_rejected(self, mem, fact_pair):
        from engram.semantic import SupersedeError
        _old, new = fact_pair
        with pytest.raises(SupersedeError, match="old_id"):
            mem.supersede("nonexistent_xxx", new.id, reason="X")

    def test_unknown_new_id_rejected(self, mem, fact_pair):
        from engram.semantic import SupersedeError
        old, _new = fact_pair
        with pytest.raises(SupersedeError, match="new_id"):
            mem.supersede(old.id, "nonexistent_yyy", reason="X")


# ---------------------------------------------------------------------------
# Idempotency + conflict
# ---------------------------------------------------------------------------

class TestSupersedeIdempotency:
    def test_same_pair_twice_is_noop(self, mem, fact_pair):
        old, new = fact_pair
        r1 = mem.supersede(old.id, new.id, reason="first")
        first_ts = r1["superseded_at"]
        r2 = mem.supersede(old.id, new.id, reason="first")
        # Idempotent: timestamp NOT bumped on no-op same-reason re-call
        assert r2["ok"] is True
        assert r2["idempotent_noop"] is True
        old_after = mem.get(old.id)
        assert old_after.superseded_at == first_ts

    def test_same_pair_different_reason_updates_reason(self, mem, fact_pair):
        old, new = fact_pair
        mem.supersede(old.id, new.id, reason="initial")
        mem.supersede(old.id, new.id, reason="refined: docstring is stale, code is truth")
        old_after = mem.get(old.id)
        assert "refined" in old_after.superseded_reason

    def test_conflict_different_new_id_raises(self, mem, fact_pair):
        from engram.semantic import SupersedeConflict
        old, new = fact_pair
        third = Fact(id="third_ccc", proposition="alt", topic="x", confidence=0.9)
        mem.store(third)
        mem.supersede(old.id, new.id, reason="first")
        with pytest.raises(SupersedeConflict, match=new.id):
            mem.supersede(old.id, third.id, reason="reassign")


# ---------------------------------------------------------------------------
# Chain (A→B→C)
# ---------------------------------------------------------------------------

class TestSupersedeChain:
    def test_chain_a_to_b_to_c_walks_forward(self, mem):
        a = Fact(id="a_id", proposition="v1: 144 detector", topic="x", confidence=0.9)
        b = Fact(id="b_id", proposition="v2: 460 detector", topic="x", confidence=0.95)
        c = Fact(id="c_id", proposition="v3: 543 detector verified", topic="x", confidence=1.0)
        for f in (a, b, c):
            mem.store(f)
        mem.supersede(a.id, b.id, reason="grew to 460")
        mem.supersede(b.id, c.id, reason="verified count 543 via ls|wc")

        chain = mem.get_supersession_chain(a.id)
        # Returns [a, b, c] (or [a.id, b.id, c.id]) — full forward walk.
        ids = [link if isinstance(link, str) else link.id for link in chain]
        assert ids == [a.id, b.id, c.id]

    def test_chain_terminal_fact_returns_singleton(self, mem, fact_pair):
        _old, new = fact_pair
        chain = mem.get_supersession_chain(new.id)
        ids = [link if isinstance(link, str) else link.id for link in chain]
        assert ids == [new.id]


# ---------------------------------------------------------------------------
# Retrieval filtering
# ---------------------------------------------------------------------------

class TestRecallExcludesSuperseded:
    def test_recall_default_excludes_superseded(self, mem, fact_pair):
        old, new = fact_pair
        mem.supersede(old.id, new.id, reason="X")
        hits = mem.recall("NEXUS phases", k=5)
        ids = {f.id for f, _ in hits}
        assert old.id not in ids
        assert new.id in ids

    def test_recall_include_superseded_opt_in_returns_both(self, mem, fact_pair):
        old, new = fact_pair
        mem.supersede(old.id, new.id, reason="X")
        hits = mem.recall("NEXUS phases", k=5, include_superseded=True)
        ids = {f.id for f, _ in hits}
        assert old.id in ids
        assert new.id in ids

    def test_list_facts_default_excludes_superseded(self, mem, fact_pair):
        old, new = fact_pair
        mem.supersede(old.id, new.id, reason="X")
        live = mem.list_facts()
        ids = {f.id for f in live}
        assert old.id not in ids
        assert new.id in ids

    def test_search_facts_default_excludes_superseded(self, mem, fact_pair):
        old, new = fact_pair
        mem.supersede(old.id, new.id, reason="X")
        hits = mem.search_facts("phases")
        ids = {f.id for f in hits}
        assert old.id not in ids
        assert new.id in ids

    def test_get_returns_superseded_anyway(self, mem, fact_pair):
        """get() is for explicit by-id lookup (audit/lineage) — never filters."""
        old, new = fact_pair
        mem.supersede(old.id, new.id, reason="X")
        assert mem.get(old.id) is not None


# ---------------------------------------------------------------------------
# Counts
# ---------------------------------------------------------------------------

class TestCounts:
    def test_count_default_excludes_superseded(self, mem, fact_pair):
        old, new = fact_pair
        assert mem.count() == 2
        mem.supersede(old.id, new.id, reason="X")
        assert mem.count() == 1  # only "new" is live

    def test_count_with_superseded_returns_all(self, mem, fact_pair):
        old, new = fact_pair
        mem.supersede(old.id, new.id, reason="X")
        assert mem.count(include_superseded=True) == 2

    def test_count_superseded_only(self, mem, fact_pair):
        old, new = fact_pair
        mem.supersede(old.id, new.id, reason="X")
        assert mem.count_superseded() == 1
