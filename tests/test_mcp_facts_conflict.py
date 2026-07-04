"""MCP integration for hippo_facts_find_conflicting (F#10).

End-to-end through the MCP call_tool handler with a real
SemanticMemory backing store. Verifies that the anti-pollution
surface flags contradictory facts and that the topic filter narrows
the scan correctly.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from engram import mcp_server
from engram.semantic import Fact, SemanticMemory


class _StubSkills:
    def all(self, status: str | None = None) -> list:
        return []

    def count(self, status: str | None = None) -> int:
        return 0


class _StubMemory:
    def all(self, limit: int | None = None) -> list:
        return []

    def count(self, outcome_filter=None) -> int:
        return 0


class _Agent:
    def __init__(self, semantic: SemanticMemory) -> None:
        self.memory = _StubMemory()
        self.skills = _StubSkills()
        self.semantic = semantic


@pytest.fixture
def agent_with_semantic(tmp_data_dir, monkeypatch):
    sm = SemanticMemory(db_path=tmp_data_dir / "semantic" / "facts.db")
    a = _Agent(sm)
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a


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


@pytest.mark.asyncio
async def test_find_conflicting_returns_empty_pool(agent_with_semantic):
    """Empty semantic memory → empty pairs, no crash."""
    blocks = await _invoke_tool("hippo_facts_find_conflicting", {})
    payload = json.loads(blocks[0])
    assert payload["pairs"] == []
    assert payload["pool_size"] == 0


@pytest.mark.asyncio
async def test_find_conflicting_flags_real_contradiction(agent_with_semantic):
    """The exact 2026-05-11 scenario: F#5 in main vs not in main."""
    sm = agent_with_semantic.semantic
    pos = Fact(
        proposition="F#5 IMPLEMENTATO 2026-05-11 in main worktree",
        topic="hippoagent/fixes", confidence=1.0,
    )
    neg = Fact(
        proposition="F#5 NON ancora portato nel main worktree",
        topic="hippoagent/fixes", confidence=1.0,
    )
    sm.store(pos)
    sm.store(neg)

    blocks = await _invoke_tool(
        "hippo_facts_find_conflicting",
        {"min_overlap": 0.2},
    )
    payload = json.loads(blocks[0])
    assert payload["pool_size"] == 2
    assert len(payload["pairs"]) == 1
    pair = payload["pairs"][0]
    assert pair["positive"]["id"] == pos.id
    assert pair["negative"]["id"] == neg.id
    assert pair["semantic_similarity"] >= 0.2


@pytest.mark.asyncio
async def test_find_conflicting_topic_filter(agent_with_semantic):
    """Topic filter narrows the comparison pool — facts in other
    topics are ignored even if they would conflict."""
    sm = agent_with_semantic.semantic
    sm.store(Fact(proposition="F#5 is in main",
                   topic="hippoagent/fixes"))
    sm.store(Fact(proposition="F#5 is NOT in main",
                   topic="hippoagent/fixes"))
    sm.store(Fact(proposition="The build is green",
                   topic="ci/status"))
    sm.store(Fact(proposition="The build is NOT green right now",
                   topic="ci/status"))

    blocks = await _invoke_tool(
        "hippo_facts_find_conflicting",
        {"topic": "hippoagent/fixes", "min_overlap": 0.3},
    )
    payload = json.loads(blocks[0])
    assert payload["topic"] == "hippoagent/fixes"
    assert len(payload["pairs"]) == 1
    prop = payload["pairs"][0]["positive"]["proposition"].lower()
    assert "f#5" in prop


@pytest.mark.asyncio
async def test_find_conflicting_no_false_positive_on_unrelated(
    agent_with_semantic,
):
    """A positive fact and an unrelated negative fact must NOT pair."""
    sm = agent_with_semantic.semantic
    sm.store(Fact(proposition="F#5 is in main",
                   topic="hippoagent/fixes"))
    sm.store(Fact(proposition="The mobile release is NOT cut yet",
                   topic="mobile/release"))

    blocks = await _invoke_tool(
        "hippo_facts_find_conflicting",
        {"min_overlap": 0.3},
    )
    payload = json.loads(blocks[0])
    assert payload["pairs"] == []


@pytest.mark.asyncio
async def test_find_conflicting_low_threshold_within_topic_pairs(
    agent_with_semantic,
):
    """F#21 — `min_shared_tokens=2` (built into the detector)
    prevents cross-fact pairs that share only a single accidental
    token, so the result set stays grounded even at min_overlap=0.0.
    The within-topic pairs (F#5/F#5 and build/build) clear the
    shared-tokens floor and surface; cross-topic ones (F#5/build)
    share zero tokens and don't.
    """
    sm = agent_with_semantic.semantic
    sm.store(Fact(proposition="F#5 is in main",
                   topic="hippoagent/fixes"))
    sm.store(Fact(proposition="F#5 is NOT in main",
                   topic="hippoagent/fixes"))
    sm.store(Fact(proposition="The build is green",
                   topic="ci/status"))
    sm.store(Fact(proposition="The build is NOT green",
                   topic="ci/status"))
    blocks = await _invoke_tool(
        "hippo_facts_find_conflicting",
        {"min_overlap": 0.0},
    )
    payload = json.loads(blocks[0])
    assert payload["min_overlap"] == 0.0
    # 2 within-topic pairs surface (F#5/F#5, build/build);
    # the F#5-vs-build cross pairs share zero content tokens and
    # are excluded by the min_shared_tokens guard.
    assert len(payload["pairs"]) == 2
    propositions = {
        p["positive"]["proposition"] for p in payload["pairs"]
    }
    assert "F#5 is in main" in propositions
    assert "The build is green" in propositions
