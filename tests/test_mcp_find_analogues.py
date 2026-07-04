"""FORGIA pezzo #210 — MCP tool `hippo_find_analogues`.

Wires Pezzo C (structural analogy / Gentner 1983) to the MCP layer.
Given a target skill, returns OTHER skills with high structural
overlap but LOW semantic similarity — the regime where analogy
adds value beyond plain semantic retrieval.
"""
from __future__ import annotations

import json
from typing import Any

import numpy as np
import pytest

from engram import mcp_server
from engram.skill import Skill

# ---------- Fakes --------------------------------------------------------


class _FakeSkillsStore:
    def __init__(self, skills: list[Skill]) -> None:
        self._by_id = {s.id: s for s in skills}

    def get(self, sid: str) -> Skill | None:
        return self._by_id.get(sid)

    def all(self, status: str | None = None) -> list[Skill]:
        ss = list(self._by_id.values())
        if status is None:
            return ss
        return [s for s in ss if s.status == status]


class _FakeAgent:
    def __init__(self, skills: list[Skill]) -> None:
        self.skills = _FakeSkillsStore(skills)


# ---------- Helpers ------------------------------------------------------


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
def fake_agent_and_emb(monkeypatch: pytest.MonkeyPatch):
    """Stub the embedding module so we can deterministically control
    semantic cosine without loading sentence-transformers."""
    skills = [
        Skill(id="t",
              name="deploy_to_production",
              trigger="deploy and verify",
              status="promoted"),
        # Structural near-clone (high token overlap), DIFFERENT
        # semantic embedding (we control via the stub).
        Skill(id="analogue",
              name="release_to_production",
              trigger="deploy and verify",
              status="promoted"),
        # Semantic clone (would have very high cosine), should be
        # filtered as a duplicate, not a true analogy.
        Skill(id="duplicate",
              name="deploy_to_production",
              trigger="deploy and verify",
              status="promoted"),
        # Structurally distant.
        Skill(id="distant",
              name="parse_json",
              trigger="parse JSON",
              status="promoted"),
    ]
    a = _FakeAgent(skills)
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)

    # Stub embedding.encode: deterministic cosine table.
    # We make `t` ↔ `duplicate` cosine ≈ 1.0 (dup), `t` ↔ `analogue`
    # cosine ≈ 0.2 (low semantic), `t` ↔ `distant` cosine ≈ 0.1.
    fixed = {
        "t": np.array([1.0, 0.0, 0.0], dtype=np.float32),
        "analogue": np.array([0.2, 0.98, 0.0], dtype=np.float32),
        "duplicate": np.array([1.0, 0.0, 0.0], dtype=np.float32),
        "distant": np.array([0.1, 0.0, 0.99], dtype=np.float32),
    }

    def fake_encode(text: str) -> np.ndarray:
        # Stub by skill name (which we put first in the encode prompt).
        for sid, vec in fixed.items():
            sk = a.skills.get(sid)
            if sk and sk.name and sk.name in text:
                return vec
        return np.array([0.5, 0.5, 0.5], dtype=np.float32)

    monkeypatch.setattr(
        "engram.embedding.encode", fake_encode, raising=False,
    )
    return a


# ---------- Tests --------------------------------------------------------


@pytest.mark.asyncio
async def test_find_analogues_listed(fake_agent_and_emb) -> None:
    from mcp.types import ListToolsRequest, PaginatedRequestParams
    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(method="tools/list", params=PaginatedRequestParams())
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    assert "hippo_find_analogues" in names


@pytest.mark.asyncio
async def test_find_analogues_returns_high_struct_low_sem(
    fake_agent_and_emb,
) -> None:
    """`analogue` skill: high structural overlap, low cosine → must
    appear. `duplicate`: high cosine → filtered out."""
    blocks = await _invoke_tool(
        "hippo_find_analogues",
        {"target_skill_id": "t", "min_structural": 0.3,
            "max_semantic": 0.5, "top_k": 5},
    )
    payload = json.loads(blocks[0])
    assert payload["target_skill_id"] == "t"
    ids = [a["id"] for a in payload["analogues"]]
    assert "analogue" in ids
    assert "duplicate" not in ids
    assert "distant" not in ids


@pytest.mark.asyncio
async def test_find_analogues_unknown_target(fake_agent_and_emb) -> None:
    """Target id not in store → found=False, analogues=[]."""
    blocks = await _invoke_tool(
        "hippo_find_analogues", {"target_skill_id": "ZZZ"},
    )
    payload = json.loads(blocks[0])
    assert payload["found"] is False
    assert payload["analogues"] == []


@pytest.mark.asyncio
async def test_find_analogues_top_k_respected(fake_agent_and_emb) -> None:
    blocks = await _invoke_tool(
        "hippo_find_analogues",
        {"target_skill_id": "t", "min_structural": 0.0,
            "max_semantic": 1.0, "top_k": 1},
    )
    payload = json.loads(blocks[0])
    assert len(payload["analogues"]) <= 1


@pytest.mark.asyncio
async def test_find_analogues_payload_shape(fake_agent_and_emb) -> None:
    """Each analogue carries id, name, structural, semantic."""
    blocks = await _invoke_tool(
        "hippo_find_analogues",
        {"target_skill_id": "t", "min_structural": 0.0,
            "max_semantic": 1.0},
    )
    payload = json.loads(blocks[0])
    if payload["analogues"]:
        a0 = payload["analogues"][0]
        for k in ("id", "name", "structural", "semantic"):
            assert k in a0, f"missing key {k} in analogue payload"
