"""Audit#2 2026-06-08 C-1: .claude-plugin/plugin.json's mcpServers description
hardcoded "Exposes 10 tools: <list>" while the server actually registers 228 —
a 22x undercount that an evaluator/investor reads first. The live registry
(len(list_tools())) is the single source of truth; the manifest must not
contradict it. Contract: the description carries NO fixed tool-count number
(drift-proof — any hardcoded N is wrong the instant a tool is added/removed),
and the server still registers a substantial toolset.
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from engram import mcp_server

_PLUGIN_JSON = Path(__file__).resolve().parents[1] / ".claude-plugin" / "plugin.json"


def test_plugin_manifest_makes_no_false_tool_count_claim():
    manifest = json.loads(_PLUGIN_JSON.read_text(encoding="utf-8"))
    desc = manifest["mcpServers"]["verimem"]["description"]
    m = re.search(r"\b(\d+)\s+tools?\b", desc)
    assert m is None, (
        f"plugin.json hardcodes a tool count ('{m.group(0)}') that drifts vs the "
        "live registry (real = len(list_tools())) — describe the toolset without "
        "a fixed number"
    )


def test_server_registers_substantial_toolset():
    n = len(asyncio.run(mcp_server.list_tools()))
    assert n > 50, f"expected a rich toolset, registry returned only {n}"
