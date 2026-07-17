"""TDD for the PRODUCTION bridge: fact_to_belief + audit_facts (run the TMS over REAL facts).

Closes the critic's recurring "library not live" FAIL: the lifecycle (maintain+propagate)
must be reachable from a real Fact, not only from hand-built Belief objects in tests.
"""
from __future__ import annotations

from dataclasses import dataclass

from verimem.justified_memory import (
    audit_facts,
    collect_contradicted_ids,
    fact_to_belief,
)
from verimem.semantic_conflict import FixedRelationJudge, Relation


@dataclass
class _Fact:  # a minimal stand-in for an Engram Fact row (duck-typed; real field names)
    id: str
    proposition: str
    verified_by: str = ""
    source_episodes: str = ""
    derives_from: tuple[str, ...] = ()  # TYPED logical-derivation edge (R26: NOT lineage_to)
    lineage_to: tuple[str, ...] = ()    # narrative successor pointer — must NOT feed cascade
    valid_until: float | None = None
    superseded_by: str | None = None
    status: str = "active"


def test_fact_to_belief_maps_core_fields() -> None:
    f = _Fact("a1", "the sky is blue", verified_by="ep7", derives_from=("p1", "p2"),
              valid_until=900.0, status="verified")
    b = fact_to_belief(f)
    assert b.id == "a1"
    assert b.proposition == "the sky is blue"
    assert b.source == "ep7"               # provenance present -> justified
    assert b.depends_on == ("p1", "p2")    # TYPED derivation -> ATMS dependency links
    assert b.valid_until == 900.0
    assert b.grounding_score == 100.0      # status verified
    assert b.status == "believed"          # alive facts enter as believed


def test_fact_to_belief_ignores_narrative_lineage_to() -> None:
    # R26: lineage_to is a narrative/session-successor pointer, NOT logical derivation.
    # It must NOT become an ATMS dependency edge (would cause false cascades).
    b = fact_to_belief(_Fact("a1", "x", verified_by="e", lineage_to=("n1", "n2")))
    assert b.depends_on == ()


def test_fact_to_belief_no_provenance_is_unjustified_source() -> None:
    b = fact_to_belief(_Fact("a2", "unsourced claim"))
    assert b.source == ""                   # no verified_by / source_episodes
    assert b.grounding_score == 50.0        # not verified


def test_fact_to_belief_accepts_dict_and_str_lineage() -> None:
    b = fact_to_belief({"id": "a3", "proposition": "x", "source_episodes": "e1",
                        "lineage_parents": "[p1, p2]"})
    assert b.source == "e1"
    assert b.depends_on == ("p1", "p2")     # stringified list is parsed


def test_audit_facts_superseded_is_retracted_not_served() -> None:
    facts = [
        _Fact("f1", "current", verified_by="e1"),
        _Fact("f2", "old", verified_by="e2", superseded_by="f1"),
    ]
    r = audit_facts(facts, now=1000.0)
    assert "f1" in r["served_ids"]
    assert "f2" not in r["served_ids"]
    assert "f2" in r["would_retract_ids"]


def test_audit_facts_stale_is_dropped() -> None:
    facts = [_Fact("f1", "expired", verified_by="e1", valid_until=500.0)]
    r = audit_facts(facts, now=1000.0)
    assert r["served"] == 0
    assert "f1" in r["would_stale_ids"]


def test_audit_facts_cascades_to_derived_of_superseded() -> None:
    # the novel core, live over real facts: f_old superseded; d1 derived from it; d2 from d1.
    # supersession alone would keep d1/d2 (derived from a now-false foundation); propagate
    # cascades the retraction. This is what NO agent-memory product does.
    facts = [
        _Fact("f_old", "foundation", verified_by="e1", superseded_by="f_new"),
        _Fact("f_new", "replacement", verified_by="e2"),
        _Fact("d1", "derived", verified_by="e3", derives_from=("f_old",)),
        _Fact("d2", "chain", verified_by="e4", derives_from=("d1",)),
        _Fact("ok", "independent", verified_by="e5"),
    ]
    r = audit_facts(facts, now=1000.0)
    assert set(r["served_ids"]) == {"f_new", "ok"}     # only justified survive
    assert "d1" in r["would_retract_ids"]              # cascade reached the derived fact
    assert "d2" in r["would_retract_ids"]              # ...and down the chain


