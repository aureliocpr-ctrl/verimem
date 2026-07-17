"""FORGIA pezzo #201 — MCP tools Wave 6.

* ``hippo_skill_describe``  — short natural-language summary of a skill,
                              built from name+trigger+body (NO LLM call).
* ``hippo_provider_switch`` — switch the active LLM provider at runtime
                              by setting HIPPO_LLM_PROVIDER env var.
                              Requires the new provider to be configured.
* ``hippo_skill_merge``     — manually merge skill A into skill B:
                              union of bodies + sum of trials/successes,
                              then retire A. Useful before sleep auto-merge.
"""
from __future__ import annotations

import json
import os
from typing import Any

import pytest

from verimem import mcp_server

# ---------- Fakes --------------------------------------------------------


class _FakeSkill:
    def __init__(self, sid: str, *, name: str, body: str = "",
                  trigger: str = "", fitness_mean: float = 0.5,
                  trials: int = 0, successes: int = 0,
                  status: str = "candidate", version: int = 1) -> None:
        self.id = sid
        self.name = name
        self.body = body
        self.trigger = trigger
        self.fitness_mean = fitness_mean
        self.trials = trials
        self.successes = successes
        self.status = status
        self.version = version
        self.parent_skills: list[str] = []
        self.compiled_macro = None


class _FakeSkillsStore:
    def __init__(self) -> None:
        self._skills = {
            "alpha": _FakeSkill(
                "alpha", name="parse JSON", body="open file. json.load. "
                "validate. return dict.",
                trigger="when input is a JSON file path",
                fitness_mean=0.85, trials=10, successes=9,
                status="promoted",
            ),
            "beta": _FakeSkill(
                "beta", name="parse JSON safer",
                body="try open file. validate schema. json.load. return.",
                trigger="when JSON parsing must validate schema",
                fitness_mean=0.70, trials=5, successes=3,
                status="candidate",
            ),
        }
        self._stored: list[_FakeSkill] = []

    def get(self, sid: str) -> _FakeSkill | None:
        return self._skills.get(sid)

    def all(self, status: str | None = None) -> list[_FakeSkill]:
        items = list(self._skills.values())
        if status:
            items = [s for s in items if s.status == status]
        return items

    def store(self, sk: _FakeSkill) -> None:
        self._skills[sk.id] = sk
        self._stored.append(sk)


class _FakeAgent:
    def __init__(self) -> None:
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
async def test_wave6_tools_listed(fake_agent: _FakeAgent) -> None:
    from mcp.types import ListToolsRequest, PaginatedRequestParams
    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(method="tools/list", params=PaginatedRequestParams())
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    for n in ("hippo_skill_describe", "hippo_provider_switch",
              "hippo_skill_merge"):
        assert n in names, f"missing tool: {n}"


# ---------- hippo_skill_describe -----------------------------------------


@pytest.mark.asyncio
async def test_skill_describe_basic(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_describe", {"skill_id": "alpha"},
    )
    payload = json.loads(blocks[0])
    assert payload["skill_id"] == "alpha"
    assert "summary" in payload
    # Summary must mention name + trigger + first body line.
    s = payload["summary"]
    assert "parse JSON" in s
    assert "JSON file path" in s
    assert "9/10" in s  # successes/trials
    assert payload["llm_called"] is False


@pytest.mark.asyncio
async def test_skill_describe_unknown(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_describe", {"skill_id": "ghost"},
    )
    payload = json.loads(blocks[0])
    assert "error" in payload


# ---------- hippo_provider_switch ---------------------------------------


@pytest.mark.asyncio
async def test_provider_switch_to_anthropic(
    fake_agent: _FakeAgent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Switching to a configured provider sets the env var and reports OK."""
    # Pretend anthropic is configured.
    monkeypatch.setattr(
        mcp_server, "_provider_is_configured",
        lambda p: p == "anthropic", raising=False,
    )
    monkeypatch.delenv("HIPPO_LLM_PROVIDER", raising=False)
    blocks = await _invoke_tool(
        "hippo_provider_switch", {"provider": "anthropic"},
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    assert payload["provider"] == "anthropic"
    assert os.environ.get("HIPPO_LLM_PROVIDER") == "anthropic"


@pytest.mark.asyncio
async def test_provider_switch_unconfigured(
    fake_agent: _FakeAgent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Switching to an unconfigured provider returns an error."""
    monkeypatch.setattr(
        mcp_server, "_provider_is_configured",
        lambda p: False, raising=False,
    )
    blocks = await _invoke_tool(
        "hippo_provider_switch", {"provider": "openai"},
    )
    payload = json.loads(blocks[0])
    assert "error" in payload


# ---------- hippo_skill_merge -------------------------------------------


@pytest.mark.asyncio
async def test_skill_merge_basic(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_merge",
        {"src_skill_id": "alpha", "dst_skill_id": "beta"},
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    assert payload["src_skill_id"] == "alpha"
    assert payload["dst_skill_id"] == "beta"
    # alpha must now be retired.
    assert fake_agent.skills.get("alpha").status == "retired"
    # beta should have inherited trials/successes (5+10=15, 3+9=12).
    beta = fake_agent.skills.get("beta")
    assert beta.trials == 15
    assert beta.successes == 12


@pytest.mark.asyncio
async def test_skill_merge_self_rejected(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_merge",
        {"src_skill_id": "alpha", "dst_skill_id": "alpha"},
    )
    payload = json.loads(blocks[0])
    assert "error" in payload


@pytest.mark.asyncio
async def test_skill_merge_unknown(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_merge",
        {"src_skill_id": "ghost", "dst_skill_id": "beta"},
    )
    payload = json.loads(blocks[0])
    assert "error" in payload
