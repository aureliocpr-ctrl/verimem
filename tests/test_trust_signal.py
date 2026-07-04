"""Cycle #117 (2026-05-17) — Memory self-doubt layer: TrustSignal on recall().

Aurelio direttiva 2026-05-17 (laboratorio mode, pensiero ampio):

   "HippoAgent non sa quando NON FIDARSI DI SÉ. Recall ritorna fact con
   cosine alta, ma NON dice 'questo fact ha 3 contradiction associate,
   age=180 giorni, è stato corretto 2 volte'. Sessione futura usa il
   fact come verità → propaga errore."

Cycle 117 add an opt-in `trust_signals` flag to `SemanticMemory.recall()`.
When enabled, every hit comes back enriched with a `TrustSignal`
verdict — `trusted` / `stale` / `contested` / `obsolete` / `unverified` —
computed live from age + ContradictionStore + supersession + status.

Test plan
---------
1. Pure function on freshly-created fact → "trusted".
2. Old fact (>180 days) → "stale".
3. Fact whose id appears in ContradictionStore → "contested".
4. Fact with superseded_by set → "obsolete".
5. legacy_unverified fact → "unverified".
6. recall(trust_signals=True) returns 3-tuples (fact, sim, signal).
7. recall(trust_signals=False) (default) returns 2-tuples — backwards-compat.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from engram.semantic import Fact, SemanticMemory


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sm.db")


class TestTrustSignalPureFunction:
    """compute_trust_signal(fact, sm, *, now, contradiction_store=None)."""

    def test_fresh_verified_fact_is_trusted(self, sm: SemanticMemory) -> None:
        from engram.trust_signal import compute_trust_signal
        now = time.time()
        f = Fact(
            id="f-fresh", proposition="X is 5MB", topic="t",
            confidence=0.95, status="model_claim", created_at=now,
        )
        sm.store(f)
        sig = compute_trust_signal(f, sm, now=now)
        assert sig.verdict == "trusted"
        assert sig.age_days < 1.0
        assert sig.n_contradictions == 0
        assert sig.is_superseded is False

    def test_old_fact_is_stale(self, sm: SemanticMemory) -> None:
        from engram.trust_signal import compute_trust_signal
        now = time.time()
        old_ts = now - 200 * 86400  # 200 days ago
        f = Fact(
            id="f-old", proposition="X is 5MB", topic="t",
            confidence=0.95, status="model_claim", created_at=old_ts,
        )
        sm.store(f)
        sig = compute_trust_signal(f, sm, now=now)
        assert sig.verdict == "stale"
        assert sig.age_days >= 180.0

    def test_legacy_unverified_fact_flagged(self, sm: SemanticMemory) -> None:
        from engram.trust_signal import compute_trust_signal
        now = time.time()
        f = Fact(
            id="f-leg", proposition="X is 5MB", topic="t",
            confidence=0.7, status="legacy_unverified", created_at=now,
        )
        sm.store(f)
        sig = compute_trust_signal(f, sm, now=now)
        # Recent legacy fact is "unverified", not "stale".
        assert sig.verdict == "unverified"

    def test_superseded_fact_is_obsolete(self, sm: SemanticMemory) -> None:
        from engram.trust_signal import compute_trust_signal
        now = time.time()
        f = Fact(
            id="f-sup", proposition="X is 5MB", topic="t",
            confidence=0.9, status="model_claim", created_at=now,
            superseded_by="f-new", superseded_at=now,
            superseded_reason="updated",
        )
        sm.store(f)
        sig = compute_trust_signal(f, sm, now=now)
        assert sig.verdict == "obsolete"
        assert sig.is_superseded is True


class TestTrustSignalUsesContradictionStore:
    """When the optional ContradictionStore is provided, contradictions
    bump verdict to 'contested'."""

    def test_fact_with_contradiction_is_contested(
        self, sm: SemanticMemory, tmp_path: Path,
    ) -> None:
        from engram.contradiction import Contradiction, ContradictionStore
        from engram.trust_signal import compute_trust_signal
        store = ContradictionStore(sm.db_path)
        now = time.time()
        f = Fact(
            id="f-contested", proposition="X is 5MB", topic="t",
            confidence=0.9, status="model_claim", created_at=now,
        )
        sm.store(f)
        # Record a fake contradiction involving this fact.
        store.add(Contradiction(
            fact_a_id="f-contested", fact_b_id="f-other",
            kind="numeric_clash", similarity=0.95,
        ))
        sig = compute_trust_signal(f, sm, now=now, contradiction_store=store)
        assert sig.verdict == "contested"
        assert sig.n_contradictions >= 1

    def test_resolved_contradictions_not_counted(
        self, sm: SemanticMemory,
    ) -> None:
        from engram.contradiction import Contradiction, ContradictionStore
        from engram.trust_signal import compute_trust_signal
        store = ContradictionStore(sm.db_path)
        now = time.time()
        f = Fact(
            id="f-was-contested", proposition="X is 5MB", topic="t",
            confidence=0.9, status="model_claim", created_at=now,
        )
        sm.store(f)
        store.add(Contradiction(
            fact_a_id="f-was-contested", fact_b_id="f-other",
            kind="numeric_clash", similarity=0.95,
        ))
        store.resolve_all_for_fact("f-was-contested", note="manual review")
        sig = compute_trust_signal(f, sm, now=now, contradiction_store=store)
        # All contradictions resolved → no longer contested.
        assert sig.verdict != "contested"


class TestRecallTrustSignalsBackwardsCompat:
    """recall(trust_signals=False) — default — returns 2-tuples."""

    def test_default_recall_returns_2tuples(self, sm: SemanticMemory) -> None:
        f = Fact(
            id="f-1", proposition="X uses 5MB memory total",
            topic="t", confidence=0.9, status="model_claim",
            created_at=time.time(),
        )
        sm.store(f)
        hits = sm.recall("X memory", k=5)
        # Each hit should be (fact, similarity) — 2-tuple, no signal.
        assert all(len(h) == 2 for h in hits)


class TestRecallWithTrustSignals:
    """recall(trust_signals=True) returns 3-tuples (fact, sim, signal)."""

    def test_trust_signals_true_returns_3tuples(
        self, sm: SemanticMemory,
    ) -> None:
        now = time.time()
        sm.store(Fact(
            id="f-fresh", proposition="X uses 5MB memory total today",
            topic="t", confidence=0.9, status="model_claim", created_at=now,
        ))
        sm.store(Fact(
            id="f-old", proposition="Y is unrelated content here",
            topic="t", confidence=0.7, status="model_claim",
            created_at=now - 200 * 86400,
        ))
        hits = sm.recall("X memory", k=5, trust_signals=True)
        # Now 3-tuples (fact, sim, signal).
        assert all(len(h) == 3 for h in hits)
        # Each signal must have a known verdict.
        for f, _sim, sig in hits:
            assert sig.verdict in {
                "trusted", "stale", "contested", "obsolete", "unverified",
            }
            # age_days exposed for downstream UI.
            assert sig.age_days >= 0.0