def test_audit_facts_contradicted_is_contested_not_served() -> None:
    # retraction-trigger #4 (R28): a contradicted served-belief becomes 'contested' and is
    # NOT served as truth. The caller supplies contradicted_ids (e.g. computed by an NLI pass
    # over semantic_conflict). Distinct from supersession: no superseded_by field is needed.
    facts = [
        _Fact("f1", "the port is 8080", verified_by="e1"),
        _Fact("f2", "the port is 9090", verified_by="e2"),
        _Fact("ok", "unrelated independent fact", verified_by="e3"),
    ]
    r = audit_facts(facts, now=1000.0, contradicted_ids=["f2"])
    assert "f2" not in r["served_ids"]               # a disputed fact is not served as truth
    assert "f2" in r["would_contest_ids"]
    assert set(r["served_ids"]) == {"f1", "ok"}
    assert r["status_counts"].get("contested") == 1


def test_audit_facts_contradiction_cascades_to_logical_derivatives() -> None:
    # a contradicted FOUNDATION pulls its TYPED-derivation descendants too (propagate), the
    # same cascade supersession triggers — but driven by contradiction. Narrative successors
    # (lineage_to) must NOT cascade.
    facts = [
        _Fact("base", "base claim", verified_by="e1"),
        _Fact("d1", "derived from base", verified_by="e2", derives_from=("base",)),
        _Fact("narr", "narrative successor", verified_by="e3", lineage_to=("base",)),
    ]
    r = audit_facts(facts, now=1000.0, contradicted_ids=["base"])
    assert "base" in r["would_contest_ids"]
    assert "d1" in r["would_retract_ids"]            # logical descendant cascades
    assert "narr" in r["served_ids"]                 # narrative successor is untouched


def _cos_only_ab(x: object, y: object) -> float:
    # high cosine ONLY for the {a,b} pair → the judge is consulted only there
    ids = {getattr(x, "id", ""), getattr(y, "id", "")}
    return 0.95 if ids == {"a", "b"} else 0.1


def test_collect_contradicted_ids_pairs_both_members_after_cosine_prefilter() -> None:
    # reuses semantic_conflict: cosine pre-filter narrows to {a,b}, the (stub) judge calls it a
    # contradiction → BOTH a and b are contested; c (low cosine, never judged) is untouched.
    facts = [
        _Fact("a", "the port is 8080", verified_by="e1"),
        _Fact("b", "the port is 9090", verified_by="e2"),
        _Fact("c", "the sky is blue", verified_by="e3"),
    ]
    judge = FixedRelationJudge(Relation.CONTRADICTION)
    ids = collect_contradicted_ids(facts, judge, min_cosine=0.7, cosine_fn=_cos_only_ab)
    assert set(ids) == {"a", "b"}


def test_collect_contradicted_ids_excludes_superseded() -> None:
    # an already-superseded fact is handled by maintain; it must NOT be re-contested here
    facts = [
        _Fact("a", "x", verified_by="e1"),
        _Fact("b", "y", verified_by="e2", superseded_by="a"),
    ]
    judge = FixedRelationJudge(Relation.CONTRADICTION)
    ids = collect_contradicted_ids(facts, judge, min_cosine=0.0, cosine_fn=lambda x, y: 1.0)
    assert "b" not in ids                       # superseded excluded from the live conflict set


def test_collect_then_audit_contests_the_pair_end_to_end() -> None:
    facts = [
        _Fact("a", "the port is 8080", verified_by="e1"),
        _Fact("b", "the port is 9090", verified_by="e2"),
        _Fact("c", "the sky is blue", verified_by="e3"),
    ]
    judge = FixedRelationJudge(Relation.CONTRADICTION)
    ids = collect_contradicted_ids(facts, judge, min_cosine=0.7, cosine_fn=_cos_only_ab)
    r = audit_facts(facts, now=1000.0, contradicted_ids=ids)
    assert set(r["would_contest_ids"]) == {"a", "b"}
    assert r["served_ids"] == ["c"]             # only the unconflicted fact is served


def test_collect_contradicted_ids_neutral_judge_contests_nothing() -> None:
    facts = [_Fact("a", "x", verified_by="e1"), _Fact("b", "y", verified_by="e2")]
    judge = FixedRelationJudge(Relation.NEUTRAL)
    ids = collect_contradicted_ids(facts, judge, min_cosine=0.0, cosine_fn=lambda x, y: 1.0)
    assert ids == []                            # no contradiction → no contest (no false flags)


def test_audit_facts_empty_is_clean() -> None:
    r = audit_facts([], now=1000.0)
    assert r["served"] == 0
    assert r["n_facts"] == 0
