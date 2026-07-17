"""Cycle #81 — supersede_chain batch helper (TDD strict RED).

Use case: declare a multi-hop refinement `A→B→C→D` in one call
instead of 3 single supersede calls. Atomicity: all-or-nothing
when ``atomic=True`` (default) — any conflict mid-chain rolls back
the previously-applied hops. When ``atomic=False`` it applies what
it can, returning per-hop status.

API:

  supersede_chain(ids: list[str], *, reason: str = "",
                  atomic: bool = True) -> dict
    -> {
         ok: bool,
         n_applied: int,       # hops actually written this call
         n_idempotent: int,    # hops that were already in place (noop)
         n_skipped: int,       # only > 0 when atomic=False on error
         chain: list[str],     # echo of input ids
         hops: list[dict],     # per-hop {old, new, status, reason?}
         error: str | None,    # set on rollback or atomic abort
       }

Status values per hop: ``applied``, ``idempotent``, ``conflict``,
``invalid``, ``rolled_back``.
"""
from __future__ import annotations

import pytest

from verimem.semantic import Fact, SemanticMemory, SupersedeConflict


@pytest.fixture
def mem(tmp_path):
    return SemanticMemory(db_path=tmp_path / "semantic.db")


@pytest.fixture
def four_facts(mem):
    for fid in ("a", "b", "c", "d"):
        mem.store(Fact(id=fid, proposition=f"v {fid}", topic="x",
                       confidence=0.9))
    return mem


# ---------------------------------------------------------------------------
# Basic batch
# ---------------------------------------------------------------------------

class TestBatchChain:
    def test_simple_three_hop_chain(self, four_facts):
        r = four_facts.supersede_chain(
            ["a", "b", "c", "d"], reason="refine x4",
        )
        assert r["ok"] is True
        assert r["n_applied"] == 3
        assert r["n_idempotent"] == 0
        assert r["n_skipped"] == 0
        # Forward walk from 'a' must reach 'd'
        chain = four_facts.get_supersession_chain("a")
        assert [f.id for f in chain] == ["a", "b", "c", "d"]

    def test_two_id_chain_single_hop(self, four_facts):
        r = four_facts.supersede_chain(["a", "b"], reason="X")
        assert r["n_applied"] == 1
        chain = four_facts.get_supersession_chain("a")
        assert [f.id for f in chain] == ["a", "b"]


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

class TestIdempotency:
    def test_replay_same_chain_is_noop(self, four_facts):
        four_facts.supersede_chain(["a", "b", "c"], reason="first")
        r = four_facts.supersede_chain(["a", "b", "c"], reason="first")
        assert r["ok"] is True
        assert r["n_applied"] == 0
        assert r["n_idempotent"] == 2

    def test_partial_replay_continues_chain(self, four_facts):
        # Apply a→b first, then full a→b→c via chain
        four_facts.supersede("a", "b", reason="manual")
        r = four_facts.supersede_chain(["a", "b", "c"], reason="full")
        # a→b is idempotent (same reason "manual" != "full" updates reason),
        # b→c is new
        assert r["n_applied"] == 1
        chain = four_facts.get_supersession_chain("a")
        assert [f.id for f in chain] == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation:
    def test_chain_too_short_raises(self, four_facts):
        from verimem.semantic import SupersedeError
        with pytest.raises(SupersedeError, match="at least 2"):
            four_facts.supersede_chain(["a"], reason="X")

    def test_chain_with_unknown_id_atomic_rollback(self, four_facts):
        # a→b OK, b→nonexistent FAIL → should roll back a→b
        r = four_facts.supersede_chain(
            ["a", "b", "nonexistent"], reason="X", atomic=True,
        )
        assert r["ok"] is False
        assert r["error"]
        # a's supersession marker must NOT be set
        a_after = four_facts.get("a")
        assert a_after.superseded_by is None

    def test_chain_with_unknown_id_non_atomic_partial(self, four_facts):
        r = four_facts.supersede_chain(
            ["a", "b", "nonexistent"], reason="X", atomic=False,
        )
        # a→b applied; second hop skipped
        assert r["ok"] is False
        assert r["n_applied"] == 1
        assert r["n_skipped"] == 1
        a_after = four_facts.get("a")
        assert a_after.superseded_by == "b"  # partial state preserved

    def test_self_loop_in_chain_rejected(self, four_facts):
        from verimem.semantic import SupersedeError
        with pytest.raises(SupersedeError):
            four_facts.supersede_chain(["a", "b", "b"], reason="X")


# ---------------------------------------------------------------------------
# Conflict handling
# ---------------------------------------------------------------------------

class TestConflict:
    def test_conflict_mid_chain_atomic_rollback(self, four_facts):
        # a→b first
        four_facts.supersede("a", "b", reason="initial")
        # Try a→c→d: a→c conflicts (a already superseded by b ≠ c)
        r = four_facts.supersede_chain(
            ["a", "c", "d"], reason="reassign", atomic=True,
        )
        assert r["ok"] is False
        assert "conflict" in (r["error"] or "").lower()
        # State should be exactly as before — a→b
        a_after = four_facts.get("a")
        assert a_after.superseded_by == "b"
        # c→d must NOT have been applied either (atomic)
        c_after = four_facts.get("c")
        assert c_after.superseded_by is None

    def test_rollback_preserves_pre_existing_reason(self, four_facts):
        """Critic cycle #81 counterexample (job cc004125dbaff256, conf 0.85).

        Pre-existing pointer a→b with reason 'r0'. Calling
        supersede_chain(['a','b','nonexistent'], reason='r1', atomic=True)
        will:
          1. Hop a→b: same pointer, different reason → supersede()
             UPDATEs superseded_reason='r1', returns idempotent_noop=False.
          2. Hop b→nonexistent: invalid → atomic rollback.

        Expected post-rollback: a.superseded_reason == 'r0' (pre-existing
        preserved). Pre-fix bug: stayed 'r1' because rollback list missed
        reason-update hops.
        """
        four_facts.supersede("a", "b", reason="r0")
        r = four_facts.supersede_chain(
            ["a", "b", "nonexistent"], reason="r1", atomic=True,
        )
        assert r["ok"] is False
        a_after = four_facts.get("a")
        assert a_after.superseded_by == "b"  # pointer preserved
        assert a_after.superseded_reason == "r0", (
            f"reason should be preserved as 'r0', got "
            f"{a_after.superseded_reason!r}"
        )
