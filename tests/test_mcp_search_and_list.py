"""FORGIA pezzo #195 — MCP tools ``hippo_search``, ``hippo_episode_list``,
``hippo_forget``, ``hippo_stats``.

Wave 1 of the tool-set expansion: privacy + observability tools.

* ``hippo_search`` — substring/keyword search on episode task_text
  (distinct from semantic ``hippo_recall``).
* ``hippo_episode_list`` — paginated listing with outcome filter.
* ``hippo_forget`` — delete one episode by id (GDPR / privacy).
* ``hippo_stats`` — aggregate metrics across the memory store.

Tests follow the established fake-agent fixture pattern.
"""
from __future__ import annotations

import json
import time
from typing import Any

import pytest

from engram import mcp_server

# ---------- Fakes ---------------------------------------------------------


class _FakeEpisode:
    def __init__(
        self,
        eid: str,
        task: str,
        outcome: str = "success",
        created_at: float | None = None,
        tokens: int = 100,
        steps: int = 3,
        skills_used: list[str] | None = None,
    ) -> None:
        self.id = eid
        self.task_text = task
        self.task_id = "t-" + eid
        self.outcome = outcome
        self.created_at = created_at if created_at is not None else time.time()
        self.tokens_used = tokens
        self.num_steps = steps
        self.final_answer = f"answer-of-{eid}"
        self.skills_used = skills_used or []
        self.critique = ""

    def trajectory_text(self) -> str:
        return f"trajectory-{self.id}"


class _FakeMemory:
    def __init__(self) -> None:
        self.episodes = [
            _FakeEpisode(
                "ep1", "compute factorial of 10", "success",
                created_at=1000.0, tokens=120, steps=4,
                skills_used=["sk-fact"],
            ),
            _FakeEpisode(
                "ep2", "reverse the string hello", "success",
                created_at=1100.0, tokens=80, steps=2,
                skills_used=["sk-rev"],
            ),
            _FakeEpisode(
                "ep3", "factorial of n iteratively", "failure",
                created_at=1200.0, tokens=200, steps=6,
                skills_used=["sk-fact"],
            ),
            _FakeEpisode(
                "ep4", "rot13 of message", "success",
                created_at=1300.0, tokens=60, steps=2,
                skills_used=["sk-rot"],
            ),
        ]
        self.deleted: list[str] = []

    # --- methods the tool handlers will call -----------------------------

    def search_episodes(
        self, query: str, *, limit: int = 20,
        outcome: str | None = None,
    ) -> list[Any]:
        q = query.strip().lower()
        out = []
        for ep in self.episodes:
            if q and q not in ep.task_text.lower():
                continue
            if outcome and ep.outcome != outcome:
                continue
            out.append(ep)
        out.sort(key=lambda e: e.created_at, reverse=True)
        return out[:limit]

    def all(self, limit: int | None = None) -> list[Any]:
        eps = sorted(self.episodes, key=lambda e: e.created_at, reverse=True)
        return eps[:limit] if limit else eps

    def by_outcome(self, outcome: str, limit: int | None = None) -> list[Any]:
        eps = [e for e in self.episodes if e.outcome == outcome]
        eps.sort(key=lambda e: e.created_at, reverse=True)
        return eps[:limit] if limit else eps

    def count(self, outcome_filter: str | None = None) -> int:
        if outcome_filter:
            return sum(1 for e in self.episodes if e.outcome == outcome_filter)
        return len(self.episodes)

    def get(self, episode_id: str) -> Any | None:
        for e in self.episodes:
            if e.id == episode_id:
                return e
        return None

    def delete(self, episode_id: str) -> bool:
        for i, e in enumerate(self.episodes):
            if e.id == episode_id:
                del self.episodes[i]
                self.deleted.append(episode_id)
                return True
        return False

    def token_usage_stats(self) -> dict[str, float]:
        toks = [e.tokens_used for e in self.episodes]
        return {
            "total": float(sum(toks)),
            "mean": float(sum(toks) / len(toks)) if toks else 0.0,
            "max": float(max(toks)) if toks else 0.0,
            "n_with_tokens": float(len(toks)),
        }


class _FakeSkillsStore:
    def count(self, status: str | None = None) -> int:
        if status == "promoted":
            return 5
        if status == "candidate":
            return 7
        if status == "retired":
            return 1
        return 13


class _FakeSemantic:
    def count(self) -> int:
        return 42


class _FakeAgent:
    def __init__(self) -> None:
        self.memory = _FakeMemory()
        self.skills = _FakeSkillsStore()
        self.semantic = _FakeSemantic()


# ---------- Helpers -------------------------------------------------------


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
    return a


# ---------- hippo_search -------------------------------------------------


