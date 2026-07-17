"""Cycle #53 — extend hippo_briefing with task_text proactive semantic recall.

When `task_text` is passed, the briefing payload includes a
`proactive_hits` list of facts whose embedding cosine similarity to
the task_text is >= threshold (default 0.55). Top-k hits sorted by
similarity desc.

When `task_text` is absent / empty, payload retains current shape
(backwards compatible — pre-#53 callers see no change).
"""
from __future__ import annotations

import time
from typing import Any

import pytest

from verimem import briefing

# ---------- Fakes --------------------------------------------------------


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
    """Minimal fake that supports the methods get_briefing actually
    uses: `count`, `list_facts`, and (cycle #53) `recall`."""

    def __init__(self, facts: list[_FakeFact],
                 recall_scores: dict[str, dict[str, float]] | None = None) -> None:
        """recall_scores maps task_text -> {fact_id: similarity}.
        If a task_text isn't in the map, recall returns no matches."""
        self._facts = facts
        self._recall_scores = recall_scores or {}

    def count(self) -> int:
        return len(self._facts)

    def list_facts(self, limit: int = 8, offset: int = 0) -> list[_FakeFact]:
        return self._facts[offset:offset + limit]

    def recall(self, query: str, k: int = 5,
               topic: str | None = None) -> list[tuple[_FakeFact, float]]:
        score_map = self._recall_scores.get(query, {})
        scored = []
        for f in self._facts:
            if topic and f.topic != topic:
                continue
            s = score_map.get(f.id, 0.0)
            scored.append((f, s))
        scored.sort(key=lambda t: -t[1])
        return scored[:k]


class _FakeMemory:
    def count(self) -> int:
        return 0

    def all(self, limit: int = 1000) -> list:
        return []


class _FakeSkills:
    def count(self) -> int:
        return 0

    def all(self) -> list:
        return []


class _FakeAgent:
    def __init__(self, semantic) -> None:
        self.skills = _FakeSkills()
        self.memory = _FakeMemory()
        self.semantic = semantic


# ---------- Tests --------------------------------------------------------


def test_briefing_without_task_text_no_proactive_hits_field() -> None:
    """Backwards compat: pre-#53 shape unchanged when no task_text."""
    sem = _FakeSemantic(facts=[
        _FakeFact("f1", proposition="auth system uses JWT"),
    ])
    a = _FakeAgent(sem)
    out = briefing.get_briefing(agent=a)
    # New field should be absent or empty when task_text not provided
    assert out.get("proactive_hits", []) == []


def test_briefing_with_task_text_returns_hits_above_threshold() -> None:
    """When task_text passed, recall facts and filter by threshold."""
    sem = _FakeSemantic(
        facts=[
            _FakeFact("f_high", proposition="auth system uses JWT"),
            _FakeFact("f_mid", proposition="some unrelated fact"),
            _FakeFact("f_low", proposition="totally different topic"),
        ],
        recall_scores={
            "building auth": {"f_high": 0.71, "f_mid": 0.40, "f_low": 0.20},
        },
    )
    a = _FakeAgent(sem)
    out = briefing.get_briefing(
        agent=a, task_text="building auth",
        top_k_proactive=5, threshold_proactive=0.55,
    )
    hits = out.get("proactive_hits", [])
    assert len(hits) == 1
    assert hits[0]["id"] == "f_high"
    assert hits[0]["similarity"] >= 0.55
    # Must include proposition + topic for UI display
    assert "proposition" in hits[0]
    assert "topic" in hits[0]


def test_briefing_proactive_threshold_default_055() -> None:
    """Default threshold is 0.55 (cycle #53 design decision)."""
    sem = _FakeSemantic(
        facts=[
            _FakeFact("f_strong", proposition="a"),
            _FakeFact("f_borderline", proposition="b"),
        ],
        recall_scores={
            "anything": {"f_strong": 0.60, "f_borderline": 0.54},
        },
    )
    a = _FakeAgent(sem)
    out = briefing.get_briefing(agent=a, task_text="anything")
    hits = out.get("proactive_hits", [])
    ids = {h["id"] for h in hits}
    assert "f_strong" in ids
    assert "f_borderline" not in ids  # 0.54 < 0.55 default


def test_briefing_proactive_threshold_configurable() -> None:
    """Threshold is an explicit param, overrideable."""
    sem = _FakeSemantic(
        facts=[_FakeFact("f", proposition="x")],
        recall_scores={"q": {"f": 0.40}},
    )
    a = _FakeAgent(sem)
    # Low threshold → hit
    out_low = briefing.get_briefing(
        agent=a, task_text="q", threshold_proactive=0.30,
    )
    assert len(out_low.get("proactive_hits", [])) == 1
    # High threshold → no hit
    out_high = briefing.get_briefing(
        agent=a, task_text="q", threshold_proactive=0.80,
    )
    assert len(out_high.get("proactive_hits", [])) == 0


def test_briefing_proactive_topk_cap() -> None:
    """top_k_proactive caps how many hits are returned even if all
    are above threshold."""
    sem = _FakeSemantic(
        facts=[_FakeFact(f"f{i}", proposition=str(i)) for i in range(10)],
        recall_scores={"q": {f"f{i}": 0.9 for i in range(10)}},
    )
    a = _FakeAgent(sem)
    out = briefing.get_briefing(
        agent=a, task_text="q",
        top_k_proactive=3, threshold_proactive=0.55,
    )
    assert len(out["proactive_hits"]) == 3


def test_briefing_proactive_empty_task_text_no_hits() -> None:
    """Empty / whitespace task_text → no recall, no hits."""
    sem = _FakeSemantic(
        facts=[_FakeFact("f", proposition="x")],
        recall_scores={"": {"f": 0.99}},  # would match if we did recall
    )
    a = _FakeAgent(sem)
    out_empty = briefing.get_briefing(agent=a, task_text="")
    out_ws = briefing.get_briefing(agent=a, task_text="   ")
    out_none = briefing.get_briefing(agent=a, task_text=None)
    for out in (out_empty, out_ws, out_none):
        assert out.get("proactive_hits", []) == []


def test_briefing_proactive_returns_similarity_score_descending() -> None:
    """Hits ordered by similarity descending."""
    sem = _FakeSemantic(
        facts=[
            _FakeFact("a", proposition="a"),
            _FakeFact("b", proposition="b"),
            _FakeFact("c", proposition="c"),
        ],
        recall_scores={
            "q": {"a": 0.60, "b": 0.85, "c": 0.70},
        },
    )
    a = _FakeAgent(sem)
    out = briefing.get_briefing(agent=a, task_text="q")
    hits = out["proactive_hits"]
    sims = [h["similarity"] for h in hits]
    assert sims == sorted(sims, reverse=True)
    assert hits[0]["id"] == "b"  # 0.85 top
