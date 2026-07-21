"""Cycle 184 (2026-05-23) — wire cycle-183 L1.8 FIX-family detector into
the anti_confab_gate orchestrator.

Cycle 183 shipped ``verimem.l1_extended_detector.detect_unsupported_fix_claim``
as a side-by-side composable module (no touch to gate). This cycle wires
it into ``run_validation_gate`` so the orchestrator surfaces L1.8 warnings
alongside the existing L1 / L1.5 / L1.7 family.

Contract
--------
* In tier ``fast`` and ``full``, a FIX-family claim
  (``FIXED/RESOLVED/PATCHED/REPAIRED``) without an evidence ref
  produces a warning of shape::

      {"layer": "L1.8", "reason": "...", "advice": "..."}

* The warning, when present, drives the existing ``downgrade``
  action path (same semantics as L1 / L1.5 / L1.7 — keyword
  heuristics never trigger ``reject``).

* In tier ``off``, no L1.8 check is run (consistent with the
  cycle-138 fast/full split).

* ``force_persist=True`` bypasses the downgrade decision but the
  warning is still surfaced for audit.

RED marker: ``run_validation_gate`` MUST return a warning with
``layer="L1.8"`` for FIX-without-evidence inputs in ``fast`` tier.
Pre-cycle-184 the gate ignores ``detect_unsupported_fix_claim``
entirely → test fails on master.
"""
from __future__ import annotations

import pytest

from verimem.anti_confab_gate import run_validation_gate


@pytest.fixture(autouse=True)
def _l1_strict(monkeypatch):
    # STRICT keyword-detector escalation is opt-in since the 2026-07-21 default
    # flip (keyword-only advisory by default); this file tests the strict path.
    monkeypatch.setenv("ENGRAM_L1_STRICT", "1")


class TestL18WiredIntoGate:
    def test_fix_claim_no_evidence_triggers_l18_warning(self) -> None:
        result = run_validation_gate(
            proposition="FIXED the race condition in the daemon",
            verified_by=["bash:some_unrelated_call"],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.8" in layers, (
            f"expected L1.8 in warnings, got layers={layers!r}"
        )

    def test_fix_claim_no_evidence_downgrades_action(self) -> None:
        """An L1.8-only warning still drives the standard downgrade path."""
        result = run_validation_gate(
            proposition="RESOLVED the database lock",
            verified_by=[],
            topic=None,
            agent=None,
            validate="fast",
        )
        assert result.action == "downgrade", (
            f"expected downgrade with L1.8 warning, got {result.action!r}"
        )

    def test_fix_claim_with_pytest_pass_ref_passes(self) -> None:
        """``pytest:test_x_PASS`` is sufficient evidence per cycle 183."""
        result = run_validation_gate(
            proposition="PATCHED the regex in validate_claim",
            verified_by=["pytest:test_validate_claim_PASS"],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.8" not in layers, (
            f"L1.8 should NOT fire with pytest:PASS ref, got {layers!r}"
        )
        assert result.action == "persist"

    def test_fix_claim_with_commit_ref_passes(self) -> None:
        result = run_validation_gate(
            proposition="REPAIRED the corrupted index",
            verified_by=["commit:abc123def", "file:engram/sem.py"],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.8" not in layers
        assert result.action == "persist"

    def test_no_l1_family_keyword_no_warning(self) -> None:
        """Plain text without any L1.X keyword → clean persist."""
        result = run_validation_gate(
            proposition="A generic observation about something.",
            verified_by=[],
            topic=None,
            agent=None,
            validate="fast",
        )
        assert result.warnings == []
        assert result.action == "persist"

    def test_off_tier_skips_l18(self) -> None:
        """validate='off' must NOT call detect_unsupported_fix_claim."""
        result = run_validation_gate(
            proposition="FIXED everything yesterday",
            verified_by=[],
            topic=None,
            agent=None,
            validate="off",
        )
        assert result.action == "persist"
        assert result.warnings == []

    def test_force_persist_surfaces_l18_warning_but_persists(self) -> None:
        """force_persist=True → action=persist but warnings still listed
        for audit (matches cycle 138 contract for L1/L1.5/L1.7)."""
        result = run_validation_gate(
            proposition="FIXED a critical bug",
            verified_by=[],
            topic=None,
            agent=None,
            validate="fast",
            force_persist=True,
        )
        assert result.action == "persist"
        layers = [w["layer"] for w in result.warnings]
        assert "L1.8" in layers, (
            f"L1.8 must still appear in warnings under force_persist; "
            f"got layers={layers!r}"
        )

    def test_l18_warning_carries_advice_field(self) -> None:
        """Cycle 183 FixClaimWarning has an ``advice`` field; gate must
        propagate it into the warning dict for caller display."""
        result = run_validation_gate(
            proposition="FIXED a race condition",
            verified_by=[],
            topic=None,
            agent=None,
            validate="fast",
        )
        l18 = next(
            (w for w in result.warnings if w["layer"] == "L1.8"), None,
        )
        assert l18 is not None
        assert "advice" in l18, f"L1.8 warning missing advice: {l18!r}"
        assert isinstance(l18["advice"], str) and l18["advice"], (
            f"advice must be non-empty str, got {l18!r}"
        )

    @pytest.mark.parametrize(
        "keyword",
        ["FIXED", "RESOLVED", "PATCHED", "REPAIRED"],
    )
    def test_each_fix_keyword_triggers_l18(self, keyword: str) -> None:
        result = run_validation_gate(
            proposition=f"{keyword} the production hotfix",
            verified_by=["bash:some_unrelated"],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.8" in layers, (
            f"keyword {keyword!r} did not produce L1.8: {layers!r}"
        )
