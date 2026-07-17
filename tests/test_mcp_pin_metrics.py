"""FORGIA pezzo #197 — MCP tools Wave 3.

* ``hippo_episode_pin``    — protect an episode from decay-pruning.
* ``hippo_episode_unpin``  — release the protection.
* ``hippo_metrics_history`` — token-usage timeseries bucketed by day.
"""
from __future__ import annotations

import json
import time
from typing import Any

import pytest

from verimem import mcp_server

# ---------- Fakes ---------------------------------------------------------


class _FakeEpisode:
    def __init__(self, eid: str, *, created_at: float,
                  tokens: int = 100, outcome: str = "success") -> None:
        self.id = eid
        self.task_id = "t-" + eid
        self.task_text = f"task {eid}"
        self.outcome = outcome
        self.created_at = created_at
        self.tokens_used = tokens
        self.num_steps = 2
        self.final_answer = ""
        self.skills_used: list[str] = []


class _FakeMemoryWithPin:
    def __init__(self) -> None:
        # 5 episodes spread across 3 days.
        # Day 0: 2 episodes (100 + 200 tokens)
        # Day 1: 1 episode (50 tokens)
        # Day 2: 2 episodes (300 + 400 tokens)
        d = 86400.0  # one day in seconds
        base = 1_700_000_000.0  # arbitrary epoch
        self.episodes = [
            _FakeEpisode("e1", created_at=base + 0 * d, tokens=100),
            _FakeEpisode("e2", created_at=base + 0 * d + 60.0, tokens=200),
            _FakeEpisode("e3", created_at=base + 1 * d, tokens=50,
                          outcome="failure"),
            _FakeEpisode("e4", created_at=base + 2 * d, tokens=300),
            _FakeEpisode("e5", created_at=base + 2 * d + 120.0,
                          tokens=400),
        ]
        self.pinned: set[str] = set()

    def get(self, eid: str) -> _FakeEpisode | None:
        for e in self.episodes:
            if e.id == eid:
                return e
        return None

    def set_pinned(self, eid: str, pinned: bool) -> bool:
        if not self.get(eid):
            return False
        if pinned:
            self.pinned.add(eid)
        else:
            self.pinned.discard(eid)
        return True

    def is_pinned(self, eid: str) -> bool:
        return eid in self.pinned

    def all(self, limit: int | None = None) -> list[_FakeEpisode]:
        eps = sorted(self.episodes, key=lambda e: e.created_at, reverse=True)
        return eps[:limit] if limit else eps


class _FakeAgent:
    def __init__(self) -> None:
        self.memory = _FakeMemoryWithPin()


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


# ---------- listing -----------------------------------------------------


@pytest.mark.asyncio
async def test_wave3_tools_listed(fake_agent: _FakeAgent) -> None:
    from mcp.types import ListToolsRequest, PaginatedRequestParams
    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(method="tools/list", params=PaginatedRequestParams())
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    for n in ("hippo_episode_pin", "hippo_episode_unpin",
              "hippo_metrics_history"):
        assert n in names, f"missing tool: {n}"


# ---------- hippo_episode_pin -------------------------------------------


@pytest.mark.asyncio
async def test_pin_existing_episode(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_episode_pin", {"episode_id": "e1"},
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    assert payload["pinned"] is True
    assert "e1" in fake_agent.memory.pinned


@pytest.mark.asyncio
async def test_pin_unknown_episode(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_episode_pin", {"episode_id": "ghost"},
    )
    payload = json.loads(blocks[0])
    assert "error" in payload


# ---------- hippo_episode_unpin -----------------------------------------


@pytest.mark.asyncio
async def test_unpin_after_pin(fake_agent: _FakeAgent) -> None:
    fake_agent.memory.set_pinned("e2", True)
    blocks = await _invoke_tool(
        "hippo_episode_unpin", {"episode_id": "e2"},
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    assert payload["pinned"] is False
    assert "e2" not in fake_agent.memory.pinned


@pytest.mark.asyncio
async def test_unpin_unknown_episode(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_episode_unpin", {"episode_id": "nope"},
    )
    payload = json.loads(blocks[0])
    assert "error" in payload


# ---------- hippo_metrics_history --------------------------------------


@pytest.mark.asyncio
async def test_metrics_history_default_grouping(
    fake_agent: _FakeAgent,
) -> None:
    blocks = await _invoke_tool("hippo_metrics_history", {})
    payload = json.loads(blocks[0])
    assert "buckets" in payload
    assert payload["bucket_size"] == "day"
    assert payload["total_episodes"] == 5
    assert payload["total_tokens"] == 1050.0  # 100+200+50+300+400
    # 3 distinct days
    assert len(payload["buckets"]) == 3
    # newest first by default
    assert payload["buckets"][0]["episodes"] == 2  # day 2
    assert payload["buckets"][0]["tokens"] == 700.0
    assert payload["buckets"][1]["episodes"] == 1  # day 1
    assert payload["buckets"][2]["episodes"] == 2  # day 0


@pytest.mark.asyncio
async def test_metrics_history_separates_outcomes(
    fake_agent: _FakeAgent,
) -> None:
    blocks = await _invoke_tool("hippo_metrics_history", {})
    payload = json.loads(blocks[0])
    failure_buckets = [b for b in payload["buckets"] if b["failures"] > 0]
    assert len(failure_buckets) == 1
    assert failure_buckets[0]["failures"] == 1
    assert failure_buckets[0]["successes"] == 0


@pytest.mark.asyncio
async def test_metrics_history_empty(
    fake_agent: _FakeAgent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_agent.memory.episodes = []
    blocks = await _invoke_tool("hippo_metrics_history", {})
    payload = json.loads(blocks[0])
    assert payload["total_episodes"] == 0
    assert payload["buckets"] == []
