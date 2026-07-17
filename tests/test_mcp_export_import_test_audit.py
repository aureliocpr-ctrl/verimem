"""FORGIA pezzo #196 — MCP tools Wave 2.

* ``hippo_skill_export``  — export 1 skill or all as JSON.
* ``hippo_skill_import``  — import skills from JSON, dedup-by-id.
* ``hippo_skill_test``    — render skill prompt for an arbitrary input
                            (no LLM call, deterministic preview).
* ``hippo_audit_tail``    — read the last N lines of the MCP audit log.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from verimem import mcp_server

# ---------- Fakes ---------------------------------------------------------


class _FakeSkill:
    def __init__(
        self, sid: str, name: str, *, body: str = "do X then Y",
        trigger: str = "when X",
        status: str = "candidate", version: int = 1,
        trials: int = 0, successes: int = 0,
    ) -> None:
        self.id = sid
        self.name = name
        self.body = body
        self.trigger = trigger
        self.status = status
        self.version = version
        self.trials = trials
        self.successes = successes
        self.fitness_mean = 0.5
        self.stage = "nrem"
        self.parent_skills: list[str] = []
        self.compiled_macro = None

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "body": self.body,
            "trigger": self.trigger, "status": self.status,
            "version": self.version, "trials": self.trials,
            "successes": self.successes, "fitness_mean": self.fitness_mean,
            "stage": self.stage,
        }

    def render(self) -> str:
        return (
            f"### Skill: {self.name}\n"
            f"_When to apply:_ {self.trigger}\n\n"
            f"{self.body}\n"
        )


class _FakeSkillsStore:
    def __init__(self, skills: list[_FakeSkill]) -> None:
        self._skills = {s.id: s for s in skills}
        self._stored: list[_FakeSkill] = []

    def all(self, status: str | None = None) -> list[_FakeSkill]:
        items = list(self._skills.values())
        if status:
            items = [s for s in items if s.status == status]
        return items

    def get(self, sid: str) -> _FakeSkill | None:
        return self._skills.get(sid)

    def store(self, skill: _FakeSkill) -> None:
        self._skills[skill.id] = skill
        self._stored.append(skill)

    def count(self, status: str | None = None) -> int:
        if status:
            return sum(1 for s in self._skills.values() if s.status == status)
        return len(self._skills)


class _FakeAgent:
    def __init__(self) -> None:
        self.skills = _FakeSkillsStore([
            _FakeSkill("s1", "factorial recurse", body="def f(n): ...",
                       trigger="when computing factorial",
                       status="promoted"),
            _FakeSkill("s2", "rot13 transform", body="apply rot13",
                       trigger="when shifting alphabet",
                       status="candidate"),
        ])


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


# ---------- listing ------------------------------------------------------


@pytest.mark.asyncio
async def test_wave2_tools_listed(fake_agent: _FakeAgent) -> None:
    from mcp.types import ListToolsRequest, PaginatedRequestParams
    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(method="tools/list", params=PaginatedRequestParams())
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    for n in ("hippo_skill_export", "hippo_skill_import",
              "hippo_skill_test", "hippo_audit_tail"):
        assert n in names, f"missing tool: {n}"


# ---------- hippo_skill_export ------------------------------------------


@pytest.mark.asyncio
async def test_hippo_skill_export_all(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool("hippo_skill_export", {})
    payload = json.loads(blocks[0])
    assert "skills" in payload
    assert "exported_at" in payload
    assert "count" in payload
    assert payload["count"] == 2
    ids = {s["id"] for s in payload["skills"]}
    assert ids == {"s1", "s2"}


@pytest.mark.asyncio
async def test_hippo_skill_export_one(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_export", {"skill_id": "s1"},
    )
    payload = json.loads(blocks[0])
    assert payload["count"] == 1
    assert payload["skills"][0]["id"] == "s1"


@pytest.mark.asyncio
async def test_hippo_skill_export_filter_status(
    fake_agent: _FakeAgent,
) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_export", {"status": "promoted"},
    )
    payload = json.loads(blocks[0])
    assert payload["count"] == 1
    assert payload["skills"][0]["id"] == "s1"


@pytest.mark.asyncio
async def test_hippo_skill_export_unknown_id(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_export", {"skill_id": "missing"},
    )
    payload = json.loads(blocks[0])
    assert "error" in payload


# ---------- hippo_skill_import ------------------------------------------


@pytest.mark.asyncio
async def test_hippo_skill_import_new(
    fake_agent: _FakeAgent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Patch Skill.from_dict so the import handler can reconstruct fakes.
    def _from_dict(d: dict) -> _FakeSkill:
        return _FakeSkill(
            sid=d["id"], name=d["name"], body=d.get("body", ""),
            trigger=d.get("trigger", ""),
            status=d.get("status", "candidate"),
            version=int(d.get("version", 1)),
            trials=int(d.get("trials", 0)),
            successes=int(d.get("successes", 0)),
        )
    monkeypatch.setattr(mcp_server, "_skill_from_dict", _from_dict,
                        raising=False)

    blocks = await _invoke_tool(
        "hippo_skill_import",
        {"skills": [
            {"id": "s3", "name": "new skill", "body": "...",
             "trigger": "when new"},
            {"id": "s1", "name": "factorial v2", "body": "..."},
        ]},
    )
    payload = json.loads(blocks[0])
    assert payload["imported"] == 1  # only s3 (s1 collides)
    assert payload["skipped_duplicates"] == 1


@pytest.mark.asyncio
async def test_hippo_skill_import_overwrite(
    fake_agent: _FakeAgent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _from_dict(d: dict) -> _FakeSkill:
        return _FakeSkill(
            sid=d["id"], name=d["name"], body=d.get("body", ""),
            trigger=d.get("trigger", ""),
            status=d.get("status", "candidate"),
            version=int(d.get("version", 1)),
        )
    monkeypatch.setattr(mcp_server, "_skill_from_dict", _from_dict,
                        raising=False)

    blocks = await _invoke_tool(
        "hippo_skill_import",
        {"overwrite": True,
         "skills": [{"id": "s1", "name": "v2", "body": "x"}]},
    )
    payload = json.loads(blocks[0])
    assert payload["imported"] == 1
    assert payload["overwritten"] == 1


@pytest.mark.asyncio
async def test_hippo_skill_import_empty(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool("hippo_skill_import", {"skills": []})
    payload = json.loads(blocks[0])
    assert payload["imported"] == 0


# ---------- hippo_skill_test --------------------------------------------


@pytest.mark.asyncio
async def test_hippo_skill_test_renders_prompt(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_test",
        {"skill_id": "s1", "task": "compute 5!"},
    )
    payload = json.loads(blocks[0])
    assert payload["skill_id"] == "s1"
    assert payload["skill_name"] == "factorial recurse"
    # the rendered context must include the trigger and body
    assert "factorial" in payload["rendered_context"].lower()
    assert "compute 5!" in payload["task"]
    # no LLM was called
    assert payload["llm_called"] is False


@pytest.mark.asyncio
async def test_hippo_skill_test_unknown(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_skill_test",
        {"skill_id": "nope", "task": "x"},
    )
    payload = json.loads(blocks[0])
    assert "error" in payload


# ---------- hippo_audit_tail --------------------------------------------


@pytest.mark.asyncio
async def test_hippo_audit_tail_reads_last_n(
    fake_agent: _FakeAgent,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Redirect audit log to tmp.
    log_path = tmp_path / "mcp_audit.log"
    monkeypatch.setattr(mcp_server, "_audit_log_path", lambda: log_path)
    # Write 5 fake records.
    for i in range(5):
        rec = {"ts": time.time(), "tool": f"tool_{i}",
                 "caller_pid": 1, "args_hash": "x", "outcome": "ok",
                 "error": ""}
        log_path.write_text(
            (log_path.read_text(encoding="utf-8") if log_path.exists() else "")
            + json.dumps(rec) + "\n",
            encoding="utf-8",
        )
    blocks = await _invoke_tool("hippo_audit_tail", {"n": 3})
    payload = json.loads(blocks[0])
    assert payload["n"] == 3
    assert len(payload["entries"]) == 3
    # newest last (file order): tool_2, tool_3, tool_4
    tools = [e["tool"] for e in payload["entries"]]
    assert tools == ["tool_2", "tool_3", "tool_4"]


@pytest.mark.asyncio
async def test_hippo_audit_tail_empty_log(
    fake_agent: _FakeAgent,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_path = tmp_path / "mcp_audit.log"
    monkeypatch.setattr(mcp_server, "_audit_log_path", lambda: log_path)
    blocks = await _invoke_tool("hippo_audit_tail", {"n": 5})
    payload = json.loads(blocks[0])
    assert payload["entries"] == []


@pytest.mark.asyncio
async def test_hippo_audit_tail_default_n(
    fake_agent: _FakeAgent,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_path = tmp_path / "mcp_audit.log"
    monkeypatch.setattr(mcp_server, "_audit_log_path", lambda: log_path)
    rec = {"ts": time.time(), "tool": "x", "caller_pid": 1,
            "args_hash": "y", "outcome": "ok", "error": ""}
    log_path.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    blocks = await _invoke_tool("hippo_audit_tail", {})
    payload = json.loads(blocks[0])
    assert payload["n"] == 50  # default
    assert len(payload["entries"]) == 1
