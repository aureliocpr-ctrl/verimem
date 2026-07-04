"""Knowledge/telemetry tiering (2026-07-02 night-2 follow-up).

The real-corpus NLI scan showed the residual conflicts are machine telemetry
(bus/consensus verdicts, dream/*/state, metric/event_*), not knowledge — so the
knowledge-reconcile judge must never auto-act (supersede OR contest) on a fact
that is not tier=knowledge. `classify_tier` in engram._telemetry_prefixes is the
single source of truth; truth_reconciliation consumes it on both sides of every
pair. dialog/ verbatim transcripts stay recallable but are NOT factual
assertions to reconcile; dream/ was a missing telemetry prefix (26 live JSON
machine-state facts slipped past write-route and read-hide).
"""
from __future__ import annotations

from engram._telemetry_prefixes import (
    TELEMETRY_TOPIC_PREFIXES,
    TIER_DIALOG,
    TIER_KNOWLEDGE,
    TIER_TELEMETRY,
    TIER_TEST,
    classify_tier,
)
from engram.contradiction import ContradictionStore
from engram.semantic import Fact, SemanticMemory
from engram.truth_reconciliation import (
    reconcile_against_corpus,
    reconcile_fact_on_write,
)

_NOW = 1_000_000_000.0
_DAY = 86400.0


# --- classify_tier (pure, single source of truth) ---

def test_machine_state_topics_are_telemetry() -> None:
    for topic in ("metric/event_git_commit", "bus/consensus",
                  "dream/246530c5ea2c", "cache/x", "dialog/voice/turn",
                  # nested machine state the first knowledge-only scan exposed
                  "pin/5f4ddddc0208", "skill/catalog/clp-ai-eye",
                  "project/recursive-mas/seqmas-123/r1/critic"):
        assert classify_tier(topic) == TIER_TELEMETRY, topic


def test_deliberate_skill_knowledge_is_not_swept_by_catalog_prefix() -> None:
    # only the auto-generated catalog registry is machine state; deliberately
    # saved skill knowledge must stay knowledge-tier (recallable, reconcilable).
    assert classify_tier("skill/notes/ai-eye-usage") == TIER_KNOWLEDGE
    assert classify_tier("emerging_skill/x") == TIER_KNOWLEDGE


def test_dream_prefix_is_in_the_shared_denylist() -> None:
    # write-route (admission_gate) and read-hide (semantic) both derive from
    # this tuple — adding dream/ here propagates to both by construction.
    assert "dream/" in TELEMETRY_TOPIC_PREFIXES


def test_fixture_and_lab_topics_are_test_tier() -> None:
    for topic in ("test/canary", "lab/exp1", "project/lab/run3"):
        assert classify_tier(topic) == TIER_TEST, topic


def test_verbatim_transcripts_are_dialog_not_telemetry() -> None:
    # deliberately-saved founding conversations: recallable, but not factual
    # assertions a reconcile judge should act on.
    assert classify_tier("dialog/doc1-hippoagent-2026-05-14") == TIER_DIALOG


def test_everything_else_is_knowledge() -> None:
    for topic in ("project/engram/x", "lessons/errors/y", "preferences/aurelio/z",
                  "", None):
        assert classify_tier(topic) == TIER_KNOWLEDGE, topic


# --- reconcile guard: non-knowledge is untouchable on BOTH sides ---

def _fact(fid, topic, prop, *, age_days=0.0):
    return Fact(id=fid, proposition=prop, topic=topic, status="verified",
                confidence=0.9, created_at=_NOW - age_days * _DAY)


def _stores(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    return sm, ContradictionStore(sm.db_path)


def test_reconcile_skips_telemetry_candidate(tmp_path) -> None:
    # a clean temporal update in every other respect — but the OLD side is
    # telemetry, so it must be neither superseded nor contested.
    sm, cs = _stores(tmp_path)
    old = _fact("old", "metric/consensus_verdict", "config X is 30s", age_days=30)
    new = _fact("new", "project/engram/cfg", "config X is 5s")
    sm.store(old)
    sm.store(new)
    res = reconcile_fact_on_write(sm, new, [old], now=_NOW, contradiction_store=cs)
    assert res == {"superseded": [], "contested": []}
    assert sm.get("old").superseded_by in (None, "")


def test_reconcile_is_noop_for_telemetry_new_fact(tmp_path) -> None:
    sm, cs = _stores(tmp_path)
    old = _fact("old", "project/engram/cfg", "config X is 30s", age_days=30)
    new = _fact("new", "dream/abc123", '{"state": "active"}')
    sm.store(old)
    sm.store(new)
    res = reconcile_fact_on_write(sm, new, [old], now=_NOW, contradiction_store=cs)
    assert res == {"superseded": [], "contested": []}
    assert sm.get("old").superseded_by in (None, "")


def test_reconcile_against_corpus_is_noop_for_dialog_fact(tmp_path) -> None:
    sm, cs = _stores(tmp_path)
    new = _fact("new", "dialog/doc2-beacon-2026-05-14", "Aurelio: apriamo il critic")
    sm.store(new)
    res = reconcile_against_corpus(
        sm, new, _EmptyEntityStore(), contradiction_store=cs, now=_NOW)
    assert res == {"superseded": [], "contested": []}


def test_reconcile_still_supersedes_knowledge_update(tmp_path) -> None:
    # regression: the guard must not break the normal knowledge path.
    sm, cs = _stores(tmp_path)
    old = _fact("old", "project/engram/cfg", "config X is 30s", age_days=30)
    new = _fact("new", "project/engram/cfg", "config X is 5s")
    sm.store(old)
    sm.store(new)
    res = reconcile_fact_on_write(sm, new, [old], now=_NOW, contradiction_store=cs)
    assert "old" in res["superseded"]
    assert sm.get("old").superseded_by == "new"


class _EmptyEntityStore:
    def entities_for_fact(self, fid):  # pragma: no cover - trivial
        raise AssertionError(
            "tier guard must short-circuit BEFORE any entity lookup")
