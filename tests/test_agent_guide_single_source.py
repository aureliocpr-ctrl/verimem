"""`verimem agent-guide` (CLI) and the MCP `instructions` field teach agents from
ONE source (verimem/agent_guide.py) — mandate 2026-07-18. Two texts drifting
apart would give MCP-connected agents and CLI users different truths.
"""
from __future__ import annotations

from typer.testing import CliRunner

from verimem.agent_guide import AGENT_GUIDE_FULL, VERIMEM_AGENT_GUIDE


def test_mcp_instructions_come_from_the_single_source():
    import verimem.mcp_server as m
    assert m.server.create_initialization_options().instructions == VERIMEM_AGENT_GUIDE


def test_full_guide_extends_the_mcp_orientation():
    assert AGENT_GUIDE_FULL.startswith(VERIMEM_AGENT_GUIDE)
    for token in ("mcpServers", "from verimem import Memory", "verimem warmup"):
        assert token in AGENT_GUIDE_FULL, f"wiring section missing: {token!r}"


def test_cli_agent_guide_prints_the_guide():
    from verimem.cli import app
    res = CliRunner().invoke(app, ["agent-guide"])
    assert res.exit_code == 0, res.output
    for token in ("moat", "verimem_remember", "mcpServers", "abstention"):
        assert token.lower() in res.output.lower(), f"missing in output: {token!r}"
