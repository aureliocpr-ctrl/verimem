"""Cycle #51 — extend hippo_record_episode with key_facts + related_episode_ids.

Backwards-compatible extension: existing callers (no key_facts, no
related_episode_ids) keep working unchanged. New optional fields let
the host populate `facts.source_episodes` (FK fact→episode) and
`causal_edges` (graph episode→episode) at write time.

Why this matters: the current memory model has the schema fields
(facts.source_episodes CSV + causal_edges table) but nobody populates
them — so the lineage graph between episodes and facts is empty.
Cycle #51 closes the write-side gap so cycle #52's `hippo_lineage_trace`
walker has data to traverse.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

import pytest

from engram import mcp_server

# ---------- Fakes (extended for key_facts + related_episode_ids) ---------


class _FakeFact:
    def __init__(self, fid: str, *, proposition: str, topic: str = "",
                 confidence: float = 0.9,
                 source_episodes: list[str] | None = None) -> None:
        self.id = fid
        self.proposition = proposition
        self.topic = topic
        self.confidence = confidence
        self.source_episodes = source_episodes or []
        self.created_at = time.time()


class _FakeSemantic:
    def __init__(self) -> None:
        self.stored: list[_FakeFact] = []

    def store(self, fact: _FakeFact, *, return_replaced: bool = False,
               coherence_hook=None, embed: str = "sync"):
        # Cycle #125: accept coherence_hook (cycle 119 wire) for back-compat.
        # 2026-06-05: accept embed kwarg (non-blocking store) — the fake just
        # records the fact regardless of embed mode (no real embedding here).
        _ = (coherence_hook, embed)
        self.stored.append(fact)
        return False if return_replaced else None

    def count(self) -> int:
        return len(self.stored)


class _FakeEpisode:
    def __init__(self, eid: str, task: str, *, final_answer: str = "ok",
                 outcome: str = "success",
                 skills_used: list[str] | None = None,
                 tokens_used: int = 0, num_steps: int = 1,
                 task_id: str | None = None) -> None:
        self.id = eid
        self.task_id = task_id or f"t-{eid}"
        self.task_text = task
        self.outcome = outcome
        self.final_answer = final_answer
        self.skills_used = skills_used or []
        self.tokens_used = tokens_used
        self.num_steps = num_steps
        self.created_at = time.time()
        self.notes = ""
        self.critique = ""


class _FakeMemory:
    def __init__(self) -> None:
        self.stored: list[_FakeEpisode] = []
        self.causal_edges: list[tuple[str, str, str, float]] = []

    def store(self, ep: _FakeEpisode, *, embed: str = "sync", **_kwargs) -> None:
        # 2026-06-06: accept embed (non-blocking episode store) — the hosted
        # hippo_record_episode handler calls store(ep, embed="auto"). The fake
        # just records regardless of embed mode.
        _ = embed
        self.stored.append(ep)

    def add_causal_edge(self, src_id: str, dst_id: str,
                        via_skill_id: str, weight: float = 1.0) -> None:
        self.causal_edges.append((src_id, dst_id, via_skill_id, weight))

    def count(self, outcome_filter=None) -> int:
        return len(self.stored)


class _FakeSkillsStore:
    def update_fitness(self, skill_id: str, success: bool, tokens: int,
                       task_text: str = ""):
        return None


class _FakeAgent:
    def __init__(self) -> None:
        self.skills = _FakeSkillsStore()
        self.memory = _FakeMemory()
        self.semantic = _FakeSemantic()


# ---------- Helper -------------------------------------------------------


async def _invoke_tool(name: str, arguments: dict[str, Any] | None = None):
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    return [c.text for c in payload.content if hasattr(c, "text")]


@pytest.fixture
def fake_agent(monkeypatch: pytest.MonkeyPatch) -> _FakeAgent:
    a = _FakeAgent()
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)

    def _ep_factory(task_id: str, task_text: str, final_answer: str,
                    outcome: str = "success",
                    skills_used: list[str] | None = None,
                    tokens_used: int = 0,
                    num_steps: int = 1):
        eid = uuid.uuid4().hex[:12]
        return _FakeEpisode(
            eid, task_text, final_answer=final_answer, outcome=outcome,
            skills_used=skills_used or [], tokens_used=tokens_used,
            num_steps=num_steps, task_id=task_id,
        )
    monkeypatch.setattr(mcp_server, "_build_episode", _ep_factory,
                        raising=False)

    # Stub _build_fact: real one uses embedding.encode (heavy). Fake just
    # builds a _FakeFact with content-hash-style id (deterministic).
    def _fact_factory(proposition: str, topic: str = "",
                      confidence: float = 0.9,
                      source_episodes: list[str] | None = None,
                      **_kw):  # tollera kw futuri (status, valid_until, ...)
        import hashlib
        h = hashlib.sha256(
            f"{proposition}|{topic}".encode()
        ).hexdigest()[:12]
        return _FakeFact(
            h, proposition=proposition, topic=topic,
            confidence=confidence, source_episodes=source_episodes or [],
        )
    monkeypatch.setattr(mcp_server, "_build_fact", _fact_factory,
                        raising=False)
    return a


# ---------- Tests --------------------------------------------------------


@pytest.mark.asyncio
async def test_record_episode_with_key_facts(fake_agent: _FakeAgent) -> None:
    """Passing key_facts creates Facts with source_episodes set to new ep.id."""
    blocks = await _invoke_tool(
        "hippo_record_episode",
        {
            "task_text": "Design narrative-episode convention",
            "final_answer": "Full design markdown here, multi-line...",
            "key_facts": [
                {"proposition": "Convention: fact=atom, episode=narrative",
                 "topic": "preferences/aurelio", "confidence": 0.9},
                {"proposition": "Threshold for proactive briefing = 0.55",
                 "topic": "decisions/architecture", "confidence": 0.8},
            ],
        },
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    ep_id = payload["episode_id"]
    assert "fact_ids" in payload
    assert len(payload["fact_ids"]) == 2
    # All facts must have source_episodes pointing to new ep
    assert len(fake_agent.semantic.stored) == 2
    for f in fake_agent.semantic.stored:
        assert ep_id in f.source_episodes, (
            f"fact {f.id} missing ep_id in source_episodes: {f.source_episodes}"
        )


@pytest.mark.asyncio
async def test_record_episode_with_related_episode_ids(
    fake_agent: _FakeAgent,
) -> None:
    """Passing related_episode_ids creates causal_edges from new ep."""
    blocks = await _invoke_tool(
        "hippo_record_episode",
        {
            "task_text": "Cycle #51 close",
            "final_answer": "completed",
            "related_episode_ids": ["ep_aaa", "ep_bbb"],
        },
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    ep_id = payload["episode_id"]
    assert payload.get("edges_created") == 2
    assert len(fake_agent.memory.causal_edges) == 2
    for src, dst, skill, _w in fake_agent.memory.causal_edges:
        assert src == ep_id
        assert dst in ("ep_aaa", "ep_bbb")
        assert skill == "narrative_link"


@pytest.mark.asyncio
async def test_record_episode_without_extras_backwards_compat(
    fake_agent: _FakeAgent,
) -> None:
    """Existing callers (no key_facts, no related) keep working unchanged."""
    blocks = await _invoke_tool(
        "hippo_record_episode",
        {"task_text": "legacy call", "final_answer": "done"},
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    assert "episode_id" in payload
    # No facts, no edges, no surprises
    assert len(fake_agent.semantic.stored) == 0
    assert len(fake_agent.memory.causal_edges) == 0
    # New fields should be present but empty/zero for consistency
    assert payload.get("fact_ids", []) == []
    assert payload.get("edges_created", 0) == 0


@pytest.mark.asyncio
async def test_record_episode_both_key_facts_and_related(
    fake_agent: _FakeAgent,
) -> None:
    """Combined: episode + 1 fact + 1 related edge in one call."""
    blocks = await _invoke_tool(
        "hippo_record_episode",
        {
            "task_text": "Cycle #51 narrative dogfooding",
            "final_answer": "Implementation complete; cycle close fact below.",
            "key_facts": [
                {"proposition": "Cycle #51 extended hippo_record_episode",
                 "topic": "project/engram/cycle-51", "confidence": 0.95},
            ],
            "related_episode_ids": ["ep_previous"],
        },
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    assert len(payload["fact_ids"]) == 1
    assert payload["edges_created"] == 1
    assert len(fake_agent.semantic.stored) == 1
    assert fake_agent.semantic.stored[0].source_episodes == [
        payload["episode_id"]
    ]
    assert len(fake_agent.memory.causal_edges) == 1
    assert fake_agent.memory.causal_edges[0][0] == payload["episode_id"]
    assert fake_agent.memory.causal_edges[0][1] == "ep_previous"


@pytest.mark.asyncio
async def test_record_episode_key_facts_validation(
    fake_agent: _FakeAgent,
) -> None:
    """key_facts entries must have non-empty proposition; bad ones skipped."""
    blocks = await _invoke_tool(
        "hippo_record_episode",
        {
            "task_text": "validation test",
            "final_answer": "test",
            "key_facts": [
                {"proposition": "valid one", "topic": "t1"},
                {"proposition": "", "topic": "t2"},  # rejected: empty prop
                {"topic": "t3"},  # rejected: no prop
                {"proposition": "valid two", "topic": "t4",
                 "confidence": 0.5},
            ],
        },
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    # Only the 2 valid ones must be stored
    assert len(payload["fact_ids"]) == 2
    assert len(fake_agent.semantic.stored) == 2
    propositions = [f.proposition for f in fake_agent.semantic.stored]
    assert "valid one" in propositions
    assert "valid two" in propositions
