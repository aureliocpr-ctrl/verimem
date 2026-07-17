"""FORGIA pezzo #203 — MCP tools Wave 8 (KEYWORD search on facts/skills).

Aurelio asked: "anche la ricerca tra i ricordi in maniera diretta?".
Wave 1 added keyword search on episodes; Wave 7 added semantic on
facts. Wave 8 closes the symmetry: keyword search (LIKE) on facts
*and* on skills.

* ``hippo_facts_search``  — substring LIKE on `proposition`,
                             case-insensitive, optional `topic` filter.
* ``hippo_skills_search`` — substring LIKE across name+trigger+body,
                             case-insensitive, optional `status` filter.
"""
from __future__ import annotations

import json
import time
from typing import Any

import pytest

from verimem import mcp_server

# ---------- Fakes --------------------------------------------------------


class _FakeFact:
    def __init__(self, fid: str, *, proposition: str, topic: str = "",
                  confidence: float = 0.9,
                  created_at: float | None = None) -> None:
        self.id = fid
        self.proposition = proposition
        self.topic = topic
        self.confidence = confidence
        self.source_episodes: list[str] = []
        self.created_at = created_at or time.time()


class _FakeSemantic:
    def __init__(self) -> None:
        self._facts = {
            "f1": _FakeFact("f1", proposition="User email is "
                            "user@example.com", topic="user_facts",
                             created_at=1000.0),
            "f2": _FakeFact("f2", proposition="API endpoint is "
                            "https://api.example.com/v1",
                             topic="api_endpoints", created_at=1100.0),
            "f3": _FakeFact("f3", proposition="The database password is "
                            "stored in 1Password", topic="secrets",
                             created_at=1200.0),
        }

    def search_facts(self, query: str, *, limit: int = 20,
                      topic: str | None = None,
                      exclude_legacy: bool = False,
                      min_status: str | None = None,
                      tokenize: bool = False,
                      require_all_tokens: bool = False,
                      topic_prefix: str | None = None,
                      ) -> list[_FakeFact]:
        # Cycle #109 S4-A: accept the new kw-only filters. These fakes
        # don't carry a ``status`` field, so the filter is a no-op here
        # (legacy detection just isn't exercised by this test suite).
        # 2026-06-13: mirror the multi-word AND/OR token semantics.
        ql = (query or "").strip().lower()
        toks = [t for t in ql.split() if len(t) >= 2] if (
            tokenize or require_all_tokens
        ) else []
        out: list[_FakeFact] = []
        for f in self._facts.values():
            pl = f.proposition.lower()
            if ql:
                if len(toks) > 1:
                    ok = (all(t in pl for t in toks) if require_all_tokens
                          else any(t in pl for t in toks))
                elif len(toks) == 1:
                    ok = toks[0] in pl
                else:
                    ok = ql in pl
                if not ok:
                    continue
            if topic and f.topic != topic:
                continue
            if topic_prefix and not f.topic.startswith(topic_prefix):
                continue
            out.append(f)
        out.sort(key=lambda f: f.created_at, reverse=True)
        return out[:limit]


class _FakeSkill:
    def __init__(self, sid: str, *, name: str, body: str = "",
                  trigger: str = "", status: str = "candidate",
                  fitness_mean: float = 0.5,
                  trials: int = 0, successes: int = 0,
                  created_at: float | None = None) -> None:
        self.id = sid
        self.name = name
        self.body = body
        self.trigger = trigger
        self.status = status
        self.fitness_mean = fitness_mean
        self.trials = trials
        self.successes = successes
        self.created_at = created_at or time.time()


class _FakeSkillsStore:
    def __init__(self) -> None:
        self._skills = {
            "sk1": _FakeSkill(
                "sk1", name="parse JSON", body="open file. json.load.",
                trigger="when input is a JSON file path",
                status="promoted", fitness_mean=0.9,
            ),
            "sk2": _FakeSkill(
                "sk2", name="send email",
                body="connect SMTP. compose. send.",
                trigger="when sending an email",
                status="candidate", fitness_mean=0.6,
            ),
            "sk3": _FakeSkill(
                "sk3", name="parse YAML", body="open file. yaml.safe_load.",
                trigger="when input is a YAML file",
                status="candidate", fitness_mean=0.5,
            ),
        }

    def search_skills(
        self, query: str, *, limit: int = 20,
        status: str | None = None,
    ) -> list[_FakeSkill]:
        ql = (query or "").strip().lower()
        out: list[_FakeSkill] = []
        for s in self._skills.values():
            blob = " ".join([s.name, s.trigger, s.body]).lower()
            if ql and ql not in blob:
                continue
            if status and s.status != status:
                continue
            out.append(s)
        out.sort(key=lambda s: s.fitness_mean, reverse=True)
        return out[:limit]


