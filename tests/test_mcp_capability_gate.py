"""Cycle 2026-05-27 round 15 P0.5 — capability matrix gating runtime.

Closes Aurelio audit gap "capability matrix exists but NO runtime consumer".

Pre-fix: tool_registry.py is dictionary-only documentation. The MCP
dispatcher in mcp_server.py dispatches every tool call without consulting
the registry. Unknown tools execute (fail-OPEN at the dispatcher level
even though the registry default is fail-CLOSED). DESTRUCTIVE tools
execute without explicit confirmation. No mandatory audit on call.

Post-fix: a `_capability_gate(name, arguments)` helper runs at the top
of `call_tool()`. Behavior:

  - READ-only tools in GATING_BYPASS_LIST: skip gate (efficiency).
  - DESTRUCTIVE / requires_confirm: deny unless `_user_confirmed=true`.
  - Unknown tools (fail-closed): deny unless `_capability_override=true`.
  - Every gated call writes a structured audit row.

Gemini cross-LLM validation (cycle 14 ask_gemini job): "Hard-block sempre.
Un warning verrebbe ignorato e annullerebbe lo scopo del gate. Sistema
deve fallire in modo rumoroso quando policy viene violata."

This module verifies the contract on the REAL MCP dispatcher (uses the
production handler wired through @server.call_tool()).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from verimem import mcp_server
from verimem.semantic import Fact, SemanticMemory


@pytest.fixture
def real_sm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SemanticMemory:
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(
        id="captest00abcd",
        proposition="Capability gate test fact",
        topic="test/cap_gate",
        confidence=0.9,
        verified_by=[],
        status="model_claim",
    ))

    class _FakeAgent:
        def __init__(self) -> None:
            self.semantic = sm

    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent())
    monkeypatch.delenv("ENGRAM_VALIDATE_DEFAULT", raising=False)
    # Cycle 15 FIX 6: default OFF in dev. Tests for gate ENFORCEMENT
    # must opt-in by setting the env var. This fixture flips it on so
    # the rest of the suite exercises the enforcing behaviour.
    monkeypatch.setenv("ENGRAM_CAPABILITY_GATE", "enforce")
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


class TestCapabilityGatePresent:
    """The helper must exist and be wired into the dispatcher."""

    def test_capability_gate_function_exists(self):
        assert hasattr(mcp_server, "_capability_gate"), (
            "mcp_server must expose _capability_gate helper"
        )

    def test_gating_bypass_list_defined(self):
        assert hasattr(mcp_server, "GATING_BYPASS_LIST"), (
            "mcp_server must define GATING_BYPASS_LIST"
        )
        bypass = mcp_server.GATING_BYPASS_LIST
        # Read-only common tools should be in the bypass list for efficiency.
        for required in ("hippo_facts_search", "hippo_facts_recall",
                          "hippo_undo_list"):
            assert required in bypass, (
                f"{required} should be in GATING_BYPASS_LIST (read-only)"
            )


class TestGateBlocksDestructive:
    """DESTRUCTIVE tools (requires_confirm=True) must be blocked w/o flag."""

    @pytest.mark.asyncio
    async def test_destructive_without_flag_denied(
        self, real_sm: SemanticMemory,
    ):
        out = await _invoke("hippo_fact_forget", {"fact_id": "captest00abcd"})
        # The gate should deny with a clear actionable message.
        assert out.get("ok") is False or "error" in out, (
            f"hippo_fact_forget MUST be denied without _user_confirmed; "
            f"got {out}"
        )
        # Error must mention how to override.
        body = json.dumps(out)
        assert "_user_confirmed" in body or "confirm" in body.lower(), (
            f"deny message must hint at _user_confirmed override; got {body}"
        )

    @pytest.mark.asyncio
    async def test_destructive_with_flag_proceeds(
        self, real_sm: SemanticMemory,
    ):
        out = await _invoke("hippo_fact_forget", {
            "fact_id": "captest00abcd",
            "_user_confirmed": True,
        })
        # Once the gate is satisfied the underlying handler runs.
        # (The handler may return ok=True if delete succeeded.)
        assert out.get("ok") is True or out.get("id") == "captest00abcd"


class TestGateBlocksUnknown:
    """Unknown tools fail-CLOSED unless explicitly overridden."""

    @pytest.mark.asyncio
    async def test_unknown_tool_denied(self, real_sm: SemanticMemory):
        out = await _invoke("hippo_does_not_exist_xyz", {})
        # The dispatcher will reject either via capability gate OR via
        # the "unknown tool" branch. Either way the user sees an error.
        body = json.dumps(out)
        assert "error" in body.lower() or out.get("ok") is False, (
            f"unknown tool must be denied; got {out}"
        )

    def test_capability_override_unlocks_unknown(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        """Cycle 15 FIX 2 (critic counterexample 0.9): _capability_override
        must unlock unknown tools INDEPENDENTLY from _user_confirmed (the
        two flags signal different decisions)."""
        monkeypatch.setenv("ENGRAM_CAPABILITY_GATE", "enforce")
        from verimem.mcp_server import _capability_gate
        # _capability_override=true → unknown tool passes gate.
        ok, msg = _capability_gate(
            "hippo_does_not_exist_xyz",
            {"_capability_override": True},
        )
        assert ok is True, (
            f"unknown tool with _capability_override MUST pass gate; "
            f"got ok={ok} msg={msg}"
        )

    def test_user_confirmed_alone_does_not_unlock_unknown(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        """Reverse contract: _user_confirmed alone should NOT unlock an
        unknown tool — that flag is for known DESTRUCTIVE classifications,
        not for fail-closed registry misses."""
        monkeypatch.setenv("ENGRAM_CAPABILITY_GATE", "enforce")
        from verimem.mcp_server import _capability_gate
        ok, msg = _capability_gate(
            "hippo_does_not_exist_xyz",
            {"_user_confirmed": True},
        )
        assert ok is False, (
            "unknown tool with only _user_confirmed must STILL be blocked; "
            "the registry-miss decision requires _capability_override"
        )
        assert msg is not None and "_capability_override" in msg, (
            f"deny message must instruct caller to use _capability_override; "
            f"got msg={msg}"
        )


class TestModeToggle:
    """Cycle 15 FIX 6 (Aurelio mandate dev-friendly): env var toggle."""

    def test_default_is_off(self, monkeypatch: pytest.MonkeyPatch):
        """No env var → gate is OFF (dev productivity)."""
        monkeypatch.delenv("ENGRAM_CAPABILITY_GATE", raising=False)
        from verimem.mcp_server import _capability_gate
        # Even a fully unknown + destructive call passes when gate is off.
        ok, msg = _capability_gate("hippo_anything_xyz", {})
        assert ok is True, (
            "default (env var unset) MUST be OFF (allow-all dev mode)"
        )

    def test_off_explicit(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("ENGRAM_CAPABILITY_GATE", "0")
        from verimem.mcp_server import _capability_gate
        ok, _ = _capability_gate("hippo_anything_xyz", {})
        assert ok is True

    def test_enforce_mode_blocks(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("ENGRAM_CAPABILITY_GATE", "enforce")
        from verimem.mcp_server import _capability_gate
        ok, msg = _capability_gate("hippo_unknown_xyz", {})
        assert ok is False
        assert msg is not None

    def test_warn_mode_allows_but_audits(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        """warn mode: audit deny signal but allow execution."""
        monkeypatch.setenv("ENGRAM_CAPABILITY_GATE", "warn")
        captured: list = []

        def _capture(name, cap, arguments, decision, reason=""):
            captured.append({"decision": decision, "reason": reason})

        monkeypatch.setattr(
            mcp_server, "_audit_capability_call", _capture, raising=False,
        )
        from verimem.mcp_server import _capability_gate
        ok, msg = _capability_gate("hippo_unknown_xyz", {})
        assert ok is True, "warn mode must allow"
        # But the audit row still records a deny decision for analytics.
        denies = [c for c in captured if c["decision"] == "deny"]
        assert len(denies) >= 1, (
            f"warn mode must STILL emit deny audit row; got {captured}"
        )


class TestBypassListSkipsGate:
    """Read-only tools in GATING_BYPASS_LIST run without confirmation flags."""

    @pytest.mark.asyncio
    async def test_facts_search_no_flag_needed(self, real_sm: SemanticMemory):
        out = await _invoke("hippo_facts_search", {"query": "capability"})
        # Should succeed without _user_confirmed.
        assert out.get("ok") is not False, (
            f"hippo_facts_search bypass-listed should run unblocked; got {out}"
        )

    @pytest.mark.asyncio
    async def test_undo_list_no_flag_needed(self, real_sm: SemanticMemory):
        out = await _invoke("hippo_undo_list", {})
        assert out.get("ok") is True


class TestAuditLogWritten:
    """Every gated call (allow OR deny) must produce an audit row."""

    @pytest.mark.asyncio
    async def test_deny_emits_audit(
        self, real_sm: SemanticMemory, monkeypatch: pytest.MonkeyPatch,
    ):
        events: list = []
        # Stub the audit emitter to capture events without writing files.
        original_audit = getattr(mcp_server, "_audit_capability_call", None)

        def _capture(name, cap, arguments, decision, reason=""):
            events.append({
                "name": name, "decision": decision, "reason": reason,
                "risk": cap.risk_level,
            })
            if original_audit:
                original_audit(name, cap, arguments, decision, reason)

        monkeypatch.setattr(
            mcp_server, "_audit_capability_call", _capture, raising=False,
        )
        await _invoke("hippo_fact_forget", {"fact_id": "captest00abcd"})
        # Audit must record at least one deny event for the destructive tool.
        denies = [e for e in events if e["decision"] == "deny"]
        assert len(denies) >= 1, (
            f"deny on hippo_fact_forget must emit audit row; got {events}"
        )
