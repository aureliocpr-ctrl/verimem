"""TDD for engram.justified_memory — grounded truth-maintenance (the 2027 thesis core)."""
from __future__ import annotations

from engram.justified_memory import (
    Belief,
    admit,
    justified_belief_integrity,
    maintain,
    propagate,
    served,
)


def test_admit_grounded_is_believed() -> None:
    b = admit(lambda s, p: 95.0, "X is A", "the source states X is A", threshold=85, bid="1")
    assert b.status == "believed"
    assert b.justified is True


def test_admit_ungrounded_is_rejected() -> None:
    b = admit(lambda s, p: 30.0, "X is B", "an unrelated source", threshold=85, bid="2")
    assert b.status == "rejected"
    assert b.justified is False


def test_supersede_retracts() -> None:
    b = Belief("1", "X is A", "src", 95.0, "believed")
    assert maintain([b], now=0, superseded_ids=["1"])[0].status == "retracted"


def test_contradiction_contests() -> None:
    b = Belief("1", "X is A", "src", 95.0, "believed")
    assert maintain([b], now=0, contradicted_ids=["1"])[0].status == "contested"


def test_expiry_makes_stale() -> None:
    b = Belief("1", "X is A", "src", 95.0, "believed", valid_until=100.0)
    assert maintain([b], now=200.0)[0].status == "stale"


def test_contested_recovers_when_contradiction_resolved() -> None:
    # the JTMS property: a belief recovers when its justification holds again
    b = Belief("1", "X is A", "src", 95.0, "contested")
    assert maintain([b], now=0)[0].status == "believed"


def test_rejected_and_retracted_are_terminal() -> None:
    rej = Belief("1", "X", "src", 30.0, "rejected")
    ret = Belief("2", "Y", "src", 95.0, "retracted")
    out = maintain([rej, ret], now=0, superseded_ids=["1", "2"], contradicted_ids=["1"])
    assert out[0].status == "rejected"
    assert out[1].status == "retracted"


def test_served_excludes_unjustified_and_expired() -> None:
    bs = [
        Belief("1", "a", "s", 95.0, "believed"),
        Belief("2", "b", "s", 95.0, "retracted"),
        Belief("3", "c", "s", 95.0, "believed", valid_until=10.0),  # expired at now=100
        Belief("4", "d", "s", 95.0, "contested"),
    ]
    assert [b.id for b in served(bs, now=100.0)] == ["1"]


def test_jbi_metric() -> None:
    s = [Belief("1", "a", "s", 95.0, "believed"), Belief("2", "b", "s", 95.0, "believed")]
    assert justified_belief_integrity(s, ["1"]) == 0.5


def test_jbi_empty_is_vacuously_one() -> None:
    assert justified_belief_integrity([], ["1"]) == 1.0


# ---- ATMS transitive retraction (propagate) -------------------------------------
def test_propagate_cascades_retraction() -> None:
    # A justifies B justifies C; retract A -> B and C must auto-retract (transitive)
    a = Belief("A", "base", "src", 95.0, "believed")
    b = Belief("B", "derived", "from A", 95.0, "believed", depends_on=("A",))
    c = Belief("C", "derived2", "from B", 95.0, "believed", depends_on=("B",))
    m = maintain([a, b, c], now=0, superseded_ids=["A"])     # A -> retracted
    out = {x.id: x.status for x in propagate(m, now=0)}
    assert out["A"] == "retracted"
    assert out["B"] == "retracted"   # lost its justification (A)
    assert out["C"] == "retracted"   # cascaded through B


def test_propagate_keeps_belief_when_support_holds() -> None:
    a = Belief("A", "base", "src", 95.0, "believed")
    b = Belief("B", "derived", "from A", 95.0, "believed", depends_on=("A",))
    out = {x.id: x.status for x in propagate(maintain([a, b], now=0), now=0)}
    assert out["A"] == "believed"
    assert out["B"] == "believed"


def test_propagate_ignores_raw_source_deps() -> None:
    # a dep that is not a belief id is a raw source (assumed present) -> not a retraction cause
    b = Belief("B", "derived", "from doc#1", 95.0, "believed", depends_on=("doc#1",))
    assert propagate([b], now=0)[0].status == "believed"
