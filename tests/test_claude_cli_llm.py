"""Cycle #72 RED — ClaudeCLILLM subprocess provider.

Spec: docs/specs/c72-claude-cli-llm.md.

Cycle #71 ha implementato MCPSamplingLLM ma Claude Code MCP host
NON espone sampling/createMessage. Cycle #72 fa bypass: usa `claude -p`
subprocess che autentica OAuth subscription locale, ZERO API key.

4 RED minimi:
1. complete() con subprocess mocked → LLMResponse(text=result.result)
2. subprocess non-zero exit / timeout → LLMError raised
3. supports_tools() → False
4. handler hippo_consolidate fallback chain: sampling fail → CLI usage
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------- RED #1: complete() returns LLMResponse from subprocess ----


def test_claude_cli_llm_complete_basic(monkeypatch) -> None:
    """RED #1: complete() chiama subprocess.run con claude -p
    --output-format json, parsa stdout JSON, ritorna LLMResponse."""
    from verimem.llm import ClaudeCLILLM

    fake_stdout = json.dumps({
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": '{"name": "stub_skill", "trigger": "x", '
                  '"body": "y", "rationale": "z"}',
        "session_id": "fake-session",
        "duration_ms": 8500,
        "usage": {"input_tokens": 5, "output_tokens": 30},
        "modelUsage": {"claude-opus-4-7[1m]": {}},
    })

    captured: dict[str, Any] = {}

    def _fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["input"] = kwargs.get("input")
        captured["timeout"] = kwargs.get("timeout")
        result = MagicMock()
        result.returncode = 0
        result.stdout = fake_stdout
        result.stderr = ""
        return result

    monkeypatch.setattr(subprocess, "run", _fake_run)

    llm = ClaudeCLILLM()
    resp = llm.complete(
        "You are a helpful agent.",
        [{"role": "user", "content": "Generate a test skill JSON"}],
    )

    assert resp.text == (
        '{"name": "stub_skill", "trigger": "x", '
        '"body": "y", "rationale": "z"}'
    )
    # cmd starts with claude binary + -p flag
    assert captured["cmd"][0] in ("claude", "claude.exe")
    assert "-p" in captured["cmd"]
    assert "--output-format" in captured["cmd"]
    assert "json" in captured["cmd"]
    # System prompt concatenated to user content via stdin
    assert "You are a helpful agent." in captured["input"]
    assert "Generate a test skill JSON" in captured["input"]


# ---------- RED #2: non-zero exit / timeout → LLMError ---------------


def test_claude_cli_llm_nonzero_exit_raises(monkeypatch) -> None:
    """RED #2a: subprocess returncode != 0 → LLMError."""
    from verimem.llm import ClaudeCLILLM, LLMError

    def _fake_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 1
        result.stdout = ""
        result.stderr = "auth error: please run /login"
        return result

    monkeypatch.setattr(subprocess, "run", _fake_run)

    llm = ClaudeCLILLM()
    with pytest.raises(LLMError, match="claude CLI exited"):
        llm.complete("sys", [{"role": "user", "content": "q"}])


def test_claude_cli_llm_timeout_raises(monkeypatch) -> None:
    """RED #2b: subprocess.TimeoutExpired → LLMError with timeout msg."""
    from verimem.llm import ClaudeCLILLM, LLMError

    def _fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=10.0)

    monkeypatch.setattr(subprocess, "run", _fake_run)

    llm = ClaudeCLILLM(timeout_s=10.0)
    with pytest.raises(LLMError, match="timed out"):
        llm.complete("sys", [{"role": "user", "content": "q"}])


def test_claude_cli_llm_is_error_response_raises(monkeypatch) -> None:
    """RED #2c: stdout JSON has is_error=true → LLMError."""
    from verimem.llm import ClaudeCLILLM, LLMError

    fake_stdout = json.dumps({
        "type": "result",
        "is_error": True,
        "result": "Not logged in · Please run /login",
        "session_id": "x",
    })

    def _fake_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = fake_stdout
        result.stderr = ""
        return result

    monkeypatch.setattr(subprocess, "run", _fake_run)

    llm = ClaudeCLILLM()
    with pytest.raises(LLMError, match="claude CLI error"):
        llm.complete("sys", [{"role": "user", "content": "q"}])


# ---------- RED #3: supports_tools → False ---------------------------


def test_claude_cli_llm_no_tools_support() -> None:
    """RED #3: P0 no tool-use via subprocess."""
    from verimem.llm import ClaudeCLILLM

    llm = ClaudeCLILLM()
    assert llm.supports_tools() is False


# ---------- RED #4: hippo_consolidate fallback to CLI ----------------


@pytest.mark.asyncio
async def test_hippo_consolidate_fallback_to_cli_when_no_sampling(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """RED #4: hosted mode + no sampling capability + claude binary
    available → handler usa ClaudeCLILLM (verifica via mock subprocess
    che è stato invocato)."""
    import os

    from mcp.types import CallToolRequest, CallToolRequestParams

    from verimem import mcp_server

    monkeypatch.setenv("HIPPO_HOSTED", "1")

    # Fake agent with sleep engine
    class _FakeSleep:
        def __init__(self):
            self.llm = object()  # placeholder

        def cycle(self):
            class _R:
                n_episodes_replayed = 0
                n_clusters = 0
                n_nrem_skills = 0
                n_rem_skills = 0
                n_facts = 0
                promoted: list = []
                retired: list = []
                merged: list = []
                duration_s = 0.0
                tokens_used = 0
            return _R()

    class _FakeAgent:
        def __init__(self):
            self.sleep = _FakeSleep()

        def consolidate(self):
            return self.sleep.cycle()

    fake = _FakeAgent()
    monkeypatch.setattr(mcp_server, "_ag", lambda: fake)

    # Stub request_context.session WITHOUT sampling capability
    class _NoSamplingSession:
        def check_client_capability(self, cap):
            return False

        async def create_message(self, **kw):
            raise RuntimeError("should not be called")

    class _StubCtx:
        def __init__(self):
            self.session = _NoSamplingSession()

    monkeypatch.setattr(
        type(mcp_server.server), "request_context",
        property(lambda self: _StubCtx()),
        raising=False,
    )

    # Mock shutil.which to "find" claude
    monkeypatch.setattr(
        "shutil.which",
        lambda name: "C:\\fake\\claude.exe" if name == "claude" else None,
    )

    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(
            name="hippo_consolidate", arguments={},
        ),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    text = payload.content[0].text
    data = json.loads(text)

    # Acceptance: NOT refused with "host doesn't support sampling"
    err = data.get("error", "")
    assert "host MCP client does NOT support sampling" not in err, (
        f"should have fallen back to CLI, instead got: {err}"
    )
    # Check that llm_provider in response indicates claude_cli
    # (the handler reports which provider was used).
    assert data.get("llm_provider") == "claude_cli", (
        f"expected llm_provider='claude_cli', got: {data.get('llm_provider')}"
    )
