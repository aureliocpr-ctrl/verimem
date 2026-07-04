"""H2 (2026-07-04 security sweep): `sandbox_exec` must be behind the same
shell-permission gate as `hippo_run_task`.

The sweep found: the MCP `sandbox_exec` handler ran SandboxedShell().execute()
with no `_shell_perm_enabled()` check, and `_resolve_sandbox_mode()` defaults
to 'legacy' (shell=True). So any MCP client reached a shell-exec surface by
default. `hippo_run_task` already refuses shell-like content unless
HIPPO_ENABLE_SHELL is set; `sandbox_exec` must match — an execution tool is
exactly the surface a public-package user should opt into, not get for free.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

import engram.mcp_server as mcp_server

pytestmark = pytest.mark.asyncio


async def _invoke(name: str, arguments: dict[str, Any]):
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(method="tools/call", params=CallToolRequestParams(
        name=name, arguments=arguments))
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    return [c.text for c in payload.content if hasattr(c, "text")]


async def test_sandbox_exec_refused_when_shell_perm_off(monkeypatch):
    monkeypatch.delenv("HIPPO_ENABLE_SHELL", raising=False)
    monkeypatch.setenv("HIPPO_MCP_DISABLE_RATELIMIT", "1")
    out = await _invoke("sandbox_exec", {"cmd": "echo hello"})
    assert out, "no response from sandbox_exec"
    body = out[0].lower()
    assert "perm_shell" in body or "hippo_enable_shell" in body, out[0]


async def test_sandbox_exec_allowed_when_shell_perm_on(monkeypatch):
    monkeypatch.setenv("HIPPO_ENABLE_SHELL", "1")
    monkeypatch.setenv("HIPPO_MCP_DISABLE_RATELIMIT", "1")
    out = await _invoke("sandbox_exec", {"cmd": "echo hello", "dry_run": True})
    assert out
    # a dry-run of an allowlisted command must NOT be refused for perm reasons
    assert "perm_shell" not in out[0].lower()
    parsed = json.loads(out[0])
    assert parsed.get("ok") is True
