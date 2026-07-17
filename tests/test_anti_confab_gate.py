"""Cycle #138 (2026-05-18) — anti-confab gate on write.

Aurelio direttiva 2026-05-18: "rendiamo davvero cazzuto e perfetto questo
programma" + "Auto-validate gate on write" (cycle 138 design choice
post-FASE-0+1 lab empirico).

Background:
* Cycle 128-131 wired L1/L1.5/L1.7 detectors as POST-STORE warnings
  (observability events only, no blocking, no status change).
* Cycle 132-137 wired the L2 RECONCILER (passive scrubber + mark_orphaned
  mutator) — operates on the existing corpus, not on new writes.
* GAP: a fresh hippo_remember call carrying "Cycle 999 SHIPPED to main"
  with verified_by=[] still lands as ``status='model_claim'`` exactly
  as before. No write-time discipline.

Cycle 138 closes the loop with a MULTI-TIER GATE (engram/anti_confab_gate.py
+ wiring inside the hippo_remember handler):

  validate ∈ {"off", "fast" (default), "full"}
      off  → no checks, bypass everything (escape hatch).
      fast → L1 + L1.5 + L1.7 detectors (sub-ms, pure functions).
      full → fast + validate_claim cycle #70 (~13ms mean, p95 40ms).

  gate_mode ∈ {"downgrade" (default), "reject"}
      downgrade → if any L1 fires, persist BUT force status='provisional'
                   so default recall hides the suspect fact.
                   if L3 contradicted, ALSO downgrade (preserves audit).
      reject    → if L3 contradicted, refuse to persist; return rejected:true
                   with advice + contradicting_fact_id. L1 still downgrades.

  force_persist=True → bypass gate entirely (admin / migration / replay).

  Env override: ENGRAM_VALIDATE_DEFAULT="off"|"fast"|"full" — lets the
  operator flip the default without code change.

This file owns the FASE-2 RED tests. Implementation lives in
engram/anti_confab_gate.py + a small splice in mcp_server.py's
hippo_remember handler.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from verimem import mcp_server
from verimem.semantic import Fact, SemanticMemory

# ---------------------------------------------------------------------------
# Test infra: real SemanticMemory + FakeAgent. We invoke the MCP handler
# directly so we exercise the real wiring (schema + handler), not a mock.
# ---------------------------------------------------------------------------


@pytest.fixture
def real_sm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SemanticMemory:
    sm = SemanticMemory(db_path=tmp_path / "s.db")

    class _FakeAgent:
        def __init__(self) -> None:
            self.semantic = sm

    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent())
    # Keep tests deterministic: gate uses env var as default unless tool
    # arg overrides — make sure the env doesn't bleed in.
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


# ---------------------------------------------------------------------------
# Schema introspection — surface contract for the operator/agent.
# ---------------------------------------------------------------------------


class TestSchemaSurfacesGateKnobs:
    @pytest.mark.asyncio
    async def test_hippo_remember_schema_exposes_validate_kwarg(
        self, real_sm: SemanticMemory,
    ) -> None:
        tools = await mcp_server.list_tools()
        remember = next(t for t in tools if t.name == "hippo_remember")
        props = remember.inputSchema["properties"]
        assert "validate" in props, (
            "cycle 138: hippo_remember schema must expose 'validate' "
            "enum ('off'|'fast'|'full', default 'fast')"
        )
        assert props["validate"].get("default") == "fast", (
            "cycle 138: 'fast' must be the default — sub-ms L1 detectors "
            "stay on by default; opt-in 'full' for validate_claim."
        )
        # Must list at least the three canonical levels.
        enum = set(props["validate"].get("enum") or [])
        assert {"off", "fast", "full"} <= enum

    @pytest.mark.asyncio
    async def test_hippo_remember_schema_exposes_gate_mode_and_force(
        self, real_sm: SemanticMemory,
    ) -> None:
        tools = await mcp_server.list_tools()
        remember = next(t for t in tools if t.name == "hippo_remember")
        props = remember.inputSchema["properties"]
        assert "gate_mode" in props, (
            "cycle 138: 'gate_mode' ('downgrade'|'reject') must be "
            "selectable per call."
        )
        assert props["gate_mode"].get("default") == "downgrade", (
            "cycle 138: downgrade is the conservative default — preserves "
            "audit trail (provisional vs reject)."
        )
        assert "force_persist" in props, (
            "cycle 138: 'force_persist' bool escape hatch must exist for "
            "migration / replay / admin flows."
        )
        assert props["force_persist"].get("default") is False


# ---------------------------------------------------------------------------
# Fast (L1 keyword) tier — sub-ms detector wiring.
# ---------------------------------------------------------------------------


class TestFastL1Downgrade:
    @pytest.mark.asyncio
    async def test_shipped_keyword_without_commit_ref_downgrades_to_provisional(
        self, real_sm: SemanticMemory,
    ) -> None:
        out = await _invoke("hippo_remember", {
            "proposition": "Cycle 999 SHIPPED to production main",
            "topic": "t/test",
            "verified_by": [],  # explicit: no commit/pr/file/git ref
            # default validate=fast, gate_mode=downgrade
        })
        assert out.get("ok") is True
        assert out.get("status") == "quarantined", (
            "cycle 138: L1 shipped-keyword + empty verified_by must "
            f"force status='provisional', got {out.get('status')!r}"
        )
        # Surface the warning to the caller so an LLM sees the issue.
        warnings = out.get("anti_confab_warnings") or []
        assert any(w.get("layer") == "L1" for w in warnings), (
            "cycle 138: response must echo at least one L1 warning"
        )
        # The fact must actually exist on disk with provisional status.
        f = real_sm.get(out["id"])
        assert f is not None and f.status == "quarantined"

    @pytest.mark.asyncio
    async def test_diagnosis_keyword_without_test_ref_downgrades(
        self, real_sm: SemanticMemory,
    ) -> None:
        out = await _invoke("hippo_remember", {
            "proposition": "Bug #99 DIAGNOSED as race in cache.py",
            "topic": "t/test",
            "verified_by": [],
        })
        assert out.get("ok") is True
        assert out.get("status") == "quarantined", (
            "cycle 138: L1.5 diagnosis keyword without test ref must "
            "downgrade to provisional."
        )

    @pytest.mark.asyncio
    async def test_clean_proposition_persists_as_model_claim(
        self, real_sm: SemanticMemory,
    ) -> None:
        out = await _invoke("hippo_remember", {
            "proposition": "User Aurelio prefers Italian responses",
            "topic": "preferences/aurelio",
            "verified_by": [],
        })
        assert out.get("ok") is True
        assert out.get("status") == "model_claim", (
            "cycle 138: clean proposition (no SHIPPED/MERGED/etc keyword) "
            "must persist as model_claim — default behavior preserved."
        )

    @pytest.mark.asyncio
    async def test_shipped_with_commit_ref_stays_model_claim(
        self, real_sm: SemanticMemory,
    ) -> None:
        out = await _invoke("hippo_remember", {
            "proposition": "Cycle 138 SHIPPED to main",
            "topic": "t/test",
            "verified_by": ["commit:abc1234def", "pr:#80:merged"],
        })
        assert out.get("ok") is True
        assert out.get("status") == "model_claim", (
            "cycle 138: SHIPPED keyword + commit ref present => no L1 "
            "trigger => stays at default model_claim."
        )


# ---------------------------------------------------------------------------
# Full (L1 + L3 validate_claim) tier — opt-in deeper checks.
# ---------------------------------------------------------------------------


class TestFullL3ContradictionGate:
    @pytest.mark.asyncio
    async def test_l3_contradicted_year_reject_mode_blocks_persist(
        self, real_sm: SemanticMemory,
    ) -> None:
        # Seed memory with a counter-claim that establishes the year.
        real_sm.store(Fact(
            id="seed-tonegawa",
            proposition="Tonegawa Susumu won the Nobel Prize in 1987",
            topic="science/biology",
            confidence=0.9,
            verified_by=["url:wikipedia.org/Tonegawa"],
            status="verified",
        ))
        out = await _invoke("hippo_remember", {
            # Contradicts the seed: same subject (Tonegawa, Nobel), wrong year
            "proposition": "Tonegawa Susumu won the Nobel Prize in 2014",
            "topic": "science/biology",
            "validate": "full",
            "gate_mode": "reject",
        })
        assert out.get("rejected") is True, (
            "cycle 138: validate=full + gate_mode=reject must refuse a "
            "year-disjoint contradiction. Got: " + str(out)
        )
        # Caller needs actionable advice.
        assert "advice" in out and out["advice"]
        # Evidence must point to the seed fact so the LLM can self-correct.
        ev = out.get("contradicting_fact_ids") or []
        assert "seed-tonegawa" in ev

    @pytest.mark.asyncio
    async def test_l3_contradicted_downgrade_mode_persists_as_provisional(
        self, real_sm: SemanticMemory,
    ) -> None:
        real_sm.store(Fact(
            id="seed-anthropic",
            proposition="Anthropic Skills launched in 2025",
            topic="tech/anthropic",
            confidence=0.9,
            verified_by=["url:anthropic.com/news"],
            status="verified",
        ))
        out = await _invoke("hippo_remember", {
            "proposition": "Anthropic Skills launched in 2026",
            "topic": "tech/anthropic",
            "validate": "full",
            "gate_mode": "downgrade",
        })
        # In downgrade mode we still persist, but force provisional.
        assert out.get("ok") is True
        assert out.get("status") == "quarantined"
        # The L3 contradiction must still surface in warnings.
        warnings = out.get("anti_confab_warnings") or []
        assert any(w.get("layer") == "L3" for w in warnings)


# ---------------------------------------------------------------------------
# Escape hatches: validate=off, force_persist=True, env override.
# ---------------------------------------------------------------------------


class TestEscapeHatches:
    @pytest.mark.asyncio
    async def test_validate_off_skips_all_checks(
        self, real_sm: SemanticMemory,
    ) -> None:
        out = await _invoke("hippo_remember", {
            "proposition": "Cycle 999 SHIPPED to production main",
            "topic": "t/test",
            "verified_by": [],
            "validate": "off",
        })
        assert out.get("ok") is True
        assert out.get("status") == "model_claim", (
            "cycle 138: validate=off must bypass L1 — status stays at "
            "default model_claim even though the keyword would trigger."
        )
        assert not (out.get("anti_confab_warnings") or [])

    @pytest.mark.asyncio
    async def test_force_persist_bypasses_reject(
        self, real_sm: SemanticMemory,
    ) -> None:
        real_sm.store(Fact(
            id="seed-lightrag",
            proposition="LightRAG was published by HKUDS in 2024",
            topic="research/rag",
            confidence=0.9,
            verified_by=["url:arxiv"],
            status="verified",
        ))
        out = await _invoke("hippo_remember", {
            "proposition": "LightRAG was published by HKUDS in 2099",
            "topic": "research/rag",
            "validate": "full",
            "gate_mode": "reject",
            "force_persist": True,
        })
        # force_persist overrides reject; we still warn but persist.
        assert out.get("ok") is True
        # The fact lands in the corpus despite the contradiction.
        f = real_sm.get(out["id"])
        assert f is not None

    @pytest.mark.asyncio
    async def test_env_override_disables_default_gate(
        self, real_sm: SemanticMemory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ENGRAM_VALIDATE_DEFAULT", "off")
        out = await _invoke("hippo_remember", {
            # No validate kwarg → must read env "off".
            "proposition": "Cycle 999 SHIPPED to production main",
            "topic": "t/test",
            "verified_by": [],
        })
        assert out.get("status") == "model_claim", (
            "cycle 138: ENGRAM_VALIDATE_DEFAULT=off must disable gate "
            "without explicit per-call kwarg."
        )


# ---------------------------------------------------------------------------
# Cycle 138 critic-orchestrator counterexample (job 1a80633751dc1459,
# 2026-05-18, confidence 0.92): quarantined was excluded from the cache
# SQL branch ONLY. The legacy SQL branch (recall with topic filter) and
# search_facts both leaked the suspect rows back to the caller.
#
# These regression tests pin BOTH read paths so any future schema change
# that adds a hidden status enum forces a parallel patch here.
# ---------------------------------------------------------------------------


class TestQuarantinedHiddenAcrossReadPaths:
    """Cycle 138 critic-fix: every read path must hide quarantined by
    default — cache (covered), legacy SQL (with topic filter), and
    search_facts. The opt-in flag ``include_orphaned`` SHOULD continue
    to expose orphaned only; a separate switch governs quarantined."""

    def test_quarantined_hidden_in_recall_legacy_path_with_topic(
        self, tmp_path: Path,
    ) -> None:
        sm = SemanticMemory(db_path=tmp_path / "s.db")
        sm.store(Fact(
            id="quar-recall",
            proposition="Cycle 999 SHIPPED to production main",
            topic="t/critic", confidence=0.9,
            verified_by=[], status="quarantined",
        ))
        # Live (non-quarantined) baseline so the SQL filter has something
        # to NOT-drop — keeps the test from passing on an empty result.
        sm.store(Fact(
            id="live-recall",
            proposition="Cycle 999 SHIPPED to production main",
            topic="t/critic", confidence=0.9,
            verified_by=["commit:abcd1234", "pr:#80:merged"],
            status="model_claim",
        ))
        # topic=... forces the legacy SQL branch (cache is cache_eligible
        # only when topic is None).
        hits = sm.recall("Cycle 999 SHIPPED", k=5, topic="t/critic")
        ids = {f.id for f, _ in hits}
        assert "quar-recall" not in ids, (
            "cycle 138 critic-fix: legacy SQL recall path with topic "
            f"must hide status='quarantined' (got ids={ids!r}). The "
            "cache path was patched in cycle 138 v1 but the legacy "
            "SQL branch only excludes 'orphaned' — needs parity."
        )
        # And the live model_claim must still be there.
        assert "live-recall" in ids

    def test_quarantined_hidden_in_search_facts(
        self, tmp_path: Path,
    ) -> None:
        sm = SemanticMemory(db_path=tmp_path / "s.db")
        sm.store(Fact(
            id="quar-search",
            proposition="Cycle 888 SHIPPED to production main",
            topic="t/critic", confidence=0.9,
            verified_by=[], status="quarantined",
        ))
        sm.store(Fact(
            id="live-search",
            proposition="Cycle 888 SHIPPED to production main",
            topic="t/critic", confidence=0.9,
            verified_by=["commit:dead1234"],
            status="model_claim",
        ))
        hits = sm.search_facts("SHIPPED", topic="t/critic")
        ids = {f.id for f in hits}
        assert "quar-search" not in ids, (
            "cycle 138 critic-fix: search_facts must hide quarantined "
            f"by default (got ids={ids!r}). hippo_facts_search → "
            "search_facts → must not surface gate-flagged rows."
        )
        assert "live-search" in ids
