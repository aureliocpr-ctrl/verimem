"""Counter-evidence cannot be worse-guaranteed than what it destroys.

`probe_fact` applied the ABSORBING `refuted` label to any live, same-subject,
differently-valued, independently-sourced rival — without ever reading either
side's epistemic label. So an UNLABELED rival permanently killed a machine-
`proven` fact, which is the exact inversion of what the guardian decides on the
same store: guardian._RANK scores proven above unlabeled, so `correct_read`
serves the proven fact and cites the other.

Measured 2026-07-28 (design review + bench): on one store the guardian answered
CORRECT and served the proven fact, while probe_fact stamped that same fact
`refuted` — and `refuted` is absorbing, so the loss is permanent and repairable
only by supersession.

Two readers of one store must not disagree about which guarantee is stronger,
so the ordering lives in ONE place (epistemic.guarantee_rank) and both ask it.

Deliberately NOT pinned here: the symmetric case (two equally-guaranteed rivals),
where the probe still refutes whichever fact is probed first. That is a real
defect, but curing it changes what the probe is FOR, so it is a decision to take
explicitly rather than a bug to patch quietly.
"""
from __future__ import annotations

import pytest

from verimem.active_probe import probe_fact
from verimem.epistemic import make_proven, make_unbeaten
from verimem.guardian import correct_read


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "0")
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "0")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "0")
    from verimem.client import Memory
    return Memory(tmp_path / "r.db")


def test_unlabeled_rival_does_not_refute_a_proven_fact(mem):
    a = mem.add("Rex is a labrador.", topic="pets",
                verified_by=["source-doc:kennel:t1"])
    assert mem.semantic.set_epistemic(a["id"], make_proven("qa:kennel_registry_PASS"))
    mem.add("Rex is a poodle.", topic="pets", verified_by=["source-doc:bob:t1"])
    out = probe_fact(mem, a["id"])
    assert out["outcome"] != "refuted_proposed", out
    assert (mem.semantic.get(a["id"]).epistemic or {}).get("kind") == "proven", (
        "an unlabeled rival must not overwrite a proven guarantee — and refuted "
        "is absorbing, so this would be permanent")


def test_unbeaten_rival_does_not_refute_a_proven_fact(mem):
    a = mem.add("Rex is a labrador.", topic="pets",
                verified_by=["source-doc:kennel:t1"])
    assert mem.semantic.set_epistemic(a["id"], make_proven("qa:kennel_registry_PASS"))
    b = mem.add("Rex is a poodle.", topic="pets", verified_by=["source-doc:bob:t1"])
    assert mem.semantic.set_epistemic(b["id"], make_unbeaten(12))
    out = probe_fact(mem, a["id"])
    assert out["outcome"] != "refuted_proposed", out
    assert (mem.semantic.get(a["id"]).epistemic or {}).get("kind") == "proven"


def test_a_better_guaranteed_rival_still_refutes(mem):
    """The guard must not disarm the probe: a stronger rival still bites."""
    a = mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    b = mem.add("Rex is a poodle.", topic="pets", verified_by=["source-doc:vet:t2"])
    assert mem.semantic.set_epistemic(b["id"], make_proven("qa:vet_registry_PASS"))
    out = probe_fact(mem, a["id"])
    assert out["outcome"] == "refuted_proposed", out
    assert out["counterexample_id"] == b["id"]


def test_probe_and_guardian_rank_guarantees_the_same_way(mem):
    """One ordering of guarantees, asked by both readers."""
    a = mem.add("Rex is a labrador.", topic="pets",
                verified_by=["source-doc:kennel:t1"])
    assert mem.semantic.set_epistemic(a["id"], make_proven("qa:kennel_registry_PASS"))
    mem.add("Rex is a poodle.", topic="pets", verified_by=["source-doc:bob:t1"])
    guard = correct_read(mem, "What breed is Rex?")
    probe = probe_fact(mem, a["id"])
    assert guard["served_id"] == a["id"], "the guardian serves the proven fact"
    assert probe["outcome"] != "refuted_proposed", (
        f"the guardian serves {a['id']} as the better-guaranteed answer while "
        f"the probe reports {probe['outcome']} against it")
