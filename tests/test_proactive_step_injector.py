"""Cycle 160 (2026-05-19) — StepInjector tests.

Empirical motivation: cycle 159.12-14 showed memory injection wins over
multi-agent teams on math hard. Step-level injection (between tool
calls) is the cycle-160 deliverable promised in master episode
abc05354316143a19faf75997926ac50.

Tests target the dedup-on-cache + threshold-honouring + reset
behaviour of :class:`StepInjector`. Recall semantics are delegated to
``engram.briefing`` and exercised in ``test_briefing_proactive``.
"""
from __future__ import annotations

import time
from typing import Any


class _FakeFact:
    def __init__(self, fid: str, *, proposition: str, topic: str = "",
                 confidence: float = 0.9) -> None:
        self.id = fid
        self.proposition = proposition
        self.topic = topic
        self.confidence = confidence
        self.source_episodes: list[str] = []
        self.created_at = time.time()


class _FakeSemantic:
    def __init__(self, facts: list[_FakeFact],
                 recall_scores: dict[str, dict[str, float]] | None = None) -> None:
        self._facts = facts
        self._recall_scores = recall_scores or {}

    def count(self) -> int:
        return len(self._facts)

    def list_facts(self, limit: int = 8, offset: int = 0) -> list[_FakeFact]:
        return self._facts[offset:offset + limit]

    def recall(self, query: str, k: int = 5,
               topic: str | None = None) -> list[tuple[_FakeFact, float]]:
        scores = self._recall_scores.get(query, {})
        scored = [(f, scores.get(f.id, 0.0)) for f in self._facts]
        scored.sort(key=lambda t: -t[1])
        return [(f, s) for f, s in scored if s > 0.0][:k]


class _FakeAgent:
    def __init__(self, semantic: _FakeSemantic) -> None:
        self.semantic = semantic
        self.memory: Any = None
        self.skills: Any = None


def _make_agent(*, scores: dict[str, dict[str, float]] | None = None) -> _FakeAgent:
    facts = [
        _FakeFact("f1", proposition="AM-GM pairing trick on (2p-1)!",
                  topic="math/imo-2022-p5"),
        _FakeFact("f2", proposition="Wilson theorem (p-1)! ≡ -1 mod p",
                  topic="math/number-theory"),
        _FakeFact("f3", proposition="Bertrand postulate prime in (n, 2n)",
                  topic="math/number-theory"),
    ]
    return _FakeAgent(_FakeSemantic(facts, recall_scores=scores or {}))


# -----------------------------------------------------------------------
# Behaviour tests
# -----------------------------------------------------------------------


def test_injector_returns_top_k_above_threshold() -> None:
    from engram.proactive_step_injector import StepInjector

    agent = _make_agent(scores={
        "close gap p<=b<2p": {"f1": 0.92, "f2": 0.40, "f3": 0.50},
    })
    inj = StepInjector(agent)
    hits = inj.inject("close gap p<=b<2p", min_similarity=0.55, top_k=3)
    assert len(hits) == 1, hits
    assert hits[0]["id"] == "f1"
    assert inj.emitted_count == 1


def test_injector_dedups_across_calls() -> None:
    """A fact emitted once must NOT be emitted again on the next step
    even if it's still the top hit — the host LLM has it in context
    already and re-injecting wastes tokens.
    """
    from engram.proactive_step_injector import StepInjector

    agent = _make_agent(scores={
        "step A": {"f1": 0.90, "f2": 0.60},
        "step B": {"f1": 0.92, "f3": 0.65},
    })
    inj = StepInjector(agent)
    a = inj.inject("step A")
    b = inj.inject("step B")
    a_ids = {h["id"] for h in a}
    b_ids = {h["id"] for h in b}
    assert "f1" in a_ids
    assert "f1" not in b_ids, "duplicate fact must be filtered"
    assert "f3" in b_ids


def test_injector_reset_clears_cache() -> None:
    """After ``reset()``, previously emitted facts can be re-injected.
    Used when the user pivots to an unrelated topic.
    """
    from engram.proactive_step_injector import StepInjector

    agent = _make_agent(scores={
        "step A": {"f1": 0.90},
        "step B": {"f1": 0.90},
    })
    inj = StepInjector(agent)
    inj.inject("step A")
    inj.reset()
    again = inj.inject("step B")
    assert {h["id"] for h in again} == {"f1"}, again


def test_injector_empty_step_returns_nothing() -> None:
    from engram.proactive_step_injector import StepInjector

    agent = _make_agent(scores={"x": {"f1": 0.99}})
    inj = StepInjector(agent)
    assert inj.inject("") == []
    assert inj.inject("   ") == []
    assert inj.emitted_count == 0


def test_injector_no_hits_under_threshold() -> None:
    from engram.proactive_step_injector import StepInjector

    agent = _make_agent(scores={
        "weak query": {"f1": 0.30, "f2": 0.20, "f3": 0.10},
    })
    inj = StepInjector(agent)
    hits = inj.inject("weak query", min_similarity=0.55)
    assert hits == []
    assert inj.emitted_count == 0
