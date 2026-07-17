"""Cycle #119 (2026-05-17) — Wire cycle 116/117/118 into MCP handlers.

Aurelio direttiva: "memoria AI-driven pilotata da te". I cycle 116/117/118
hanno costruito i meccanismi ma il critic-orchestrator review (cycle 116)
ha confermato: **nessun production caller li usa ancora** — sono opt-in
extension points dormienti.

Cycle 119 wire ufficiale:
1. `hippo_remember` MCP → passa un default coherence_hook a
   `SemanticMemory.store()` che emette `BUS.emit("coherence_warning",
   ...)` per ogni `CoherenceWarning`. NO mutation, solo segnalazione.
2. `hippo_facts_recall` MCP → accetta nuovo arg ``trust_signals: bool=
   False`` e quando True espone verdict + age_days + n_contradictions
   per ogni item nel payload.

Test plan (focused, mock-based to avoid global state coupling):
* `hippo_remember` handler chiama `a.semantic.store(...,
  coherence_hook=callable)` non None.
* `hippo_facts_recall` con `trust_signals=False` (default): payload
  NON contiene `verdict`/`age_days`.
* `hippo_facts_recall` con `trust_signals=True`: payload contiene
  `verdict`/`age_days`/`n_contradictions` per item.
"""
from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from verimem.semantic import Fact
from verimem.trust_signal import TrustSignal


class TestRememberWiresCoherenceHook:
    """`hippo_remember` calls `store(coherence_hook=callable)`."""

    @pytest.mark.asyncio
    async def test_hippo_remember_passes_coherence_hook_kwarg(
        self, tmp_path, monkeypatch,
    ) -> None:
        """The handler must pass a coherence_hook (callable) to
        SemanticMemory.store. We capture the call args via a mock."""
        monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(tmp_path / "audit.log"))
        from verimem import mcp_server

        # Fake semantic memory with the relevant interface.
        fake_sm = MagicMock()
        fake_sm.store = MagicMock(return_value=False)  # was_replaced=False
        # Fake agent containing the fake semantic.
        fake_agent = MagicMock()
        fake_agent.semantic = fake_sm

        monkeypatch.setattr(mcp_server, "_ag", lambda: fake_agent)

        result = await mcp_server.call_tool(
            "hippo_remember",
            {"proposition": "Test fact for hook wiring",
             "topic": "t", "confidence": 0.9},
        )
        assert result, "expected a non-empty MCP response"
        # store() must have been called at least once.
        assert fake_sm.store.called
        # The kwargs of the LAST call must include coherence_hook as
        # something callable (or None — we accept both, but verify the
        # kwarg was passed explicitly).
        call_kwargs = fake_sm.store.call_args.kwargs
        assert "coherence_hook" in call_kwargs, (
            "hippo_remember must pass coherence_hook= explicitly to store()"
        )
        hook = call_kwargs["coherence_hook"]
        assert callable(hook), (
            "coherence_hook must be a callable so the hook actually runs"
        )


