"""Cycle 2026-05-27 round 12 F-fix — MCP-level provenance args propagation.

Closes the gap between the unit-level trusted-hook bypass (see
test_anti_confab_gate_trusted_hook_bypass.py) and the real MCP wiring.
The unit tests prove `run_validation_gate(writer_role=..., meta_narrative=...)`
behaves correctly; THESE tests prove the `hippo_remember` MCP handler
exposes those knobs to callers and persists them as provenance columns
on the stored fact (schema v6).

Without this, the unit-level bypass is unreachable from the API and the
pre-compact hook would have to keep using the SQL-UPDATE workaround.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from engram import mcp_server
from engram.semantic import SemanticMemory


@pytest.fixture
def real_sm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SemanticMemory:
    sm = SemanticMemory(db_path=tmp_path / "s.db")

    class _FakeAgent:
        def __init__(self) -> None:
            self.semantic = sm

    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent())
    monkeypatch.delenv("ENGRAM_VALIDATE_DEFAULT", raising=False)
    return sm


async def _invoke(name: str, arguments: dict | None = None) -> dict[str, Any]:
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


_RETROSPECTIVE_NARRATIVE = (
    "SESSION RECAP 2026-05-27: SHIPPED 11 L1.x detectors, "
    "all tests COMPLETO. AUTOMATED auto-Dream. MONITORED via "
    "dashboard. Authorized by Aurelio post-restart."
)


class TestSchemaSurfacesProvenance:
    """The MCP tool schema must advertise writer_role and meta_narrative."""

    @pytest.mark.asyncio
    async def test_writer_role_in_schema(self, real_sm: SemanticMemory):
        tools = await mcp_server.list_tools()
        remember = next(t for t in tools if t.name == "hippo_remember")
        props = remember.inputSchema["properties"]
        assert "writer_role" in props, (
            "F-fix: writer_role must be exposed on hippo_remember"
        )
        enum = set(props["writer_role"].get("enum") or [])
        assert {
            "agent_inference", "user", "system_hook", "trusted_hook",
        } <= enum
        assert props["writer_role"].get("default") == "agent_inference"

    @pytest.mark.asyncio
    async def test_meta_narrative_in_schema(self, real_sm: SemanticMemory):
        tools = await mcp_server.list_tools()
        remember = next(t for t in tools if t.name == "hippo_remember")
        props = remember.inputSchema["properties"]
        assert "meta_narrative" in props, (
            "F-fix: meta_narrative must be exposed on hippo_remember"
        )
        assert props["meta_narrative"].get("type") == "boolean"
        assert props["meta_narrative"].get("default") is False


class TestProvenancePropagatesToGate:
    """MCP args propagate end-to-end → trusted-hook bypass at gate."""

    @pytest.mark.asyncio
    async def test_trusted_hook_via_mcp_is_failclosed_without_token(
        self, real_sm: SemanticMemory,
    ) -> None:
        """Security fix 2026-06-02 (sorelle loop): writer_role + meta_narrative
        are client-spoofable via MCP arguments, so the MCP path deliberately
        NEVER supplies the server-side ENGRAM_HOOK_TOKEN. Without the token the
        trusted-hook bypass is fail-closed: the gate runs the L1.x detectors
        and DEMOTES the narrative to 'quarantined' instead of keeping 'verified'.

        (Was: test_trusted_hook_bypass_via_mcp, which asserted the unconditional
        bypass — it crystallised the spoof later proven empirically in
        tests/test_store_trusted_provenance_spoof.py.)"""
        out = await _invoke("hippo_remember", {
            "proposition": _RETROSPECTIVE_NARRATIVE,
            "topic": "handoff/pre-compact-test",
            "status": "verified",
            "verified_by": ["session:test:2026-05-27"],
            "writer_role": "system_hook",
            "meta_narrative": True,
        })
        assert out.get("ok") is True
        assert out.get("status") == "quarantined", (
            f"MCP is fail-closed (no hook_token) → a spoofed trusted writer_role "
            f"must NOT keep status=verified; got {out.get('status')}. "
            f"Warnings={out.get('anti_confab_warnings')}"
        )
        # The L1.x detectors now FIRE (bypass NOT taken without the token).
        warns = out.get("anti_confab_warnings") or []
        assert warns, (
            "fail-closed MCP path must surface L1.x warnings (no silent bypass)"
        )

    @pytest.mark.asyncio
    async def test_default_writer_role_still_gated(
        self, real_sm: SemanticMemory,
    ) -> None:
        """Without writer_role override (default agent_inference), the
        gate fires and quarantines retrospective narrative."""
        out = await _invoke("hippo_remember", {
            "proposition": _RETROSPECTIVE_NARRATIVE,
            "topic": "handoff/pre-compact-test",
            "status": "verified",
        })
        assert out.get("ok") is True
        assert out.get("status") == "quarantined", (
            f"agent_inference + no meta_narrative must quarantine; "
            f"got {out.get('status')}"
        )
        warns = out.get("anti_confab_warnings") or []
        assert len(warns) >= 3, (
            f"expected 3+ L1.x layers fire; got {len(warns)}"
        )

    @pytest.mark.asyncio
    async def test_attacker_with_user_role_cannot_bypass(
        self, real_sm: SemanticMemory,
    ) -> None:
        """Attacker tries to inject handoff/ topic + meta_narrative=True
        but writer_role='user' → still gated (defense in depth)."""
        out = await _invoke("hippo_remember", {
            "proposition": _RETROSPECTIVE_NARRATIVE,
            "topic": "handoff/pre-compact-malicious",
            "status": "verified",
            "writer_role": "user",
            "meta_narrative": True,
        })
        assert out.get("ok") is True
        assert out.get("status") == "quarantined", (
            "attacker with user role + handoff topic + meta_narrative "
            "MUST still be quarantined"
        )


class TestProvenancePersistedInDB:
    """Schema v6 columns must contain the supplied writer_role/meta_narrative."""

    @pytest.mark.asyncio
    async def test_provenance_columns_persisted(
        self, real_sm: SemanticMemory, tmp_path: Path,
    ) -> None:
        out = await _invoke("hippo_remember", {
            "proposition": _RETROSPECTIVE_NARRATIVE,
            "topic": "handoff/pre-compact-persist-test",
            "status": "verified",
            "writer_role": "system_hook",
            "meta_narrative": True,
        })
        fact_id = out.get("id")
        assert fact_id, f"expected fact id returned; got {out}"

        # Direct SQL inspection — verify schema v6 columns wrote correctly.
        conn = sqlite3.connect(str(real_sm.db_path), timeout=5)
        cur = conn.cursor()
        cur.execute(
            "SELECT writer_role, meta_narrative, status FROM facts "
            "WHERE id = ?",
            (fact_id,),
        )
        row = cur.fetchone()
        conn.close()
        assert row is not None, f"fact {fact_id} not found in DB"
        assert row[0] == "system_hook", (
            f"writer_role must persist; got {row[0]}"
        )
        assert row[1] == 1, (
            f"meta_narrative must persist as 1; got {row[1]}"
        )
        # Security fix 2026-06-02: the columns still persist the supplied
        # provenance, but the MCP path is fail-closed (no hook_token) so the
        # spoofed trusted-hook write is DEMOTED to 'quarantined', not 'verified'.
        assert row[2] == "quarantined", (
            f"MCP fail-closed: spoofed trusted-hook write must be demoted, "
            f"not kept verified; got {row[2]}"
        )

    @pytest.mark.asyncio
    async def test_default_provenance_columns_are_safe(
        self, real_sm: SemanticMemory,
    ) -> None:
        """Callers that don't pass writer_role/meta_narrative still write
        valid defaults (no NULL on NOT NULL columns)."""
        out = await _invoke("hippo_remember", {
            "proposition": "Just a normal fact about something boring.",
            "topic": "notes/random",
        })
        fact_id = out.get("id")
        assert fact_id

        conn = sqlite3.connect(str(real_sm.db_path), timeout=5)
        cur = conn.cursor()
        cur.execute(
            "SELECT writer_role, meta_narrative FROM facts WHERE id = ?",
            (fact_id,),
        )
        row = cur.fetchone()
        conn.close()
        assert row[0] == "agent_inference"
        assert row[1] == 0
