"""Cycle #132 (2026-05-17) — L2 async reconciler tests (DETECTION V1).

L2 closes the historical-confabulation gap: facts saved BEFORE
cycle 128 in main don't get the write-time warning. The reconciler
walks the corpus and reports which existing facts would now trigger
a warning.

V1 is detection-only, no schema migration, no mutation. The output
is a structured report keyed by category.

Test plan:
1. Empty corpus → empty report.
2. Clean corpus (no anti-patterns) → empty report.
3. Mixed corpus with one shipped + one diagnosis + one task-state
   → report has each in the right category.
4. ``include_*=False`` toggles correctly skip a category.
5. Summarize returns sensible string.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from engram.anti_confabulation import (
    scan_orphaned_facts,
    summarize_scan,
)


@dataclass
class _FakeFact:
    id: str
    proposition: str
    verified_by: list[str] = field(default_factory=list)


class TestScanOrphanedFactsEmptyCorpus:
    def test_empty_iterable_yields_empty_report(self) -> None:
        report = scan_orphaned_facts([])
        assert report == {
            "shipped": [], "diagnosis": [], "task_state": [],
        }


class TestScanOrphanedFactsCleanCorpus:
    def test_no_confabulation_keywords_yields_empty(self) -> None:
        facts = [
            _FakeFact("a", "User lives in Italy.", []),
            _FakeFact("b", "Email is x@y.z.", []),
            _FakeFact("c", "Preferred editor is VS Code.", []),
        ]
        report = scan_orphaned_facts(facts)
        assert all(len(v) == 0 for v in report.values()), (
            "Clean corpus must produce empty per-category lists."
        )


class TestScanOrphanedFactsMixedCorpus:
    """Realistic corpus with one fact per anti-pattern category."""

    @pytest.fixture
    def corpus(self) -> list[_FakeFact]:
        return [
            # shipped — keyword SHIPPED + no commit ref
            _FakeFact(
                "f-shipped",
                "Cycle 999 X is SHIPPED in main PR #99",
                ["tool:agent:no_commit"],
            ),
            # diagnosis — BUG # + no test ref
            _FakeFact(
                "f-diag",
                "Bug #99 is search miss",
                ["observation:sintomo"],
            ),
            # task-state — phrase + no tracker ref
            _FakeFact(
                "f-task",
                "Cycle 99 da chiudere prossimo cycle",
                ["session:proactive_memory"],
            ),
            # clean
            _FakeFact("f-ok", "User lives in Italy.", []),
        ]

    def test_each_category_caught(self, corpus: list[_FakeFact]) -> None:
        report = scan_orphaned_facts(corpus)
        assert len(report["shipped"]) == 1
        assert report["shipped"][0][0] == "f-shipped"
        assert len(report["diagnosis"]) == 1
        assert report["diagnosis"][0][0] == "f-diag"
        assert len(report["task_state"]) == 1
        assert report["task_state"][0][0] == "f-task"

    def test_warning_msg_present_in_each(
        self, corpus: list[_FakeFact],
    ) -> None:
        report = scan_orphaned_facts(corpus)
        for cat in ("shipped", "diagnosis", "task_state"):
            assert all(msg for _fid, msg in report[cat]), (
                f"{cat}: each tuple must have a non-empty warning."
            )

    def test_clean_fact_not_in_any_category(
        self, corpus: list[_FakeFact],
    ) -> None:
        report = scan_orphaned_facts(corpus)
        for cat, items in report.items():
            for fid, _msg in items:
                assert fid != "f-ok", (
                    f"Clean fact must not appear in {cat}: {report}"
                )


class TestIncludeToggles:
    def test_include_shipped_false_skips_shipped(self) -> None:
        facts = [
            _FakeFact("s", "X is SHIPPED", ["tool:x"]),
            _FakeFact("d", "Bug #1", ["observation:y"]),
        ]
        report = scan_orphaned_facts(facts, include_shipped=False)
        assert report["shipped"] == []
        assert len(report["diagnosis"]) == 1

    def test_include_diagnosis_false_skips_diagnosis(self) -> None:
        facts = [
            _FakeFact("s", "X is SHIPPED", ["tool:x"]),
            _FakeFact("d", "Bug #1", ["observation:y"]),
        ]
        report = scan_orphaned_facts(facts, include_diagnosis=False)
        assert len(report["shipped"]) == 1
        assert report["diagnosis"] == []

    def test_include_task_state_false_skips_task_state(self) -> None:
        facts = [
            _FakeFact("t", "Cycle 9 da chiudere", []),
        ]
        report = scan_orphaned_facts(facts, include_task_state=False)
        assert report["task_state"] == []


class TestSummarizeScan:
    def test_empty_report(self) -> None:
        s = summarize_scan({
            "shipped": [], "diagnosis": [], "task_state": [],
        })
        assert "corpus clean" in s

    def test_one_per_category(self) -> None:
        report = {
            "shipped": [("a", "w1")],
            "diagnosis": [("b", "w2")],
            "task_state": [("c", "w3")],
        }
        s = summarize_scan(report)
        assert "3" in s
        assert "shipped=1" in s
        assert "diagnosis=1" in s
        assert "task_state=1" in s
