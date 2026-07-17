"""Cycle #137 (2026-05-17 sera) — MCP wire test for hippo_anti_confab_apply.

The handler must:
  1. Be listed in list_tools().
  2. With dry_run=True (default), return the prospective fact_ids
     without mutating the corpus.
  3. With dry_run=False, actually call SemanticMemory.mark_orphaned()
     for each detected fact and report applied counts.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from verimem import mcp_server
from verimem.semantic import Fact, SemanticMemory


@pytest.fixture
def real_semantic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SemanticMemory:
    """A real SemanticMemory with 3 confabulation-prone facts pre-loaded."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    # Three facts that L1 detector will flag (SHIPPED without commit ref).
    for fid, prop in [
        ("orphan-1", "Cycle X has been SHIPPED to production"),
        ("orphan-2", "Feature Y was MERGED yesterday"),
        ("clean-3", "Generic note about temperature"),
    ]:
        sm.store(Fact(
            id=fid, proposition=prop, topic="t/test",
            confidence=0.9, verified_by=[],
            status="model_claim",
        ))

    class _FakeAgent:
        def __init__(self) -> None:
            self.semantic = sm

    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent())
    return sm


async def _invoke(name: str, arguments: dict | None = None) -> dict:
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    text = next(c.text for c in payload.content if hasattr(c, "text"))
    return json.loads(text)


class TestApplyDryRunDefault:
    @pytest.mark.asyncio
    async def test_dry_run_default_no_mutation(
        self, real_semantic: SemanticMemory,
    ) -> None:
        out = await _invoke("hippo_anti_confab_apply", {})
        assert out["dry_run"] is True
        # Two L1-prone facts detected, no actual mutation.
        assert out["total_scanned"] >= 2
        # The shipped category should list both orphan ids.
        shipped_ids = set(out["categories"]["shipped"]["fact_ids"])
        assert {"orphan-1", "orphan-2"} <= shipped_ids
        # No mutation: corpus statuses unchanged.
        f1 = real_semantic.get("orphan-1")
        f2 = real_semantic.get("orphan-2")
        assert f1 is not None and f1.status == "model_claim"
        assert f2 is not None and f2.status == "model_claim"


class TestApplyMutates:
    @pytest.mark.asyncio
    async def test_dry_run_false_flips_status(
        self, real_semantic: SemanticMemory,
    ) -> None:
        out = await _invoke(
            "hippo_anti_confab_apply", {"dry_run": False},
        )
        assert out["dry_run"] is False
        assert out["total_applied"] >= 2
        # Persisted: orphan-1 and orphan-2 now have status='orphaned'.
        f1 = real_semantic.get("orphan-1")
        f2 = real_semantic.get("orphan-2")
        assert f1 is not None and f1.status == "orphaned"
        assert f2 is not None and f2.status == "orphaned"
        # Clean fact untouched.
        f3 = real_semantic.get("clean-3")
        assert f3 is not None and f3.status == "model_claim"
        # And recall default-filter excludes the orphaned pair.
        hits = real_semantic.recall("SHIPPED", k=10)
        ids = {f.id for f, _ in hits}
        assert "orphan-1" not in ids
        assert "orphan-2" not in ids


class TestApplyListedInTools:
    @pytest.mark.asyncio
    async def test_tool_listed(
        self, real_semantic: SemanticMemory,
    ) -> None:
        tools = await mcp_server.list_tools()
        names = {t.name for t in tools}
        assert "hippo_anti_confab_apply" in names, (
            "cycle 137: MCP tool hippo_anti_confab_apply must be exposed"
        )
        # Schema sanity: dry_run defaults to True for safety.
        tool = next(t for t in tools if t.name == "hippo_anti_confab_apply")
        schema = tool.inputSchema
        assert schema["properties"]["dry_run"]["default"] is True
