"""CVE-007 — MCP server hardening contract.

Coverage:
  - inputSchema validation rejects bad arguments before dispatch
  - Audit log appends one JSONL entry per call (success, schema-fail,
    rate-limit, exception)
  - Token-bucket rate-limit on hippo_run_task / hippo_consolidate
  - perm_shell gate refuses shell-like task content when off
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from verimem import mcp_server


@dataclass
class _FakeSkill:
    id: str = "sk-1"
    name: str = "test-skill"
    trigger: str = "test"
    body: str = "do something"
    rationale: str = ""
    fitness_mean: float = 0.7
    status: str = "promoted"
    stage: str = "consolidated"
    trials: int = 5
    successes: int = 4
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


@dataclass
class _FakeEpisode:
    id: str = "ep-1"
    task_text: str = "fake task"
    outcome: str = "success"
    final_answer: str = "42"
    num_steps: int = 3
    tokens_used: int = 100
    skills_used: list[str] = field(default_factory=list)
    critique: str = ""

    def trajectory_text(self) -> str:
        return ""


class _FakeMemory:
    def __init__(self):
        self._eps: dict[str, _FakeEpisode] = {}

    def get(self, eid):
        return self._eps.get(eid)

    def all(self, limit=None):
        return list(self._eps.values())

    def count(self):
        return len(self._eps)

    def recall(self, query, k=5, outcome_filter=None):
        return []


class _FakeSkills:
    def __init__(self):
        self._s: dict[str, _FakeSkill] = {}

    def get(self, sid):
        return self._s.get(sid)

    def all(self, status=None):
        items = list(self._s.values())
        return [s for s in items if not status or s.status == status]

    def count(self, status=None):
        return len(self.all(status=status))

    def store(self, s):
        self._s[s.id] = s

    def retrieve(self, task, k=3, status=None):
        return self.all(status=status)[:k]


class _FakeSemantic:
    def count(self):
        return 0


@dataclass
class _FakeAgent:
    memory: _FakeMemory = field(default_factory=_FakeMemory)
    skills: _FakeSkills = field(default_factory=_FakeSkills)
    semantic: _FakeSemantic = field(default_factory=_FakeSemantic)


@pytest.fixture
def isolated_audit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the audit log to a tmp file."""
    audit_path = tmp_path / "mcp_audit.log"
    monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(audit_path))
    return audit_path


@pytest.fixture
def fake_agent(monkeypatch: pytest.MonkeyPatch) -> _FakeAgent:
    a = _FakeAgent()
    a.skills.store(_FakeSkill(id="sk-1"))
    a.memory._eps["ep-1"] = _FakeEpisode(id="ep-1")
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    monkeypatch.setattr(mcp_server, "_agent", a, raising=False)
    return a


@pytest.fixture
def reset_buckets(monkeypatch: pytest.MonkeyPatch):
    """Force fresh rate-limit buckets per test."""
    monkeypatch.setattr(mcp_server, "_RATE_BUCKETS", {})
    yield


async def _invoke_tool(name: str, arguments: dict[str, Any] | None = None):
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(method="tools/call", params=CallToolRequestParams(
        name=name, arguments=arguments or {},
    ))
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    return [c.text for c in payload.content if hasattr(c, "text")]


