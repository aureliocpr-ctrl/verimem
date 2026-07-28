"""A conflict with no winner is not a reason to kill one of the two facts.

`refuted` is ABSORBING (epistemic.can_transition: refuted -> proven|unbeaten is
forbidden), so applying it is irreversible and repairable only by supersession.
`probe_fact` applied it whenever it found ANY same-subject rival with a
different value and an independent source — without asking whether that rival
was better guaranteed. Two consequences, both measured 2026-07-28:

* ORDER DECIDES. Two equally-guaranteed conflicting facts: probing the labrador
  kills the labrador, probing the poodle kills the poodle. A nightly pass would
  execute a coin flip on which knowledge survives, permanently.
* SPECIALISATION READS AS CONTRADICTION. "Rex is a dog." and "Rex is a
  labrador." are BOTH true, but the object head-nouns differ, so the general
  fact is stamped refuted and never served again — the exact inversion of
  "abstain instead of hallucinate".

The cure is not to disarm the probe. It keeps building the falsifying query and
keeps refuting when the counter-evidence is genuinely stronger; what changes is
what it does when the conflict has NO epistemic winner: it reports `contested`
and NAMES the rival, instead of picking a loser in silence. That is the same
answer the guardian already gives on the same input (ABSTAIN, both sides shown)
— one store, one verdict.

Second, `unbeaten(bound)` is a receipt: the bound is documented as the NUMBER OF
PROBES SURVIVED. When every rival was excluded by a guard, no probe occurred and
survival was structurally guaranteed, so minting the receipt overstates
verification — precisely the failure this product exists to prevent.
"""
from __future__ import annotations

import pytest

from verimem.active_probe import probe_fact
from verimem.epistemic import make_proven


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "0")
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "0")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "0")
    from verimem.client import Memory
    return Memory(tmp_path / "c.db")


def _kind(mem, fact_id):
    return (mem.semantic.get(fact_id).epistemic or {}).get("kind")


def test_an_even_conflict_is_contested_not_refuted(mem):
    a = mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    b = mem.add("Rex is a poodle.", topic="pets", verified_by=["source-doc:vet:t2"])
    out = probe_fact(mem, a["id"])
    assert out["outcome"] == "contested", out
    assert out["rival_id"] == b["id"], "the rival is NAMED, not just counted"
    assert _kind(mem, a["id"]) != "refuted", (
        "an absorbing label must not be applied to settle a tie")


def test_the_probe_order_no_longer_decides_who_dies(mem):
    """The same store, probed from either side, must reach the same verdict."""
    a = mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    b = mem.add("Rex is a poodle.", topic="pets", verified_by=["source-doc:vet:t2"])
    first = probe_fact(mem, a["id"])["outcome"]
    second = probe_fact(mem, b["id"])["outcome"]
    assert first == second == "contested"
    assert _kind(mem, a["id"]) != "refuted"
    assert _kind(mem, b["id"]) != "refuted"


def test_a_true_general_fact_survives_a_true_specific_one(mem):
    """'Rex is a dog' and 'Rex is a labrador' are both true; neither may kill
    the other on the strength of two different head-nouns."""
    dog = mem.add("Rex is a dog.", topic="pets", verified_by=["source-doc:A:1"])
    mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:B:1"])
    out = probe_fact(mem, dog["id"])
    assert out["outcome"] == "contested", out
    assert _kind(mem, dog["id"]) != "refuted"


def test_stronger_counter_evidence_still_refutes(mem):
    """The probe is not disarmed: a better-guaranteed rival still bites."""
    a = mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    b = mem.add("Rex is a poodle.", topic="pets", verified_by=["source-doc:vet:t2"])
    assert mem.semantic.set_epistemic(b["id"], make_proven("qa:vet_registry_PASS"))
    out = probe_fact(mem, a["id"])
    assert out["outcome"] == "refuted_proposed", out
    assert _kind(mem, a["id"]) == "refuted"


def test_survival_is_only_minted_when_a_probe_could_have_failed(mem):
    """`unbeaten(n)` says n probes were SURVIVED. With every rival excluded by a
    guard, nothing was survived — the receipt must not claim it."""
    a = mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    mem.add("Rex is a poodle.", topic="pets",
            verified_by=["actor:composer:r1"])          # P85: cannot testify
    out = probe_fact(mem, a["id"])
    assert out["outcome"] != "survived", out
    assert _kind(mem, a["id"]) != "unbeaten", (
        "no rival could compete, so no falsification attempt took place")


def test_a_genuinely_unchallenged_fact_still_survives(mem):
    """With no rival at all, survival is real and the bound grows as before."""
    a = mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    out = probe_fact(mem, a["id"])
    assert out["outcome"] == "survived"
    assert mem.semantic.get(a["id"]).epistemic == {"kind": "unbeaten", "bound": 1}
