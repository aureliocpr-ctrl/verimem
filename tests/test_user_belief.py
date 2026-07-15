"""user_belief epistemic class — the write-origin anti-sycophancy gate (Giro 2).

An unverified USER assertion of fact must not be laundered into a stored fact the
default recall serves back as truth. This locks the FOUNDATION increment: the status
exists, is valid, ranks below model_claim, and is HIDDEN from default recall exactly
like `quarantined` — but retrievable on an explicit opt-in. Extraction-time tagging,
guardian correction and MemSyco-Bench are separate later increments (see
docs/USER-BELIEF-DESIGN.md).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from engram.semantic import _STATUS_RANK, _VALID_STATUSES, Fact, SemanticMemory


def _mem() -> SemanticMemory:
    return SemanticMemory(db_path=Path(tempfile.mkdtemp()) / "s.db")


def test_user_belief_is_a_valid_status():
    assert "user_belief" in _VALID_STATUSES


def test_user_belief_ranks_below_model_claim():
    # weaker provenance than an ordinary model_claim, so a min_status floor and any
    # rank-ordering treat it as low-trust.
    assert _STATUS_RANK["user_belief"] < _STATUS_RANK["model_claim"]


def test_user_belief_is_hidden_from_default_recall():
    m = _mem()
    m.store(Fact(proposition="The vendor API is the fastest on the market",
                 topic="user/claim", status="user_belief"), embed="sync")
    m.store(Fact(proposition="The user prefers dark mode in the editor",
                 topic="user/pref", status="model_claim"), embed="sync")
    hits = m.recall("vendor API fastest market", k=5)
    statuses = [getattr(f, "status", "") for f, *_ in hits]
    assert "user_belief" not in statuses, (
        f"user_belief leaked into default recall: {statuses}")


def test_user_belief_is_stored_not_deleted():
    # hidden from default recall, but the row exists (rehabilitable on corroboration —
    # the include_beliefs retrieval path builds on this).
    m = _mem()
    m.store(Fact(proposition="The vendor API is the fastest on the market",
                 topic="user/claim", status="user_belief"), embed="sync")
    all_props = [f.proposition for f in m.list_facts(limit=100)]
    assert "The vendor API is the fastest on the market" in all_props