@pytest.mark.asyncio
async def test_hippo_search_listed_in_tool_set(fake_agent: _FakeAgent) -> None:
    from mcp.types import ListToolsRequest, PaginatedRequestParams
    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(method="tools/list", params=PaginatedRequestParams())
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    assert "hippo_search" in names
    assert "hippo_episode_list" in names
    assert "hippo_forget" in names
    assert "hippo_stats" in names


@pytest.mark.asyncio
async def test_hippo_search_substring_match(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool("hippo_search", {"query": "factorial"})
    payload = json.loads(blocks[0])
    ids = [it["id"] for it in payload]
    assert "ep1" in ids and "ep3" in ids
    assert "ep2" not in ids
    assert "ep4" not in ids


@pytest.mark.asyncio
async def test_hippo_search_outcome_filter(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_search", {"query": "factorial", "outcome": "success"},
    )
    payload = json.loads(blocks[0])
    ids = [it["id"] for it in payload]
    assert ids == ["ep1"]


@pytest.mark.asyncio
async def test_hippo_search_returns_preview_fields(
    fake_agent: _FakeAgent,
) -> None:
    blocks = await _invoke_tool("hippo_search", {"query": "rot13"})
    payload = json.loads(blocks[0])
    assert len(payload) == 1
    item = payload[0]
    assert item["id"] == "ep4"
    assert item["outcome"] == "success"
    assert "task" in item and "answer_preview" in item
    assert item["tokens"] == 60


@pytest.mark.asyncio
async def test_hippo_search_limit_respected(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool("hippo_search", {"query": "", "limit": 2})
    payload = json.loads(blocks[0])
    assert len(payload) == 2  # all 4 match empty query → limited to 2


@pytest.mark.asyncio
async def test_hippo_search_empty_query_returns_recent(
    fake_agent: _FakeAgent,
) -> None:
    blocks = await _invoke_tool("hippo_search", {"query": ""})
    payload = json.loads(blocks[0])
    # Newest first.
    assert payload[0]["id"] == "ep4"
    assert payload[-1]["id"] == "ep1"


# ---------- hippo_episode_list -------------------------------------------


@pytest.mark.asyncio
async def test_hippo_episode_list_default_returns_all(
    fake_agent: _FakeAgent,
) -> None:
    blocks = await _invoke_tool("hippo_episode_list", {})
    payload = json.loads(blocks[0])
    assert isinstance(payload, dict)
    assert payload["total"] == 4
    items = payload["items"]
    assert len(items) == 4
    # newest first
    assert items[0]["id"] == "ep4"


@pytest.mark.asyncio
async def test_hippo_episode_list_pagination(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_episode_list", {"limit": 2, "offset": 1},
    )
    payload = json.loads(blocks[0])
    items = payload["items"]
    # newest first → ep4, ep3, ep2, ep1; offset 1 limit 2 → ep3, ep2
    assert [it["id"] for it in items] == ["ep3", "ep2"]
    assert payload["limit"] == 2
    assert payload["offset"] == 1


@pytest.mark.asyncio
async def test_hippo_episode_list_outcome_filter(
    fake_agent: _FakeAgent,
) -> None:
    blocks = await _invoke_tool(
        "hippo_episode_list", {"outcome": "failure"},
    )
    payload = json.loads(blocks[0])
    items = payload["items"]
    assert len(items) == 1
    assert items[0]["id"] == "ep3"


# ---------- hippo_forget --------------------------------------------------


@pytest.mark.asyncio
async def test_hippo_forget_deletes_existing(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool("hippo_forget", {"episode_id": "ep2"})
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    assert payload["id"] == "ep2"
    assert "ep2" in fake_agent.memory.deleted
    # second call → not found
    blocks2 = await _invoke_tool("hippo_forget", {"episode_id": "ep2"})
    payload2 = json.loads(blocks2[0])
    assert "error" in payload2


@pytest.mark.asyncio
async def test_hippo_forget_unknown_id(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool("hippo_forget", {"episode_id": "nope"})
    payload = json.loads(blocks[0])
    assert "error" in payload


# ---------- hippo_stats ---------------------------------------------------


@pytest.mark.asyncio
async def test_hippo_stats_returns_full_snapshot(
    fake_agent: _FakeAgent,
) -> None:
    blocks = await _invoke_tool("hippo_stats", {})
    payload = json.loads(blocks[0])
    assert payload["episodes"]["total"] == 4
    assert payload["episodes"]["success"] == 3
    assert payload["episodes"]["failure"] == 1
    assert payload["skills"]["promoted"] == 5
    assert payload["skills"]["candidate"] == 7
    assert payload["skills"]["retired"] == 1
    assert payload["skills"]["total"] == 13
    assert payload["facts"] == 42
    tu = payload["tokens"]
    assert tu["total"] == 460.0  # 120+80+200+60
    assert tu["max"] == 200.0
    assert tu["mean"] == pytest.approx(115.0, rel=1e-3)
    assert tu["n_with_tokens"] == 4.0
