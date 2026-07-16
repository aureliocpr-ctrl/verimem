"""Fase-C audit mod.8 (client.py): history() must return the FULL trail.

Reproduced live 2026-07-17: after add(500k) → update(550k) → update(600k),
``history(oldest_id)`` returned 3 entries but ``history(newest_id)`` returned
ONLY 1 — the walk was forward-only, so the id a caller most naturally holds
(the CURRENT fact, e.g. from search) yielded no audit trail at all, while the
quickstart promises "the supersession chain of one fact (audit trail)". The
fix walks BACKWARD to the lineage root first, then forward — any id in the
chain returns the same full oldest→newest trail.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def mem(tmp_path):
    from engram.client import Memory
    return Memory(tmp_path / "h.db")


def _chain(mem):
    r1 = mem.add("Client budget is 500k.")
    r2 = mem.update(r1["id"], "Client budget is 550k.")
    r3 = mem.update(r2["id"], "Client budget is 600k.")
    return r1["id"], r2["id"], r3["id"]


def test_history_from_newest_returns_full_trail(mem):
    a, b, c = _chain(mem)
    trail = mem.history(c)                      # the id a caller actually has
    assert [e["id"] for e in trail] == [a, b, c]
    assert trail[0]["superseded_by"] == b
    assert trail[-1]["superseded_by"] is None   # current fact closes the trail


def test_history_from_middle_returns_full_trail(mem):
    a, b, c = _chain(mem)
    assert [e["id"] for e in mem.history(b)] == [a, b, c]


def test_history_from_oldest_unchanged(mem):
    a, b, c = _chain(mem)
    assert [e["id"] for e in mem.history(a)] == [a, b, c]


def test_history_singleton_and_unknown(mem):
    r = mem.add("Standalone fact.")
    assert [e["id"] for e in mem.history(r["id"])] == [r["id"]]
    assert mem.history("no-such-id") == []


def test_get_and_get_all_expose_same_provenance_as_search(mem):
    # audit mod.8: a trust-conditioning caller must not LOSE verified_by /
    # asserted_at the moment it re-fetches by id — one provenance surface.
    r = mem.add("Standalone provenance fact.", asserted_at=1741000000.0)
    for view in (mem.get(r["id"]), mem.get_all(limit=5)[0]):
        for key in ("asserted_at", "created_at", "source", "verified_by"):
            assert key in view, f"missing {key} in {sorted(view)}"
    assert mem.get(r["id"])["asserted_at"] == 1741000000.0
