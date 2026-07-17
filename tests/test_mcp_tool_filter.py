"""Cycle 176 (2026-05-22) — ENGRAM_MCP_TOOLS_PREFIX selective tool loading.

The MCP server exposes ~211 tools. At ~400 tokens/tool definition this
consumes ~48k tokens of every Claude Code session's context window (cycle
175 audit measured a 194,097-char list_tools body). Cycle 176 adds an env-
var-controlled prefix filter so users can opt into a curated subset,
reducing boot-time token consumption proportionally.

Spec compliance
---------------
  * Backward-compat: ``ENGRAM_MCP_TOOLS_PREFIX`` unset → ALL tools
    (current behaviour preserved byte-identical).
  * Filter is applied AFTER the full tool list is built, so
    ``call_tool()`` dispatch via ``_SCHEMAS_BY_TOOL`` still works for any
    tool name (the filter only affects DISCOVERY, not EXECUTION — clients
    that already know a tool name from a prior session can still call it).
  * Spec-compliant per MCP 2025-06-18+: servers MAY return any subset of
    their tools in ``tools/list``. No new method, no new field.

RED marker: ``from verimem.mcp_server import _allowed_tool_prefixes,
_filter_tools`` must fail on master.
"""
from __future__ import annotations

import pytest

# RED MARKER
from verimem.mcp_server import (
    _allowed_tool_prefixes,
    _filter_tools,
    list_tools,
)

# ---------------------------------------------------------------------------
# Unit: _allowed_tool_prefixes (env-var parser)
# ---------------------------------------------------------------------------


class TestAllowedToolPrefixes:
    def test_unset_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ENGRAM_MCP_TOOLS_PREFIX absent → None (no filter applied)."""
        monkeypatch.delenv("ENGRAM_MCP_TOOLS_PREFIX", raising=False)
        assert _allowed_tool_prefixes() is None

    def test_empty_string_returns_none(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Empty env → None (treat as unset for backward-compat)."""
        monkeypatch.setenv("ENGRAM_MCP_TOOLS_PREFIX", "")
        assert _allowed_tool_prefixes() is None

    def test_whitespace_only_returns_none(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ENGRAM_MCP_TOOLS_PREFIX", "   ")
        assert _allowed_tool_prefixes() is None

    def test_single_prefix(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ENGRAM_MCP_TOOLS_PREFIX", "hippo_facts_")
        assert _allowed_tool_prefixes() == {"hippo_facts_"}

    def test_multi_prefix_comma_split(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "ENGRAM_MCP_TOOLS_PREFIX",
            "hippo_facts_,hippo_skill_",
        )
        assert _allowed_tool_prefixes() == {
            "hippo_facts_", "hippo_skill_",
        }

    def test_whitespace_stripped_around_prefixes(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Tolerant parser: trim spaces around each comma-separated entry."""
        monkeypatch.setenv(
            "ENGRAM_MCP_TOOLS_PREFIX",
            " hippo_facts_ , hippo_skill_ ",
        )
        assert _allowed_tool_prefixes() == {
            "hippo_facts_", "hippo_skill_",
        }

    def test_empty_entries_dropped(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`,,hippo_facts_,,` should not produce empty-string prefixes."""
        monkeypatch.setenv(
            "ENGRAM_MCP_TOOLS_PREFIX",
            ",,hippo_facts_,,",
        )
        assert _allowed_tool_prefixes() == {"hippo_facts_"}


# ---------------------------------------------------------------------------
# Unit: _filter_tools (pure prefix-startswith match)
# ---------------------------------------------------------------------------


class _StubTool:
    """Minimal stub matching ``mcp.types.Tool.name`` for filter logic."""

    def __init__(self, name: str) -> None:
        self.name = name


_SAMPLE_TOOLS = [
    _StubTool("hippo_facts_search"),
    _StubTool("hippo_facts_recall"),
    _StubTool("hippo_skill_promote"),
    _StubTool("hippo_skill_retire"),
    _StubTool("hippo_recall"),
    _StubTool("hippo_remember"),
]


class TestFilterTools:
    def test_none_prefixes_returns_all_unchanged(self) -> None:
        """``None`` means no filter → identity behaviour."""
        out = _filter_tools(_SAMPLE_TOOLS, None)
        assert out == _SAMPLE_TOOLS

    def test_single_prefix_filters(self) -> None:
        out = _filter_tools(_SAMPLE_TOOLS, {"hippo_facts_"})
        assert {tool.name for tool in out} == {
            "hippo_facts_search", "hippo_facts_recall",
        }

    def test_multi_prefix_union(self) -> None:
        out = _filter_tools(
            _SAMPLE_TOOLS, {"hippo_facts_", "hippo_skill_"},
        )
        assert {tool.name for tool in out} == {
            "hippo_facts_search", "hippo_facts_recall",
            "hippo_skill_promote", "hippo_skill_retire",
        }

    def test_nonexistent_prefix_returns_empty(self) -> None:
        out = _filter_tools(_SAMPLE_TOOLS, {"nonexistent_"})
        assert out == []

    def test_case_sensitive_no_match(self) -> None:
        """Prefix match is case-sensitive (Python str.startswith semantics).

        Documenting the contract: callers must match the exact case used
        in tool registration. Avoids surprising semantics if we ever ship
        tools with mixed-case names.
        """
        out = _filter_tools(_SAMPLE_TOOLS, {"HIPPO_facts_"})
        assert out == []

    def test_empty_prefix_set_returns_empty(self) -> None:
        """An empty set (vs ``None``) means "filter with zero allowed
        prefixes" → no tool can match."""
        out = _filter_tools(_SAMPLE_TOOLS, set())
        assert out == []


# ---------------------------------------------------------------------------
# Integration: live list_tools() handler with env-var filtering
# ---------------------------------------------------------------------------


class TestListToolsFilterIntegration:
    async def test_no_env_returns_all_tools(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Backward-compat: unset env → server returns its full registry."""
        monkeypatch.delenv("ENGRAM_MCP_TOOLS_PREFIX", raising=False)
        tools = await list_tools()
        # Sanity: the server registers many tools; exact count may evolve
        # but MUST stay above 50 (cycle 175 audit measured 211).
        assert len(tools) > 50, (
            f"expected >50 tools when unfiltered, got {len(tools)}"
        )

    async def test_filter_hippo_facts_reduces_count(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ENGRAM_MCP_TOOLS_PREFIX", "hippo_facts_")
        tools = await list_tools()
        bad = [t.name for t in tools if not t.name.startswith("hippo_facts_")]
        assert bad == [], f"non-matching tool leaked into filter: {bad}"
        assert len(tools) > 0, "expected at least one hippo_facts_* tool"

    async def test_filter_nonexistent_returns_empty(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "ENGRAM_MCP_TOOLS_PREFIX",
            "totally_nonexistent_prefix_xyz_",
        )
        tools = await list_tools()
        assert tools == []
