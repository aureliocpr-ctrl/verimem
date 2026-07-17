"""Cycle 2026-05-27 round 13 P0.5 — capability matrix pytest."""
from __future__ import annotations

import pytest

from verimem.tool_registry import (
    DEFAULT_CAPABILITY,
    REGISTRY,
    CapabilityRegistry,
    ToolCapability,
    build_default_registry,
)


class TestInitialPopulation:
    def test_15_critical_tools_seeded(self):
        reg = build_default_registry()
        assert len(reg.all()) >= 15

    def test_destructive_tools_require_confirm_or_undo(self):
        reg = build_default_registry()
        for cap in reg.by_capability("DESTRUCTIVE"):
            # Either user must confirm, or the op must be undoable.
            assert cap.requires_confirm or cap.reversibility == "undoable", (
                f"DESTRUCTIVE tool {cap.name} must have confirm OR undoable; "
                f"got confirm={cap.requires_confirm} "
                f"reversibility={cap.reversibility}"
            )

    def test_critical_writes_memory_tools(self):
        reg = build_default_registry()
        ws = {c.name for c in reg.writes_memory()}
        for required in (
            "hippo_remember", "hippo_record_episode",
            "hippo_fact_forget", "hippo_fact_forget_with_undo",
        ):
            assert required in ws, f"{required} should writes_memory=True"


class TestLookup:
    def test_known_tool_returns_real_cap(self):
        cap = REGISTRY.get("hippo_fact_forget")
        assert cap.name == "hippo_fact_forget"
        assert cap.capability == "DESTRUCTIVE"
        assert cap.requires_confirm is True

    def test_unknown_tool_returns_default_with_name(self):
        cap = REGISTRY.get("ghost_unknown_tool_xyz")
        assert cap.name == "ghost_unknown_tool_xyz"
        assert cap.capability == DEFAULT_CAPABILITY.capability
        assert cap.risk_level == DEFAULT_CAPABILITY.risk_level
        assert "default" in cap.notes.lower()

    def test_unknown_tool_fails_closed(self):
        """Cycle 14 FIX 1 (agy audit High): unknown tools must be
        treated as critical/destructive/requires-confirm, NOT read-only."""
        cap = REGISTRY.get("brand_new_destructive_tool_xyz")
        # The 4 critical safety bits — fail-CLOSED, not fail-OPEN.
        assert cap.capability == "DESTRUCTIVE", (
            "fail-CLOSED: unknown tools must default to DESTRUCTIVE"
        )
        assert cap.risk_level == "critical", (
            "fail-CLOSED: unknown tools must default to critical risk"
        )
        assert cap.requires_confirm is True, (
            "fail-CLOSED: unknown tools must require user confirm"
        )
        assert cap.requires_sandbox is True, (
            "fail-CLOSED: unknown tools must route through sandbox"
        )


class TestFilters:
    def test_by_capability(self):
        reg = build_default_registry()
        reads = reg.by_capability("READ")
        names = {c.name for c in reads}
        assert "hippo_facts_search" in names
        assert "hippo_facts_recall" in names

    def test_by_risk_high(self):
        reg = build_default_registry()
        high = reg.by_risk("high")
        # hippo_fact_forget + hippo_decay_run + hippo_forget + hippo_run_task
        # are seeded high.
        names = {c.name for c in high}
        assert "hippo_fact_forget" in names

    def test_executes_command_filter(self):
        reg = build_default_registry()
        ec = reg.executes_command()
        names = {c.name for c in ec}
        assert "hippo_run_task" in names

    def test_requires_confirm_filter(self):
        reg = build_default_registry()
        rc = reg.requires_confirm()
        names = {c.name for c in rc}
        assert "hippo_fact_forget" in names
        assert "hippo_forget" in names


class TestExtensibility:
    def test_register_overwrites(self):
        reg = build_default_registry()
        new_cap = ToolCapability(
            name="hippo_fact_forget",  # known name
            capability="READ",  # downgrade
            risk_level="low",
            reversibility="yes",
        )
        reg.register(new_cap)
        got = reg.get("hippo_fact_forget")
        assert got.capability == "READ"
        assert got.risk_level == "low"

    def test_new_tool_registers(self):
        reg = CapabilityRegistry()
        new_cap = ToolCapability(
            name="my_new_tool",
            capability="EXECUTE",
            risk_level="critical",
            reversibility="no",
            requires_sandbox=True,
            executes_command=True,
        )
        reg.register(new_cap)
        got = reg.get("my_new_tool")
        assert got.capability == "EXECUTE"
        assert got.requires_sandbox is True
