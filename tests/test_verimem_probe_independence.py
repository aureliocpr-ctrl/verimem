"""An active probe may only be refuted by an INDEPENDENT source.

`probe_fact` filtered rivals five ways — self, not-LIVE, same subject, agreement,
and `actor:` (P85) — but never compared the rival's source with the FACT'S OWN.
The module docstring promises counter-evidence "from an INDEPENDENT non-engine
source"; "not the engine" is not the same claim as "independent".

Two consequences, and `refuted` is ABSORBING — a wrong one kills a fact forever:

* alice says "Rex is a labrador", then alice says "Rex is a poodle" → the first
  fact was refuted. That is a source CORRECTING ITSELF, not counter-evidence;
  the supersession machinery exists for exactly that case.
* a fact carrying NO provenance at all could refute a fact that cites a source —
  and 92% of a real corpus carries no provenance.

The rule this pins: refutation is irreversible, so the counter-evidence must be
at least as well-sourced as what it kills — a rival needs an identifiable source,
and that source must differ from the fact's own.
"""
from __future__ import annotations

import pytest

from verimem.active_probe import probe_fact


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "0")
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "0")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "0")
    from verimem.client import Memory
    return Memory(tmp_path / "p.db")


def test_same_source_correction_does_not_refute(mem):
    """A source revising itself is supersession, not falsification.

    2026-07-28: the outcome is `inconclusive`, not `survived`. A rival existed
    and a guard removed it, so nothing withstood falsification — claiming
    survival (and minting an `unbeaten` bound that counts probes SURVIVED)
    would sell a receipt no probe earned.
    """
    a = mem.add("Rex is a labrador.", topic="pets",
                verified_by=["source-doc:alice:t1"])
    mem.add("Rex is a poodle.", topic="pets", verified_by=["source-doc:alice:t2"])
    out = probe_fact(mem, a["id"])
    assert out["outcome"] == "inconclusive"
    assert (mem.semantic.get(a["id"]).epistemic or {}).get("kind") != "refuted"


def test_unsourced_rival_does_not_refute_a_sourced_fact(mem):
    """Refutation is absorbing: it cannot be cheaper than what it destroys."""
    a = mem.add("Rex is a labrador.", topic="pets",
                verified_by=["source-doc:alice:t1"])
    mem.add("Rex is a poodle.", topic="pets")          # no provenance at all
    out = probe_fact(mem, a["id"])
    assert out["outcome"] == "inconclusive"
    assert (mem.semantic.get(a["id"]).epistemic or {}).get("kind") != "refuted"


def test_an_independent_rival_is_still_detected(mem):
    """The guard must not blind the probe: a genuine rival is still found and
    NAMED. Equally guaranteed, so the verdict is `contested` rather than a
    refutation decided by which side was probed first."""
    a = mem.add("Rex is a labrador.", topic="pets",
                verified_by=["source-doc:alice:t1"])
    b = mem.add("Rex is a poodle.", topic="pets", verified_by=["source-doc:vet:t2"])
    out = probe_fact(mem, a["id"])
    assert out["outcome"] == "contested"
    assert out["rival_id"] == b["id"]


def test_unsourced_fact_can_still_be_refuted_by_a_sourced_rival(mem):
    """The rule is 'at least as well-sourced', not 'both must be sourced':
    a cited rival may still refute a fact that cites nothing."""
    a = mem.add("Rex is a labrador.", topic="pets")     # fact has no provenance
    b = mem.add("Rex is a poodle.", topic="pets", verified_by=["source-doc:vet:t2"])
    out = probe_fact(mem, a["id"])
    assert out["outcome"] == "refuted_proposed"
    assert out["counterexample_id"] == b["id"]
