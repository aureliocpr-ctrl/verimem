"""Regression: _has_personal_context must NOT fire on software homonyms (2026-06-20).

The full suite caught requalify_quarantined recovering a perf claim ("10x faster,
a real game changer") because _PERSONAL_CONTEXT matched "game" → the gate treated
the dev claim as a personal false-positive and un-quarantined it. "game changer" is
canonically a perf claim in this codebase (test_anti_confab_gate_l19_wire). Same
hazard for "class" (Python class) and "call" (function/API call). These weak
personal signals were pruned; the strong personal markers stay.
"""
from __future__ import annotations

from verimem.anti_confab_gate import _has_personal_context


def test_software_homonyms_are_not_personal() -> None:
    assert not _has_personal_context("this approach is 10x faster, a real game changer")
    assert not _has_personal_context("the UserAccount class writes the row")
    assert not _has_personal_context("the function call returns inside a transaction")


def test_real_personal_facts_still_detected() -> None:
    # the strong markers that the personal-FP recovery actually depends on
    assert _has_personal_context("dentist appointment on Monday")
    assert _has_personal_context("renew the medication prescription")
    assert _has_personal_context("dinner with my family this weekend")
    assert _has_personal_context("pay the rent and the gym subscription")
