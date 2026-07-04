"""MCP recall payloads must carry a readable date (2026-06-20).

hippo_recall (episodes) carried NO timestamp, and hippo_facts_recall carried only a
raw epoch float — neither lets the consuming agent reason temporally ("how long
ago", "which came first"). Both now expose a readable ``when`` (YYYY-MM-DD, UTC).
This is the production-side of the timestamp lever validated on HaluMem + the QA
temporal-reasoning A/B.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from engram import mcp_server


def test_iso_day_formats_and_guards() -> None:
    assert mcp_server._iso_day(1_000_000_000.0) == "2001-09-09"
    assert mcp_server._iso_day(0) is None        # missing
    assert mcp_server._iso_day(-5) is None        # invalid
    assert mcp_server._iso_day("nope") is None    # non-numeric


class _FakeEpisode:
    def __init__(self, eid: str, created_at: float) -> None:
        self.id = eid
        self.task_text = "did a thing"
        self.outcome = "success"
        self.final_answer = "the answer"
        self.num_steps = 3
        self.created_at = created_at


class _FakeMemory:
    def __init__(self) -> None:
        self._eps = [_FakeEpisode("e1", 1_000_000_000.0)]

    def recall(self, query: str, k: int = 5, outcome_filter: Any = None):
        return [(ep, 0.9) for ep in self._eps[:k]]


class _FakeFact:
    def __init__(self) -> None:
        self.id = "f1"
        self.proposition = "alpha fact"
        self.topic = "lessons/test"
        self.confidence = 0.8
        self.created_at = 1_000_000_000.0
        self.status = "model_claim"
        self.verified_by: list[str] = []
        self.source_episodes: list[str] = []


class _FakeSemantic:
    def recall(self, query: str, k: int = 5, topic=None, *, exclude_legacy=False,
               min_status=None, trust_signals=False):
        return [(_FakeFact(), 0.9)]


class _FakeAgent:
    def __init__(self) -> None:
        self.memory = _FakeMemory()
        self.semantic = _FakeSemantic()


async def _invoke(name: str, arguments: dict[str, Any]):
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(method="tools/call",
                          params=CallToolRequestParams(name=name, arguments=arguments))
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    return json.loads(payload.content[0].text)


@pytest.fixture
def fake_agent(monkeypatch: pytest.MonkeyPatch) -> _FakeAgent:
    a = _FakeAgent()
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a


@pytest.mark.asyncio
async def test_episode_recall_exposes_when(fake_agent: _FakeAgent) -> None:
    items = await _invoke("hippo_recall", {"query": "thing", "k": 5})
    assert items and items[0]["when"] == "2001-09-09"


@pytest.mark.asyncio
async def test_facts_recall_exposes_when(fake_agent: _FakeAgent) -> None:
    payload = await _invoke("hippo_facts_recall", {"query": "alpha", "k": 5})
    it = payload["items"][0]
    assert it["when"] == "2001-09-09"
    assert it["created_at"] == 1_000_000_000.0  # raw epoch kept for back-compat


@pytest.mark.asyncio
async def test_recall_explain_exposes_when(fake_agent: _FakeAgent) -> None:
    # _FakeMemory has no recall_explain -> handler falls back to plain recall.
    payload = await _invoke("hippo_recall_explain", {"query": "thing", "k": 5})
    assert payload["results"][0]["when"] == "2001-09-09"
