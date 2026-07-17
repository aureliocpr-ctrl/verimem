"""Semantic (NLI) contradiction/entailment detector — the gap the lexical stack
misses (measured: coherence_check + looks_like_conflict catch 0/6 semantic
conflicts at cosine 0.80-0.87). Tests are hermetic: cosine and the relation judge
are both injected, so no embeddings / no claude -p here.
"""
from __future__ import annotations

from verimem.coherence_check import CoherenceWarning
from verimem.semantic import Fact
from verimem.semantic_conflict import (
    Relation,
    build_nli_prompt,
    detect_semantic_conflicts,
    parse_relation,
)


class _RecordingJudge:
    def __init__(self, rel: Relation) -> None:
        self.rel = rel
        self.calls: list[tuple[str, str]] = []

    def classify(self, a: str, b: str) -> Relation:
        self.calls.append((a, b))
        return self.rel


def _f(fid: str, prop: str) -> Fact:
    return Fact(id=fid, proposition=prop, topic="t")


def test_parse_relation_compliant_and_failsafe() -> None:
    assert parse_relation("CONTRADICTION") is Relation.CONTRADICTION
    assert parse_relation("ENTAILMENT") is Relation.ENTAILMENT
    assert parse_relation("NEUTRAL") is Relation.NEUTRAL
    assert parse_relation("neutral.") is Relation.NEUTRAL
    # fail-safe: an unreadable verdict must NOT fabricate a contradiction
    assert parse_relation("") is Relation.NEUTRAL
    assert parse_relation("maybe?") is Relation.NEUTRAL
    # the dangerous case: a NEGATED verdict must not be misread as a conflict
    assert parse_relation("no contradiction") is Relation.NEUTRAL
    assert parse_relation("not a contradiction, they agree") is Relation.NEUTRAL


def test_build_nli_prompt_contains_both_and_labels() -> None:
    system, messages = build_nli_prompt("A says X", "B says Y")
    blob = system + " " + " ".join(m["content"] for m in messages)
    assert "A says X" in blob and "B says Y" in blob
    for label in ("CONTRADICTION", "ENTAILMENT", "NEUTRAL"):
        assert label in blob


def test_detect_contradiction_emits_semantic_conflict() -> None:
    j = _RecordingJudge(Relation.CONTRADICTION)
    warns = detect_semantic_conflicts(
        _f("n", "Caroline lives in Milan"), [_f("o", "Caroline lives in Rome")],
        j, min_cosine=0.7, cosine_fn=lambda a, b: 0.9)
    assert len(warns) == 1
    assert isinstance(warns[0], CoherenceWarning)
    assert warns[0].kind == "semantic_conflict"
    assert warns[0].other_fact_id == "o"


def test_detect_entailment_emits_semantic_duplicate() -> None:
    j = _RecordingJudge(Relation.ENTAILMENT)
    warns = detect_semantic_conflicts(
        _f("n", "Alice is a doctor"), [_f("o", "Alice works as a physician")],
        j, min_cosine=0.7, cosine_fn=lambda a, b: 0.95)
    assert len(warns) == 1 and warns[0].kind == "semantic_duplicate"


def test_detect_neutral_emits_nothing() -> None:
    j = _RecordingJudge(Relation.NEUTRAL)
    warns = detect_semantic_conflicts(
        _f("n", "John is 30 years old"), [_f("o", "John lives in Rome")],
        j, min_cosine=0.7, cosine_fn=lambda a, b: 0.88)
    assert warns == []


def test_nli_system_has_temporal_supersession_rule() -> None:
    """The judge prompt must instruct temporal reconciliation (the validated
    HaluMem FPR-cut), else timestamp-ordered evolution is misread as conflict."""
    system, _ = build_nli_prompt("A", "B")
    low = system.lower()
    assert "timestamp" in low and ("evolution" in low or "evolves" in low)


def test_timestamp_is_passed_to_judge_when_present() -> None:
    """A fact's created_at must reach the judge as a [stamp] prefix so it can tell
    supersession from a same-time conflict (FPR 0.10->0.0125, 2026-06-20)."""
    import datetime as _dt
    # 2025-09-05 and 2026-01-05 epochs (UTC) — clearly different dates
    t_old = _dt.datetime(2025, 9, 5, tzinfo=_dt.timezone.utc).timestamp()
    t_new = _dt.datetime(2026, 1, 5, tzinfo=_dt.timezone.utc).timestamp()
    new = Fact(id="n", proposition="title is Senior PT", topic="t", created_at=t_new)
    old = Fact(id="o", proposition="title is PT", topic="t", created_at=t_old)
    j = _RecordingJudge(Relation.NEUTRAL)
    detect_semantic_conflicts(new, [old], j, min_cosine=0.7, cosine_fn=lambda a, b: 0.9)
    assert len(j.calls) == 1
    a, b = j.calls[0]
    assert a.startswith("[2026-01-05] ") and "title is Senior PT" in a
    assert b.startswith("[2025-09-05] ") and "title is PT" in b


def test_cosine_prefilter_skips_low_similarity() -> None:
    # below threshold -> the (costly) judge must NEVER be consulted
    j = _RecordingJudge(Relation.CONTRADICTION)
    warns = detect_semantic_conflicts(
        _f("n", "totally unrelated thing"), [_f("o", "Caroline lives in Rome")],
        j, min_cosine=0.7, cosine_fn=lambda a, b: 0.40)
    assert warns == []
    assert j.calls == []


def test_bench_shape_and_neutral_judge_flags_nothing() -> None:
    # the bench harness runs with real cosine + an injected judge; a NEUTRAL
    # judge must produce zero semantic conflicts (no claude -p touched).
    from benchmark.semantic_conflict_bench import run
    from verimem.semantic_conflict import FixedRelationJudge

    res = run(FixedRelationJudge(Relation.NEUTRAL))
    assert set(res["per_case"]) == {"A", "B", "C", "D", "E"}
    assert all(c["semantic_conflict_rate"] == 0.0
               for c in res["per_case"].values())
