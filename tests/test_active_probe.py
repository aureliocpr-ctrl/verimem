"""TDD — active probes (Vivarium P87 / cortex active_real): the store BUILDS
the query that would falsify a fact instead of waiting for a contradiction to
wander in. One probe pass over a copula fact:

  * counter-evidence found (same subject, different value, INDEPENDENT
    non-actor source) → propose refuted(counterexample=<id>);
  * survived → the fact's ``unbeaten`` bound GROWS by one survived probe
    (bound semantics: number of probes survived — declared in the proof);
  * engine-signed rivals (actor:*) never count as counter-evidence (P85).
"""
from __future__ import annotations

import pytest

from verimem.active_probe import probe_fact


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "0")
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "0")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    from verimem.client import Memory
    return Memory(tmp_path / "p.db")


def test_probe_finds_independent_counterevidence(mem, monkeypatch):
    # 0.7.0 auto-NLI churn: this test exercises READ-side machinery on
    # conflicting facts, which the write-side semantic tier (auto-on when
    # the model is installed) would now quarantine before they land -- so
    # the write-side NLI is explicitly opted out here.
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "0")
    # 2026-07-28: both facts here are equally guaranteed (neither carries an
    # epistemic label, both carry a source), so this pins DETECTION, which is
    # what the probe owes on such a pair. Applying the absorbing `refuted` to
    # settle it would decide by probe ORDER — probe the labrador and the
    # labrador dies, probe the poodle and the poodle dies — so the even case is
    # now reported as `contested` with the rival named. Refutation by a
    # STRICTLY better-guaranteed rival is pinned in test_verimem_probe_rank.py
    # and test_verimem_probe_contested.py.
    a = mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    b = mem.add("Rex is a poodle.", topic="pets", verified_by=["source-doc:vet:t2"])
    out = probe_fact(mem, a["id"])
    assert out["outcome"] == "contested"
    assert out["rival_id"] == b["id"]
    assert (mem.semantic.get(a["id"]).epistemic or {}).get("kind") != "refuted"


def test_probe_survival_grows_the_bound(mem):
    a = mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    out1 = probe_fact(mem, a["id"])
    assert out1["outcome"] == "survived"
    f1 = mem.semantic.get(a["id"])
    assert f1.epistemic == {"kind": "unbeaten", "bound": 1}
    out2 = probe_fact(mem, a["id"])
    assert out2["outcome"] == "survived"
    assert mem.semantic.get(a["id"]).epistemic["bound"] == 2   # monotone growth


def test_actor_written_rival_never_counts(mem):
    a = mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    mem.add("Rex is a poodle.", topic="pets", verified_by=["actor:composer:r1"])
    out = probe_fact(mem, a["id"])
    assert out["outcome"] == "survived"                        # self-echo can't refute
    assert mem.semantic.get(a["id"]).epistemic["kind"] == "unbeaten"


def test_non_copula_fact_abstains(mem):
    a = mem.add("Remember to water the plants tomorrow morning.", topic="notes",
                verified_by=["source-doc:alice:t1"])
    out = probe_fact(mem, a["id"])
    assert out["outcome"] == "not_probeable"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
