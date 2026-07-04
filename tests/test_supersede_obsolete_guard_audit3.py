"""audit#3-r3 (R2/R10): a SUPERSEDED (obsolete) fact must never be used to
invalidate a LIVE one. Its status rank is stale, so heal_contradictions /
auto_supersede_on_contradiction must refuse it as the winning new_id.
"""
from __future__ import annotations

from engram.semantic import Fact, SemanticMemory


def test_auto_supersede_rejects_obsolete_winner(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(id="A", proposition="prod region is eu-west-1", topic="t",
                  status="verified", source_episodes=["e"]))
    sm.store(Fact(id="B", proposition="prod region is us-east-1", topic="t",
                  status="model_claim", source_episodes=["e"]))
    sm.store(Fact(id="C", proposition="prod region is af-south-1", topic="t",
                  status="verified", source_episodes=["e"]))
    # A becomes obsolete (superseded by C).
    sm.supersede("A", "C", reason="newer truth")
    assert sm.get("A").superseded_by == "C"

    # The obsolete A must NOT be allowed to supersede the live B.
    res = sm.auto_supersede_on_contradiction("A", ["B"])
    assert "B" not in res.get("superseded", []), res
    assert sm.get("B").superseded_by is None, (
        "live fact B was wrongly invalidated by an obsolete winner A"
    )
