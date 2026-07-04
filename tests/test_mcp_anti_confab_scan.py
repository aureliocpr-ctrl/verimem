"""Cycle #133 (2026-05-17) — MCP tool hippo_anti_confab_scan.

Exposes cycle 132 scan_orphaned_facts via MCP. Detection-only, no
mutation. Returns per-category counts + sample fact_ids.

Test plan:
1. Tool is registered in list_tools.
2. inputSchema declares the 4 documented properties.
3. Handler scans corpus + returns dict with summary + categories.
4. limit_per_category caps fact_ids returned per category.
5. include_* toggles skip a category.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from unittest.mock import MagicMock

import pytest


@dataclass
class _FakeFact:
    id: str
    proposition: str
    verified_by: list[str] = field(default_factory=list)


class TestSchema:
    @pytest.mark.asyncio
    async def test_tool_registered_in_list_tools(
        self, tmp_path, monkeypatch,
    ) -> None:
        monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(tmp_path / "audit.log"))
        from engram import mcp_server
        tools = await mcp_server.list_tools()
        names = {t.name for t in tools}
        assert "hippo_anti_confab_scan" in names

    @pytest.mark.asyncio
    async def test_schema_has_expected_properties(
        self, tmp_path, monkeypatch,
    ) -> None:
        monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(tmp_path / "audit.log"))
        from engram import mcp_server
        tools = await mcp_server.list_tools()
        tool = next(t for t in tools if t.name == "hippo_anti_confab_scan")
        props = tool.inputSchema.get("properties", {})
        for k in (
            "limit_per_category",
            "include_shipped",
            "include_diagnosis",
            "include_task_state",
        ):
            assert k in props, f"inputSchema missing {k}"


class TestHandler:
    @pytest.mark.asyncio
    async def test_scan_returns_categorized_orphans(
        self, tmp_path, monkeypatch,
    ) -> None:
        monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(tmp_path / "audit.log"))
        from engram import mcp_server

        fake_sm = MagicMock()
        fake_sm.all = MagicMock(return_value=[
            _FakeFact("s1", "X is SHIPPED", ["tool:a"]),
            _FakeFact("d1", "Bug #1 search miss", ["obs:s"]),
            _FakeFact("t1", "Cycle 9 da chiudere", []),
            _FakeFact("ok", "User lives in Italy", []),
        ])
        fake_agent = MagicMock()
        fake_agent.semantic = fake_sm

        monkeypatch.setattr(mcp_server, "_ag", lambda: fake_agent)

        result = await mcp_server.call_tool(
            "hippo_anti_confab_scan", {},
        )
        payload = json.loads(result[0].text)
        cats = payload["categories"]
        assert cats["shipped"]["count"] == 1
        assert "s1" in cats["shipped"]["fact_ids"]
        assert cats["diagnosis"]["count"] == 1
        assert "d1" in cats["diagnosis"]["fact_ids"]
        assert cats["task_state"]["count"] == 1
        assert "t1" in cats["task_state"]["fact_ids"]
        assert "summary" in payload
        assert "3" in payload["summary"]

    @pytest.mark.asyncio
    async def test_include_toggles_skip_category(
        self, tmp_path, monkeypatch,
    ) -> None:
        monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(tmp_path / "audit.log"))
        from engram import mcp_server

        fake_sm = MagicMock()
        fake_sm.all = MagicMock(return_value=[
            _FakeFact("s1", "X is SHIPPED", ["tool:a"]),
            _FakeFact("d1", "Bug #1", ["obs:s"]),
        ])
        fake_agent = MagicMock()
        fake_agent.semantic = fake_sm
        monkeypatch.setattr(mcp_server, "_ag", lambda: fake_agent)

        result = await mcp_server.call_tool(
            "hippo_anti_confab_scan",
            {"include_diagnosis": False},
        )
        payload = json.loads(result[0].text)
        assert payload["categories"]["shipped"]["count"] == 1
        assert payload["categories"]["diagnosis"]["count"] == 0

    @pytest.mark.asyncio
    async def test_limit_per_category_caps_fact_ids(
        self, tmp_path, monkeypatch,
    ) -> None:
        monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(tmp_path / "audit.log"))
        from engram import mcp_server

        # 30 shipped orphans — limit_per_category=5 must cap output.
        fake_sm = MagicMock()
        fake_sm.all = MagicMock(return_value=[
            _FakeFact(f"s{i}", "X is SHIPPED", ["tool:a"])
            for i in range(30)
        ])
        fake_agent = MagicMock()
        fake_agent.semantic = fake_sm
        monkeypatch.setattr(mcp_server, "_ag", lambda: fake_agent)

        result = await mcp_server.call_tool(
            "hippo_anti_confab_scan",
            {"limit_per_category": 5},
        )
        payload = json.loads(result[0].text)
        assert payload["categories"]["shipped"]["count"] == 30
        assert len(payload["categories"]["shipped"]["fact_ids"]) == 5
