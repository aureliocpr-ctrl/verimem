"""The sandbox cwd jail must never be handed an EMPTY allowlist (audit C2).

SandboxPolicy.allowed_cwds gates the jail with `if self.policy.allowed_cwds:`
(sandbox.py:511), so an EMPTY list disables the check completely. The MCP server
built `SandboxedShell()` with no policy at all, so the jail was always empty and
a caller-supplied `cwd` could point anywhere.

That is the second half of the RCE chain: strict mode allowlists
`python -m pytest`, and pytest imports conftest.py from the rootdir by design.
Point the cwd at a directory you control, and your conftest.py executes —
arbitrary code, in the mode that is supposed to be the hard one.

The jail itself was never broken. It was simply never switched on.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from verimem import mcp_server


async def _invoke(name: str, arguments: dict[str, Any]):
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(method="tools/call",
                          params=CallToolRequestParams(name=name,
                                                       arguments=arguments))
    res = await handler(req)
    payload = res.root if hasattr(res, "root") else res
    return json.loads([c.text for c in payload.content if hasattr(c, "text")][0])


@pytest.fixture()
def _shell_on(monkeypatch, tmp_path):
    monkeypatch.setenv("HIPPO_ENABLE_SHELL", "1")
    monkeypatch.setenv("ENGRAM_SANDBOX_MODE", "strict")
    jail = tmp_path / "jail"
    jail.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setenv("ENGRAM_SANDBOX_ALLOWED_CWDS", str(jail))
    return jail, outside


def test_the_wiring_never_produces_an_empty_jail(_shell_on):
    """An empty allowed_cwds silently disables the whole check."""
    jail, _outside = _shell_on
    policy = mcp_server._sandbox_policy()
    assert policy.allowed_cwds, "empty jail = the cwd check never runs"
    assert any(str(jail) == str(p) for p in policy.allowed_cwds)


def test_jail_defaults_to_the_process_cwd_when_unconfigured(monkeypatch):
    """Secure by default: with no env set the shell may only run where the
    server itself lives, not wherever a caller points it."""
    monkeypatch.delenv("ENGRAM_SANDBOX_ALLOWED_CWDS", raising=False)
    monkeypatch.delenv("ENGRAM_SANDBOX_CWD", raising=False)
    policy = mcp_server._sandbox_policy()
    assert policy.allowed_cwds, "unconfigured must still be jailed, not open"


@pytest.mark.asyncio
async def test_sandbox_exec_denies_a_cwd_outside_the_jail(_shell_on):
    """The exact RCE path: allowlisted pytest, attacker-chosen cwd."""
    _jail, outside = _shell_on
    payload = await _invoke("sandbox_exec", {
        "cmd": "python -m pytest .", "cwd": str(outside), "dry_run": True})
    blob = json.dumps(payload).lower()
    assert payload.get("action") == "deny", f"cwd escaped the jail: {payload}"
    assert "jail" in blob or "cwd" in blob


@pytest.mark.asyncio
async def test_sandbox_exec_still_works_inside_the_jail(_shell_on):
    """Narrowness: the jail must not break legitimate in-jail use."""
    jail, _outside = _shell_on
    payload = await _invoke("sandbox_exec", {
        "cmd": "git status", "cwd": str(jail), "dry_run": True})
    assert payload.get("action") != "deny", payload
