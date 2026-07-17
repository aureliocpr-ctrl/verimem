"""Cycle #134 (2026-05-17) — Live Dashboard BUS coverage GAP-FILL.

Aurelio direttiva 2026-05-17 (CEO): "scala il progetto" + "feature wow
integrata, push live sub-second, copertura totale (episodi+traces+skills+
lineage+facts+causal+bundles+audit), test E2E reali".

Audit pre-cycle (2026-05-17): la dashboard FastAPI esiste già con SSE su
``/api/events/stream`` (vedi ``engram/dashboard_routes/events.py``). Il
``BUS`` (``engram/observability.py:113``) emette già 92 event types
distinti. Gap reale identificato:

* ``hippo_remember`` NON emette ``fact_stored`` sul BUS → la dashboard
  non vede facts nuovi in real-time
* ``_audit()`` NON emette ``audit_tool_call`` sul BUS con latency_ms →
  la dashboard non vede il throughput cognitivo (cycle #115.A è scritto
  solo su JSONL mcp_audit.log)
* Detector L1/L1.5/L1.7 (cycle #128/#130/#131) NON emettono
  ``anti_confab_warning_l1*`` sul BUS → la dashboard non può colorare
  fact rossi in live

I test seguenti sono RED su main (verificato pre-commit). Diventano
GREEN nel medesimo cycle aggiungendo i 3 ``emit(...)`` mancanti.

Design: ZERO modifiche al contratto esistente. Aggiunte additive.
"""
from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from verimem.observability import BUS


def _collect_events(name_glob: str | None = None) -> list[tuple[str, dict[str, Any]]]:
    """Drain BUS history filtered by event name (post-test inspection)."""
    items = BUS.history(limit=1024)
    if name_glob is None:
        return [(e.name, e.payload) for e in items]
    if name_glob.endswith("*"):
        prefix = name_glob[:-1]
        return [(e.name, e.payload) for e in items if e.name.startswith(prefix)]
    return [(e.name, e.payload) for e in items if e.name == name_glob]


# ---------------------------------------------------------------------------
# Test 1 — hippo_remember emits fact_stored on BUS
# ---------------------------------------------------------------------------


class TestHippoRememberEmitsFactStored:
    """When hippo_remember handler succeeds, the BUS must receive a
    `fact_stored` event with at least {fact_id, topic, confidence}.

    RED on main: the handler calls _audit() but not emit("fact_stored").
    """

    @pytest.mark.asyncio
    async def test_remember_emits_fact_stored_event(
        self, tmp_path, monkeypatch,
    ) -> None:
        monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(tmp_path / "audit.log"))
        from verimem import mcp_server

        fake_sm = MagicMock()
        fake_sm.store = MagicMock(return_value=False)  # was_replaced=False
        fake_agent = MagicMock()
        fake_agent.semantic = fake_sm
        monkeypatch.setattr(mcp_server, "_ag", lambda: fake_agent)

        # Capture BUS events from this point forward.
        captured: list[tuple[str, dict[str, Any]]] = []
        BUS.subscribe("fact_stored", lambda e: captured.append((e.name, e.payload)))

        await mcp_server.call_tool(
            "hippo_remember",
            {"proposition": "Test fact for cycle 134 BUS coverage",
             "topic": "cycle134/test", "confidence": 0.91},
        )

        assert captured, (
            "cycle 134: hippo_remember handler must emit('fact_stored', ...) "
            "on the BUS so the live dashboard SSE stream picks it up. "
            "Found 0 events."
        )
        name, payload = captured[-1]
        assert name == "fact_stored"
        assert "fact_id" in payload, "payload must include fact_id"
        assert payload.get("topic") == "cycle134/test"
        assert payload.get("confidence") == pytest.approx(0.91)


# ---------------------------------------------------------------------------
# Test 2 — _audit() emits audit_tool_call with latency_ms
# ---------------------------------------------------------------------------


class TestAuditEmitsToolCallEvent:
    """Every _audit() call inside the request flow (where
    _REQUEST_START_NS is set) must additionally emit an
    `audit_tool_call` event on the BUS carrying {tool, outcome,
    latency_ms}. The dashboard uses this for throughput + p95 latency.

    RED on main: _audit writes JSONL only; no BUS emit happens.
    """

    def test_audit_with_timer_emits_bus_event(
        self, tmp_path, monkeypatch,
    ) -> None:
        monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(tmp_path / "audit.log"))
        from verimem.mcp_server import _REQUEST_START_NS, _audit

        captured: list[tuple[str, dict[str, Any]]] = []
        BUS.subscribe(
            "audit_tool_call", lambda e: captured.append((e.name, e.payload)),
        )

        token = _REQUEST_START_NS.set(time.monotonic_ns())
        try:
            time.sleep(0.020)  # 20 ms — well above any clock tick
            _audit("hippo_fake_tool", {"x": 1}, outcome="ok")
        finally:
            _REQUEST_START_NS.reset(token)

        assert captured, (
            "cycle 134: _audit must emit('audit_tool_call', ...) on the "
            "BUS when the request timer is set so the dashboard SSE "
            "picks up cognitive throughput. Got 0 events."
        )
        name, payload = captured[-1]
        assert name == "audit_tool_call"
        assert payload.get("tool") == "hippo_fake_tool"
        assert payload.get("outcome") == "ok"
        assert isinstance(payload.get("latency_ms"), float)
        assert payload["latency_ms"] >= 1.0


