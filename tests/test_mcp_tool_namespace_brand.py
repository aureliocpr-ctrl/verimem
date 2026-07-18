"""The MCP tool namespace must honor the brand-named env var the README hands out.

README's `.mcp.json` quickstart sets ``VERIMEM_TOOL_NAMESPACE: "verimem"`` and
promises the tools appear as ``verimem_remember`` etc. But the code read ONLY the
legacy ``ENGRAM_TOOL_NAMESPACE`` — so a user who copy-pastes the documented
config got the old ``hippo_*`` names instead, silently. That is a broken headline
promise (the MCP surface is Verimem's primary pitch). Found walking the MCP
quickstart as an outside user, 2026-07-18.
"""
from __future__ import annotations

import verimem.mcp_server as mcp_server


def _tool(name):
    return mcp_server.t.Tool(name=name, description="x", inputSchema={"type": "object"})


def test_verimem_tool_namespace_from_readme_renames(monkeypatch):
    # exactly what the README .mcp.json sets
    monkeypatch.delenv("ENGRAM_TOOL_NAMESPACE", raising=False)
    monkeypatch.setenv("VERIMEM_TOOL_NAMESPACE", "verimem")
    out = mcp_server._apply_tool_namespace([_tool("hippo_remember"),
                                            _tool("hippo_facts_recall")])
    assert {x.name for x in out} == {"verimem_remember", "verimem_facts_recall"}


def test_legacy_engram_namespace_still_works(monkeypatch):
    # back-compat: existing 0.3.x/0.5.x host configs keep working
    monkeypatch.delenv("VERIMEM_TOOL_NAMESPACE", raising=False)
    monkeypatch.setenv("ENGRAM_TOOL_NAMESPACE", "verimem")
    out = mcp_server._apply_tool_namespace([_tool("hippo_remember")])
    assert out[0].name == "verimem_remember"


def test_unset_keeps_legacy_hippo_names(monkeypatch):
    monkeypatch.delenv("VERIMEM_TOOL_NAMESPACE", raising=False)
    monkeypatch.delenv("ENGRAM_TOOL_NAMESPACE", raising=False)
    out = mcp_server._apply_tool_namespace([_tool("hippo_remember")])
    assert out[0].name == "hippo_remember"