class TestRecallTrustSignalsExposure:
    """`hippo_facts_recall` payload exposes verdict when
    trust_signals=True."""

    @pytest.mark.asyncio
    async def test_default_payload_omits_trust_fields(
        self, tmp_path, monkeypatch,
    ) -> None:
        monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(tmp_path / "audit.log"))
        from verimem import mcp_server

        # The handler calls a.semantic.recall(...). For
        # trust_signals=False it should get 2-tuples and the payload
        # must NOT include verdict/age_days.
        fact = Fact(
            id="f-1", proposition="X uses 5MB", topic="t",
            confidence=0.9, status="model_claim", created_at=time.time(),
        )
        fake_sm = MagicMock()
        fake_sm.recall = MagicMock(return_value=[(fact, 0.91)])
        fake_agent = MagicMock()
        fake_agent.semantic = fake_sm

        monkeypatch.setattr(mcp_server, "_ag", lambda: fake_agent)

        result = await mcp_server.call_tool(
            "hippo_facts_recall",
            {"query": "X memory", "k": 5},
        )
        payload = json.loads(result[0].text)
        assert payload["items"], "expected at least one hit"
        for item in payload["items"]:
            assert "verdict" not in item
            assert "age_days" not in item

    @pytest.mark.asyncio
    async def test_trust_signals_true_includes_verdict(
        self, tmp_path, monkeypatch,
    ) -> None:
        monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(tmp_path / "audit.log"))
        from verimem import mcp_server

        fact = Fact(
            id="f-1", proposition="X uses 5MB", topic="t",
            confidence=0.9, status="model_claim", created_at=time.time(),
        )
        signal = TrustSignal(
            verdict="trusted", age_days=0.5, n_contradictions=0,
            is_superseded=False, details="status=model_claim",
        )
        fake_sm = MagicMock()
        # When trust_signals=True the handler must call recall with
        # trust_signals=True; we return 3-tuples to mirror the real API.
        fake_sm.recall = MagicMock(return_value=[(fact, 0.91, signal)])
        fake_agent = MagicMock()
        fake_agent.semantic = fake_sm

        monkeypatch.setattr(mcp_server, "_ag", lambda: fake_agent)

        result = await mcp_server.call_tool(
            "hippo_facts_recall",
            {"query": "X memory", "k": 5, "trust_signals": True},
        )
        payload = json.loads(result[0].text)
        assert payload["items"], "expected at least one hit"
        # The handler must forward trust_signals=True to recall().
        recall_kwargs = fake_sm.recall.call_args.kwargs
        assert recall_kwargs.get("trust_signals") is True, (
            "hippo_facts_recall must forward trust_signals=True to recall()"
        )
        # And the payload must expose the verdict + age + n_contradictions.
        for item in payload["items"]:
            assert "verdict" in item, "missing verdict on hit"
            assert item["verdict"] == "trusted"
            assert "age_days" in item
            assert "n_contradictions" in item
            assert item["n_contradictions"] == 0


class TestFactsRecallSchemaExposesTrustSignals:
    """Cycle #121 (2026-05-17) — Aurelio direttiva: "memoria AI-driven
    pilotata da te, lab profittevole".

    Cycle 119 wire ha aggiunto runtime support per ``trust_signals=True``
    al handler (linea 9301: ``arguments.get("trust_signals", False)``) ma
    il flag NON è dichiarato in ``inputSchema``. Conseguenza: i client
    MCP che fanno ``tools/list`` introspection non sanno che il flag
    esiste e quindi non lo usano. Cycle 117 effort sprecato lato API.

    Test gap: ``list_tools()`` must expose ``trust_signals`` property
    nel inputSchema del tool ``hippo_facts_recall`` perché i client lo
    scoprano automaticamente.
    """

    @pytest.mark.asyncio
    async def test_schema_lists_trust_signals_property(
        self, tmp_path, monkeypatch,
    ) -> None:
        monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(tmp_path / "audit.log"))
        from verimem import mcp_server

        tools = await mcp_server.list_tools()
        recall_tool = next(
            (t for t in tools if t.name == "hippo_facts_recall"), None,
        )
        assert recall_tool is not None, "hippo_facts_recall must be registered"

        schema = recall_tool.inputSchema
        props = schema.get("properties", {})
        assert "trust_signals" in props, (
            "Cycle #121: hippo_facts_recall.inputSchema must declare "
            "trust_signals as a boolean property so MCP clients can "
            "discover it via tools/list introspection."
        )
        ts_schema = props["trust_signals"]
        assert ts_schema.get("type") == "boolean", (
            "trust_signals must be type=boolean"
        )
        # Default false preserves backward compat (legacy 2-tuple payload).
        assert ts_schema.get("default") is False, (
            "trust_signals must default to False (legacy payload format)"
        )