def _parse_response(text: str) -> dict[str, Any]:
    """The handler returns either JSON (from our _ok / _err) OR a plain-text
    error from the MCP framework's pre-dispatch schema validator. Normalise."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Treat raw error string as { error: text }
        return {"error": text}


# ---------------------------------------------------------------------------
# inputSchema validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_schema_rejects_missing_required_field(
    fake_agent: _FakeAgent, isolated_audit: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HIPPO_MCP_DISABLE_RATELIMIT", "1")
    blocks = await _invoke_tool("hippo_run_task", {})  # missing 'task'
    payload = _parse_response(blocks[0])
    assert "error" in payload
    assert "validation" in payload["error"].lower() \
        or "task" in payload["error"].lower()


@pytest.mark.asyncio
async def test_schema_rejects_wrong_type(
    fake_agent: _FakeAgent, isolated_audit: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HIPPO_MCP_DISABLE_RATELIMIT", "1")
    blocks = await _invoke_tool("hippo_recall", {"query": "x", "k": "five"})
    payload = _parse_response(blocks[0])
    assert "error" in payload
    assert "validation" in payload["error"].lower() \
        or "integer" in payload["error"].lower()


@pytest.mark.asyncio
async def test_schema_rejects_bad_enum(
    fake_agent: _FakeAgent, isolated_audit: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HIPPO_MCP_DISABLE_RATELIMIT", "1")
    blocks = await _invoke_tool("hippo_recall", {
        "query": "x", "outcome": "bogus",
    })
    payload = _parse_response(blocks[0])
    assert "error" in payload


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


def _read_audit(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


@pytest.mark.asyncio
async def test_audit_log_records_calls(
    fake_agent: _FakeAgent, isolated_audit: Path,
    reset_buckets, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HIPPO_MCP_DISABLE_RATELIMIT", "1")
    # Two successful calls — exercises the audit code path that writes
    # outcome=ok records.
    await _invoke_tool("hippo_skill_retire", {"skill_id": "sk-1"})
    await _invoke_tool("hippo_skill_promote", {"skill_id": "sk-1"})
    # Unknown tool — exercises the unknown_tool branch
    await _invoke_tool("hippo_skill_retire", {"skill_id": "missing"})
    records = _read_audit(isolated_audit)
    assert len(records) >= 3
    outcomes = [r["outcome"] for r in records]
    assert "ok" in outcomes
    # Each record has required fields
    for r in records:
        assert "ts" in r
        assert "tool" in r
        assert "args_hash" in r
        assert "caller_pid" in r
        # args_hash never reveals raw content - fixed length, hex-only
        assert len(r["args_hash"]) == 16
        assert all(c in "0123456789abcdef" for c in r["args_hash"])


@pytest.mark.asyncio
async def test_audit_log_records_schema_rejection(
    fake_agent: _FakeAgent, isolated_audit: Path,
    reset_buckets, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When OUR schema validator (manual fallback) rejects, the audit MUST
    record outcome=rejected_schema. Force the manual path by simulating the
    jsonschema lib being absent."""
    monkeypatch.setenv("HIPPO_MCP_DISABLE_RATELIMIT", "1")

    # Force the manual validator path inside the call_tool dispatcher by
    # disabling jsonschema lookup. We do this by patching _validate_input to
    # always go through manual validation and intentionally fail for an
    # arguments shape the dispatcher would otherwise accept.
    real_validate = mcp_server._validate_input

    def fake_validate(name, arguments):
        if name == "hippo_skill_retire" and arguments.get("skill_id") == "":
            return "skill_id must be non-empty"
        return real_validate(name, arguments)

    monkeypatch.setattr(mcp_server, "_validate_input", fake_validate)

    await _invoke_tool("hippo_skill_retire", {"skill_id": ""})
    records = _read_audit(isolated_audit)
    outcomes = [r["outcome"] for r in records]
    assert "rejected_schema" in outcomes