class _FakeAgent:
    def __init__(self) -> None:
        self.semantic = _FakeSemantic()
        self.skills = _FakeSkillsStore()


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
def fake_agent(monkeypatch: pytest.MonkeyPatch) -> _FakeAgent:
    a = _FakeAgent()
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a


# ---------- listing -----------------------------------------------------


@pytest.mark.asyncio
async def test_wave8_tools_listed(fake_agent: _FakeAgent) -> None:
    from mcp.types import ListToolsRequest, PaginatedRequestParams
    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(method="tools/list", params=PaginatedRequestParams())
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    for n in ("hippo_facts_search", "hippo_skills_search"):
        assert n in names, f"missing tool: {n}"


# ---------- hippo_facts_search ------------------------------------------


@pytest.mark.asyncio
async def test_facts_search_substring(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_facts_search", {"query": "email"},
    )
    payload = json.loads(blocks[0])
    items = payload["items"]
    ids = [it["id"] for it in items]
    # f1 has "email", f3 has nothing; api_endpoints (f2) doesn't match
    assert "f1" in ids
    assert "f3" not in ids


@pytest.mark.asyncio
async def test_facts_search_topic_filter(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_facts_search", {"query": "", "topic": "secrets"},
    )
    payload = json.loads(blocks[0])
    items = payload["items"]
    ids = [it["id"] for it in items]
    assert ids == ["f3"]


@pytest.mark.asyncio
async def test_facts_search_case_insensitive(fake_agent: _FakeAgent) -> None:
    # Fixture has no "Aurelio" — match against a token present in the
    # seeded facts. f1.proposition contains lowercase "email"; uppercase
    # query MUST hit via case-insensitive ``LIKE``.
    blocks = await _invoke_tool(
        "hippo_facts_search", {"query": "EMAIL"},
    )
    payload = json.loads(blocks[0])
    items = payload["items"]
    assert any("email" in it["proposition"].lower() for it in items), (
        f"case-insensitive search failed: ids={[it['id'] for it in items]}"
    )
    # Specifically f1 (has "User email is ...") must surface.
    assert any(it["id"] == "f1" for it in items)


@pytest.mark.asyncio
async def test_facts_search_empty_query_returns_all(
    fake_agent: _FakeAgent,
) -> None:
    blocks = await _invoke_tool("hippo_facts_search", {"query": ""})
    payload = json.loads(blocks[0])
    items = payload["items"]
    # All 3 facts.
    assert len(items) == 3
    # Newest first.
    assert items[0]["id"] == "f3"


# ---------- hippo_skills_search ----------------------------------------


@pytest.mark.asyncio
async def test_skills_search_finds_in_name(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skills_search", {"query": "JSON"},
    )
    payload = json.loads(blocks[0])
    ids = [it["id"] for it in payload["items"]]
    assert "sk1" in ids
    assert "sk2" not in ids  # email skill, no JSON


@pytest.mark.asyncio
async def test_skills_search_finds_in_trigger(fake_agent: _FakeAgent) -> None:
    """Trigger contains 'sending email' — distinct from name field."""
    blocks = await _invoke_tool(
        "hippo_skills_search", {"query": "sending"},
    )
    payload = json.loads(blocks[0])
    ids = [it["id"] for it in payload["items"]]
    assert "sk2" in ids


@pytest.mark.asyncio
async def test_skills_search_finds_in_body(fake_agent: _FakeAgent) -> None:
    """Body contains 'safe_load' — appears nowhere else."""
    blocks = await _invoke_tool(
        "hippo_skills_search", {"query": "safe_load"},
    )
    payload = json.loads(blocks[0])
    ids = [it["id"] for it in payload["items"]]
    assert ids == ["sk3"]


@pytest.mark.asyncio
async def test_skills_search_status_filter(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skills_search",
        {"query": "parse", "status": "promoted"},
    )
    payload = json.loads(blocks[0])
    items = payload["items"]
    ids = [it["id"] for it in items]
    # Both sk1 (parse JSON) and sk3 (parse YAML) match query, but only
    # sk1 is promoted.
    assert ids == ["sk1"]


@pytest.mark.asyncio
async def test_skills_search_sorted_by_fitness(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skills_search", {"query": "parse"},
    )
    payload = json.loads(blocks[0])
    items = payload["items"]
    # parse JSON (0.9) before parse YAML (0.5)
    assert items[0]["id"] == "sk1"
    assert items[1]["id"] == "sk3"