# ---------------------------------------------------------------------------
# Test 3 — anti-confab L1 detector emits warning on BUS
# ---------------------------------------------------------------------------


class TestAntiConfabL1EmitsWarning:
    """When hippo_remember stores a fact whose proposition trips the L1
    shipped-claim detector (cycle #128), the BUS must receive an
    `anti_confab_warning` event with {level=l1, fact_id, topic,
    proposition_excerpt}.

    RED on main: semantic.py logs the warning via _LOG.warning but never
    emits on the BUS — the dashboard can't show red banners in live.
    """

    @pytest.mark.asyncio
    async def test_shipped_claim_without_ref_emits_warning(
        self, tmp_path, monkeypatch,
    ) -> None:
        monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(tmp_path / "audit.log"))
        from verimem import mcp_server

        fake_sm = MagicMock()
        fake_sm.store = MagicMock(return_value=False)
        fake_agent = MagicMock()
        fake_agent.semantic = fake_sm
        monkeypatch.setattr(mcp_server, "_ag", lambda: fake_agent)

        captured: list[tuple[str, dict[str, Any]]] = []
        BUS.subscribe(
            "anti_confab_warning",
            lambda e: captured.append((e.name, e.payload)),
        )

        # No commit ref / no PR ref → L1 detector should fire.
        await mcp_server.call_tool(
            "hippo_remember",
            {
                "proposition": "Feature X is SHIPPED in production",
                "topic": "cycle134/test_l1",
                "confidence": 0.95,
            },
        )

        assert captured, (
            "cycle 134: hippo_remember must emit('anti_confab_warning', "
            "level='l1', ...) on the BUS when the L1 detector fires, so "
            "the live dashboard can flag suspect facts in red."
        )
        name, payload = captured[-1]
        assert name == "anti_confab_warning"
        assert payload.get("level") == "l1"
        assert payload.get("topic") == "cycle134/test_l1"
        # Excerpt must be non-empty; full text is up to the emitter.
        assert payload.get("proposition_excerpt"), "missing proposition_excerpt"


# ---------------------------------------------------------------------------
# Test 4 — coverage summary: at least 8 categories reachable via BUS
# ---------------------------------------------------------------------------


class TestEightCategoryCoverageContract:
    """Assert the BUS reaches the 8 dashboard-required event categories.

    This is a structural contract test (read existing emit calls in the
    source). It DOES NOT trigger handlers, so it stays fast and stable.
    """

    def test_bus_emit_names_cover_eight_dashboard_categories(self) -> None:
        # Inventario delle 8 categorie del design Aurelio cycle 134.
        required_categories = {
            "episode": {"episode_started", "episode_completed", "episode_stored"},
            "fact":     {"fact_stored"},                 # cycle 134 GREEN add
            "skill":    {"skill_promoted", "skill_synthesized",
                          "skill_retired", "skill_reactivated"},
            "lineage":  {"lineage_edge"},                # cycle 134 GREEN add
            "causal":   {"causal_chain"},                # cycle 134 GREEN add
            "bundle":   {"bundle_abstraction_done", "bundle_discovery_done"},
            "audit":    {"audit_tool_call"},             # cycle 134 GREEN add
            "anti_confab": {"anti_confab_warning",       # cycle 134 GREEN add
                             "coherence_warning"},
        }

        # Static AST scan of engram/ for emit("name", ...) calls.
        import ast
        import pathlib
        emitted_names: set[str] = set()
        engram_root = pathlib.Path(__file__).resolve().parents[1] / "engram"
        for src in engram_root.rglob("*.py"):
            try:
                tree = ast.parse(src.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "emit"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                ):
                    emitted_names.add(node.args[0].value)
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "emit"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                ):
                    emitted_names.add(node.args[0].value)

        missing_by_category: dict[str, set[str]] = {}
        for cat, names in required_categories.items():
            unreachable = names - emitted_names
            if unreachable:
                missing_by_category[cat] = unreachable

        assert not missing_by_category, (
            "cycle 134: the 8 dashboard categories must each have at "
            "least one source-level emit() reachable on the BUS. "
            f"Missing per category: {missing_by_category}"
        )