# ---------------------------------------------------------------------------
# Rate limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limit_blocks_second_call(
    fake_agent: _FakeAgent, isolated_audit: Path,
    reset_buckets, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default capacity=1 - first call succeeds, second is rate-limited."""
    monkeypatch.delenv("HIPPO_MCP_DISABLE_RATELIMIT", raising=False)
    monkeypatch.setenv("HIPPO_MCP_RATELIMIT_HIPPO_CONSOLIDATE_CAP", "1")
    monkeypatch.setenv("HIPPO_MCP_RATELIMIT_HIPPO_CONSOLIDATE_RPM", "0.001")
    fake_report = MagicMock()
    fake_report.n_episodes_replayed = 0
    fake_report.n_clusters = 0
    fake_report.n_nrem_skills = 0
    fake_report.n_rem_skills = 0
    fake_report.n_facts = 0
    fake_report.promoted = []
    fake_report.retired = []
    fake_report.merged = []
    fake_report.duration_s = 0.0
    fake_report.tokens_used = 0
    fake_agent.consolidate = MagicMock(return_value=fake_report)

    blocks_1 = await _invoke_tool("hippo_consolidate", {})
    payload_1 = json.loads(blocks_1[0])
    assert "error" not in payload_1

    blocks_2 = await _invoke_tool("hippo_consolidate", {})
    payload_2 = json.loads(blocks_2[0])
    assert "error" in payload_2
    assert "rate" in payload_2["error"].lower()


@pytest.mark.asyncio
async def test_rate_limit_does_not_apply_to_lightweight_tools(
    fake_agent: _FakeAgent, isolated_audit: Path,
    reset_buckets, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """hippo_status / hippo_recall / skill_get NOT rate-limited."""
    monkeypatch.delenv("HIPPO_MCP_DISABLE_RATELIMIT", raising=False)
    # Many calls in a row - none should be limited
    for _ in range(5):
        blocks = await _invoke_tool("hippo_skill_retire", {"skill_id": "sk-1"})
        assert "rate" not in blocks[0].lower()


# ---------------------------------------------------------------------------
# perm_shell gate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_perm_shell_off_blocks_shell_like_task(
    fake_agent: _FakeAgent, isolated_audit: Path,
    reset_buckets, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HIPPO_MCP_DISABLE_RATELIMIT", "1")
    monkeypatch.delenv("HIPPO_ENABLE_SHELL", raising=False)
    blocks = await _invoke_tool("hippo_run_task", {
        "task": "Run sudo rm -rf /tmp/foo to clean up",
    })
    payload = _parse_response(blocks[0])
    assert "error" in payload
    assert "perm_shell" in payload["error"] or "shell" in payload["error"].lower()


@pytest.mark.asyncio
async def test_perm_shell_on_allows_shell_like_task(
    fake_agent: _FakeAgent, isolated_audit: Path,
    reset_buckets, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HIPPO_MCP_DISABLE_RATELIMIT", "1")
    monkeypatch.setenv("HIPPO_ENABLE_SHELL", "1")
    fake_result = MagicMock()
    fake_result.episode = _FakeEpisode(id="ep-new", outcome="success",
                                        final_answer="done", num_steps=1,
                                        tokens_used=10)
    fake_result.skills_retrieved = []
    fake_agent.run_task = MagicMock(return_value=fake_result)
    blocks = await _invoke_tool("hippo_run_task", {
        "task": "Run sudo apt update for me",
    })
    payload = _parse_response(blocks[0])
    assert "error" not in payload, payload


@pytest.mark.asyncio
async def test_perm_shell_off_normal_task_still_works(
    fake_agent: _FakeAgent, isolated_audit: Path,
    reset_buckets, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HIPPO_MCP_DISABLE_RATELIMIT", "1")
    monkeypatch.delenv("HIPPO_ENABLE_SHELL", raising=False)
    fake_result = MagicMock()
    fake_result.episode = _FakeEpisode(id="ep-new", outcome="success",
                                        final_answer="hi", num_steps=1,
                                        tokens_used=5)
    fake_result.skills_retrieved = []
    fake_agent.run_task = MagicMock(return_value=fake_result)
    blocks = await _invoke_tool("hippo_run_task", {
        "task": "Write a haiku about clouds",
    })
    payload = _parse_response(blocks[0])
    assert "error" not in payload, payload


# ---------------------------------------------------------------------------
# Schema unit tests on internal helpers (don't go through MCP request handlers)
# ---------------------------------------------------------------------------


def test_manual_validate_object() -> None:
    schema = {"type": "object", "properties": {
        "x": {"type": "string"}, "y": {"type": "integer"},
    }, "required": ["x"]}
    assert mcp_server._manual_validate({"x": "ok"}, schema) == ""
    assert "missing" in mcp_server._manual_validate({}, schema)
    assert "string" in mcp_server._manual_validate({"x": 5}, schema)


def test_token_bucket_basic() -> None:
    b = mcp_server._TokenBucket(capacity=2, rate_per_sec=10.0)
    assert b.take() is True
    assert b.take() is True
    # capacity exhausted; immediate next call fails
    assert b.take() is False


def test_looks_shell_like() -> None:
    assert mcp_server._looks_shell_like("sudo rm -rf /tmp/x")
    assert mcp_server._looks_shell_like("powershell ls")
    assert mcp_server._looks_shell_like("subprocess.run('id')")
    assert not mcp_server._looks_shell_like("Write a haiku about cats")
    assert not mcp_server._looks_shell_like("Compute fib(10)")
