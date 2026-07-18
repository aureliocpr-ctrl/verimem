"""The MCP server hands every connecting agent an onboarding guide via the
standard `instructions` field (returned on `initialize`) — mandate 2026-07-18:
"a mechanism that, on install, makes any new agent aware of how to use verimem".
Before this the server was Server("verimem") with no instructions, so a fresh
agent got zero orientation.
"""
from __future__ import annotations

import verimem.mcp_server as m


def test_server_exposes_nonempty_agent_instructions():
    opts = m.server.create_initialization_options()
    instr = (opts.instructions or "").lower()
    assert instr, "MCP server must expose a non-empty `instructions` onboarding field"
    # orients a fresh agent on the core concept + the key tools + the guarantee
    for token in ("moat", "verimem_remember", "verimem_trust_report", "abstain"):
        assert token in instr, f"agent onboarding guide missing: {token!r}"
