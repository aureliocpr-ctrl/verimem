"""Audit#2 2026-06-08 A-4/A9: supersede_chain(atomic=True) documents "any error
mid-chain rolls back the previously-applied hops (state unchanged)", but the
loop only caught SupersedeConflict / SupersedeError. An UNEXPECTED exception
(RuntimeError, sqlite3.OperationalError 'database is locked', a coherence-hook
bug, ...) from supersede() escaped the function WITHOUT rolling back the hops
already applied -> partial mutation, the documented atomic contract violated.
Fix: a catch-all that, in atomic mode, restores the supersession snapshots and
returns ok=False (identical handling to the conflict/error paths).
"""
from __future__ import annotations

from engram.semantic import Fact, SemanticMemory


def _store(sm, prop):
    f = Fact(proposition=prop, topic="t", status="model_claim", source_episodes=["e"])
    sm.store(f, embed="defer")
    with sm._connect() as c:
        return c.execute(
            "SELECT id FROM facts WHERE proposition = ?", (prop,)
        ).fetchone()[0]


def test_atomic_chain_rolls_back_on_unexpected_error(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    a = _store(sm, "fact-A")
    b = _store(sm, "fact-B")
    c = _store(sm, "fact-C")

    real = sm.supersede
    calls = {"n": 0}

    def flaky(old, new, *, reason=""):
        calls["n"] += 1
        if calls["n"] == 2:  # hop0 (a->b) applied; blow up on hop1 (b->c)
            raise RuntimeError("unexpected backend failure mid-chain")
        return real(old, new, reason=reason)

    monkeypatch.setattr(sm, "supersede", flaky)
    res = sm.supersede_chain([a, b, c], reason="r", atomic=True)

    assert res["ok"] is False
    assert res["error"] and "unexpected" in res["error"].lower()
    # hop0 (a->b) MUST be rolled back: `a` is no longer superseded.
    pa = sm.get(a)
    assert pa is not None and pa.superseded_by is None, (
        "atomic chain left hop0 applied after an unexpected error (A-4/A9)"
    )
