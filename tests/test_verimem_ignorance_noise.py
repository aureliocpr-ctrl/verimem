"""Irrelevant facts must not change the diagnosis of an unrelated query.

The ignorance map exists to answer "what am I missing to answer this?", and
each class carries a different acquisition action:

  no_evidence  -> "a source about: rome, weather, tomorrow"
  below_floor  -> "stronger evidence — the best hit sits under the floor"

Measured 2026-07-28 (banco 5): the query "Che tempo fa domani a Roma?" was
classified `no_evidence` on an empty store and `below_floor` after adding
thirteen facts about SERVERS. No evidence about the weather was added, yet the
advice changed to "get stronger evidence" — pointing the operator at a fact
about Server3. The work-list that is supposed to schedule the cure gets sent
the wrong errand.

The store already knows how to tell noise from weak evidence and does not need
a new constant to do it: `relevance_floor.estimate_relevance_floor` measures
the store's OWN noise ceiling with scrambled in-domain probes (words drawn from
different facts, shuffled — lexically in-domain, semantically nothing). A hit
at or below that ceiling is noise, not weak support.

Deliberately conservative: on a store too small to measure, the estimate is 0.0
and nothing changes.
"""
from __future__ import annotations

import pytest

from verimem.ignorance_map import ignorance_map

QUERY = "Che tempo fa domani a Roma?"


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "0")
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "0")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "0")
    from verimem.client import Memory
    return Memory(tmp_path / "n.db")


def _klass(mem, query=QUERY, **kw):
    return ignorance_map(mem, [query], **kw)["queries"][0]["class"]


def test_unrelated_facts_do_not_turn_no_evidence_into_below_floor(mem):
    before = _klass(mem)
    for i in range(14):
        mem.add(f"Server{i} is a machine.", topic="ops",
                verified_by=[f"source-doc:s{i}:t1"])
    after = _klass(mem)
    assert before == after == "no_evidence", (
        f"{before!r} -> {after!r}: fourteen facts about servers changed the "
        f"diagnosis of a question about the weather, and with it the advice")


def test_genuinely_weak_evidence_is_still_below_floor(mem):
    """The guard must not collapse every class into no_evidence: a hit that is
    ABOUT the query but under the floor is still weak evidence, not noise."""
    mem.add("Rome is a city.", topic="geo", verified_by=["source-doc:atlas:t1"])
    for i in range(14):
        mem.add(f"Server{i} is a machine.", topic="ops",
                verified_by=[f"source-doc:s{i}:t1"])
    assert _klass(mem, "What is Rome?", floor=0.999) == "below_floor"


def test_the_advice_matches_the_class(mem):
    """Whatever the class, the cure it names must fit it."""
    for i in range(14):
        mem.add(f"Server{i} is a machine.", topic="ops",
                verified_by=[f"source-doc:s{i}:t1"])
    row = ignorance_map(mem, [QUERY])["queries"][0]
    assert row["class"] == "no_evidence"
    assert "a source about" in row["what_would_help"]


def test_the_report_says_where_the_noise_floor_came_from(mem):
    """0.0 means three different things and the report told them apart in none.

    estimate_relevance_floor returns 0.0 when the store is too small to measure
    (deliberate: a floor guessed from nothing is worse than none), and the
    caller ALSO falls back to 0.0 when the measurement raises. With the guard at
    0.0 every weak hit is classified below_floor again — the exact pre-fix
    misclassification — so "measurement crashed, guard disabled" and "store too
    small, guard intentionally off" have to be distinguishable in the receipt.
    """
    out = ignorance_map(mem, [QUERY])
    assert out["noise_floor_source"] in ("measured", "unmeasurable", "failed")


def test_an_explicit_floor_is_reported_as_the_callers(mem):
    out = ignorance_map(mem, [QUERY], noise_floor=0.42)
    assert out["noise_floor"] == 0.42
    assert out["noise_floor_source"] == "caller"


def test_a_measurement_failure_is_not_silently_a_zero(mem, monkeypatch):
    monkeypatch.setattr("verimem.relevance_floor.estimate_relevance_floor",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    out = ignorance_map(mem, [QUERY])
    assert out["noise_floor"] == 0.0
    assert out["noise_floor_source"] == "failed", (
        "a crashed measurement must not look like a measured 0.0")


def test_a_store_too_small_to_measure_changes_nothing(mem):
    """estimate_relevance_floor returns 0.0 when it cannot measure; the map
    must then behave exactly as before rather than guess."""
    mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:a:t1"])
    out = ignorance_map(mem, ["What breed is Rex?"])
    assert out["queries"][0]["class"] in ("answerable", "below_floor")
    assert sum(out["by_class"].values()) == out["n"] == 1
