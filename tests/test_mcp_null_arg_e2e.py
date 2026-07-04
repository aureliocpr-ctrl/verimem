"""Audit#2 A10 — END-TO-END proof through the real MCP dispatcher (closing the
gap I'd only unit-tested before: _drop_none_args was tested in isolation, the
WIRING was only read, not exercised). hippo_facts_recent does
`top_k=int(arguments.get("top_k", 20))` OUTSIDE its try/except, so a client
sending {"top_k": null} pre-fix hit int(None) -> TypeError. This drives the
actual call_tool path and ALSO falsifies: neutering _drop_none_args must rebreak
it, proving the fix is load-bearing.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from engram import mcp_server


def _fake_agent():
    fake_sm = MagicMock()
    fake_sm.list_facts = MagicMock(return_value=[])
    agent = MagicMock()
    agent.semantic = fake_sm
    return agent


@pytest.mark.asyncio
async def test_null_top_k_through_dispatch_uses_default(monkeypatch):
    monkeypatch.setattr(mcp_server, "_ag", _fake_agent)

    # WITH the fix: {"top_k": null} is normalized away → default 20 → ok payload.
    res = await mcp_server.call_tool("hippo_facts_recent", {"top_k": None})
    payload = json.loads(res[0].text)
    assert "error" not in payload, f"null top_k crashed through dispatch: {payload}"

    # FALSIFY: neuter _drop_none_args (simulate pre-fix) → int(None) must fail,
    # whether the dispatcher returns an error envelope or lets TypeError escape.
    monkeypatch.setattr(mcp_server, "_drop_none_args", lambda a: a)
    crashed = False
    try:
        res2 = await mcp_server.call_tool("hippo_facts_recent", {"top_k": None})
        crashed = "error" in json.loads(res2[0].text)
    except TypeError:
        crashed = True
    assert crashed, "fix is vacuous: null top_k did NOT fail even with _drop_none_args neutered"
