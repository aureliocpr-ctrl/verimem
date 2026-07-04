"""Cycle #118 (2026-05-17) — Memory self-curation autonomous loop.

Aurelio direttiva (laboratorio mode): "memoria AI-driven pilotata da te,
sperimenta". Cycle 118 implementa un primo loop di auto-cura del
ContradictionStore — NIENTE mutazione dei Fact reali, solo gestione
intelligente delle pair di contraddizioni.

Risultato della misura empirica FASE 1 (232 contradictions live):

* 96% AMBIGUOUS (age_delta=0, conf_delta=0) — NOT auto-actionable.
* 3% FP_LIKELY (boolean_clash + both conf > 0.9 + recent + same topic)
  → pattern classico STRENGTHS/WEAKNESS sectioning del cycle #77
  L3-contradiction detector. Sono complementary sections, non
  contradiction reali.
* 0% safe_supersede + 0% newer_wins (su questo corpus).

Quindi cycle 118 V1 si limita a:
1. **auto_resolve_false_positives**: marca come resolved (con note
   `auto_fp_complementary`) le pair che matchano il pattern FP_LIKELY.
2. **propose_resolution**: per le pair ambigue, salva una "suggested
   resolution" — placeholder per future iterazioni che possano
   coinvolgere ragionamento LLM o review umana.

NO auto-supersede, NO Fact mutation. Solo ContradictionStore.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from engram.contradiction import Contradiction, ContradictionStore
from engram.semantic import Fact, SemanticMemory


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sm.db")


@pytest.fixture
def store(sm: SemanticMemory) -> ContradictionStore:
    return ContradictionStore(sm.db_path)


def _store(sm: SemanticMemory, fid: str, prop: str, *,
           topic: str = "t", conf: float = 0.9,
           created_at: float | None = None) -> Fact:
    f = Fact(
        id=fid, proposition=prop, topic=topic, confidence=conf,
        status="model_claim",
        created_at=created_at if created_at is not None else time.time(),
    )
    sm.store(f)
    return f


def _record(store: ContradictionStore, a_id: str, b_id: str, *,
            kind: str = "boolean_clash", sim: float = 0.92) -> Contradiction:
    c = Contradiction(fact_a_id=a_id, fact_b_id=b_id, kind=kind, similarity=sim)
    store.add(c)
    return c


class TestClassifyContradictionsPureFunction:
    """`classify_contradiction(c, a, b)` returns a bucket label."""

    def test_safe_supersede_when_one_side_superseded(
        self, sm: SemanticMemory, store: ContradictionStore,
    ) -> None:
        from engram.self_curation import classify_contradiction
        a = Fact(id="a", proposition="X is 5MB", topic="t", confidence=0.9,
                 status="model_claim", superseded_by="z", superseded_at=time.time())
        b = Fact(id="b", proposition="X is 50MB", topic="t", confidence=0.9,
                 status="model_claim")
        sm.store(a); sm.store(b)
        c = _record(store, "a", "b", kind="numeric_clash", sim=0.9)
        bucket = classify_contradiction(c, a, b)
        assert bucket == "safe_supersede"

    def test_fp_likely_when_both_high_conf_recent_boolean(
        self, sm: SemanticMemory, store: ContradictionStore,
    ) -> None:
        from engram.self_curation import classify_contradiction
        now = time.time()
        a = _store(sm, "a", "STRENGTHS: project does X well",
                   conf=0.98, created_at=now)
        b = _store(sm, "b", "WEAKNESS: project does not Y",
                   conf=0.98, created_at=now - 5 * 86400)
        c = _record(store, "a", "b", kind="boolean_clash", sim=0.92)
        bucket = classify_contradiction(c, a, b)
        assert bucket == "fp_likely"

    def test_newer_wins_when_age_and_conf_deltas_strong(
        self, sm: SemanticMemory, store: ContradictionStore,
    ) -> None:
        from engram.self_curation import classify_contradiction
        now = time.time()
        a = _store(sm, "a", "X has 5MB total", conf=0.5,
                   created_at=now - 90 * 86400)
        b = _store(sm, "b", "X has 50MB total", conf=0.9, created_at=now)
        c = _record(store, "a", "b", kind="numeric_clash", sim=0.9)
        bucket = classify_contradiction(c, a, b)
        assert bucket == "newer_wins"

    def test_ambiguous_otherwise(
        self, sm: SemanticMemory, store: ContradictionStore,
    ) -> None:
        from engram.self_curation import classify_contradiction
        a = _store(sm, "a", "X is 5MB", conf=0.9)
        b = _store(sm, "b", "X is 50MB", conf=0.9)
        c = _record(store, "a", "b", kind="numeric_clash", sim=0.9)
        bucket = classify_contradiction(c, a, b)
        assert bucket == "ambiguous"


class TestAutoResolveFalsePositives:
    """`auto_resolve_false_positives(sm, store)` marks FP_LIKELY pairs
    as resolved with note `auto_fp_complementary`."""

    def test_resolves_fp_likely_only(
        self, sm: SemanticMemory, store: ContradictionStore,
    ) -> None:
        from engram.self_curation import auto_resolve_false_positives
        now = time.time()
        # FP_LIKELY pair
        a = _store(sm, "a-fp", "STRENGTHS section A1", conf=0.98, created_at=now)
        b = _store(sm, "b-fp", "WEAKNESS section A2", conf=0.98, created_at=now)
        c_fp = _record(store, "a-fp", "b-fp", kind="boolean_clash")
        # AMBIGUOUS pair
        a2 = _store(sm, "a-amb", "X has 5MB", conf=0.9)
        b2 = _store(sm, "b-amb", "X has 50MB", conf=0.9)
        c_amb = _record(store, "a-amb", "b-amb", kind="numeric_clash")

        report = auto_resolve_false_positives(sm, store)

        assert report["resolved"] == 1
        assert report["skipped"] == 1
        # FP_LIKELY resolved
        unresolved_ids = {x.id for x in store.list_unresolved()}
        assert c_fp.id not in unresolved_ids
        # Ambiguous still unresolved
        assert c_amb.id in unresolved_ids

    def test_returns_zero_on_empty_store(
        self, sm: SemanticMemory, store: ContradictionStore,
    ) -> None:
        from engram.self_curation import auto_resolve_false_positives
        report = auto_resolve_false_positives(sm, store)
        assert report["resolved"] == 0
        assert report["skipped"] == 0
        assert report["scanned"] == 0

    def test_resolution_note_carries_auto_fp_marker(
        self, sm: SemanticMemory, store: ContradictionStore,
    ) -> None:
        """The resolved row must carry a distinguishable note so a
        human reviewer can later filter auto-resolutions from manual
        ones."""
        from engram.self_curation import auto_resolve_false_positives
        now = time.time()
        a = _store(sm, "a", "VERDICT: prototype solid", conf=0.95, created_at=now)
        b = _store(sm, "b", "WEAKNESS: not yet production", conf=0.95, created_at=now)
        c = _record(store, "a", "b", kind="boolean_clash")
        auto_resolve_false_positives(sm, store)
        # The resolved row stays in `list_all` with a note.
        all_rows = store.list_all()
        target = next((x for x in all_rows if x.id == c.id), None)
        assert target is not None
        assert target.resolved_at is not None
        assert "auto_fp_complementary" in (target.resolution_note or "")

    def test_dangling_pair_skipped_not_resolved(
        self, sm: SemanticMemory, store: ContradictionStore,
    ) -> None:
        """If either fact_a or fact_b no longer exists in SemanticMemory,
        the contradiction is skipped (cannot classify safely)."""
        from engram.self_curation import auto_resolve_false_positives
        # Record a contradiction whose facts were deleted/never existed.
        c = _record(store, "missing-a", "missing-b")
        report = auto_resolve_false_positives(sm, store)
        assert report["resolved"] == 0
        # Either skipped or dangling — must NOT be resolved.
        unresolved = [x.id for x in store.list_unresolved()]
        assert c.id in unresolved


class TestAuditOnly:
    """`audit_contradictions(sm, store)` returns the bucket distribution
    WITHOUT mutating anything — for visibility / decision support."""

    def test_audit_reports_counts(
        self, sm: SemanticMemory, store: ContradictionStore,
    ) -> None:
        from engram.self_curation import audit_contradictions
        now = time.time()
        # FP_LIKELY
        _store(sm, "a1", "STRENGTHS X", conf=0.98, created_at=now)
        _store(sm, "b1", "WEAKNESS Y", conf=0.98, created_at=now)
        _record(store, "a1", "b1", kind="boolean_clash")
        # AMBIGUOUS
        _store(sm, "a2", "X is 5MB", conf=0.9)
        _store(sm, "b2", "X is 50MB", conf=0.9)
        _record(store, "a2", "b2", kind="numeric_clash")

        report = audit_contradictions(sm, store)
        assert report["total_unresolved"] == 2
        assert report["buckets"]["fp_likely"] == 1
        assert report["buckets"]["ambiguous"] == 1

    def test_audit_does_not_mutate(
        self, sm: SemanticMemory, store: ContradictionStore,
    ) -> None:
        from engram.self_curation import audit_contradictions
        now = time.time()
        _store(sm, "a", "STRENGTHS X", conf=0.98, created_at=now)
        _store(sm, "b", "WEAKNESS Y", conf=0.98, created_at=now)
        c = _record(store, "a", "b", kind="boolean_clash")
        before = store.count_unresolved()
        audit_contradictions(sm, store)
        # No row marked resolved.
        assert store.count_unresolved() == before
        unresolved_ids = {x.id for x in store.list_unresolved()}
        assert c.id in unresolved_ids
