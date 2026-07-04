"""Cycle #131 (2026-05-17) — L1.7 task-state detector tests.

Empirical motivation: cycle #129 replay residual gap is the 1/7 confab
that escaped L1 + L1.5 — confab #1 "Cycle 45 stress concurrency è il
prossimo da chiudere — candidato cycle dedicato per fix". Task-state
claim ('da chiudere'), saved without tracker reference.

L1.7 design: phrase ∈ TASK_STATE_PHRASES + verified_by con tracker ref
(pr:|issue:|task:|git:|commit:|gh:). Otherwise warning.
"""
from __future__ import annotations

import pytest

from engram.anti_confabulation import (
    TASK_STATE_PHRASES,
    detect_unsupported_task_state_claim,
)


class TestDetectUnsupportedTaskStateClaim:
    """L1.7: fact con task-state phrase DEVE avere tracker ref."""

    @pytest.mark.parametrize("phrase", sorted(TASK_STATE_PHRASES))
    def test_phrase_without_tracker_ref_yields_warning(
        self, phrase: str,
    ) -> None:
        prop = f"Cycle 999 task X {phrase} secondo memoria"
        warn = detect_unsupported_task_state_claim(
            proposition=prop,
            verified_by=["session:proactive_memory_hit"],
        )
        assert warn is not None, (
            f"L1.7: phrase '{phrase}' without tracker ref must warn."
        )

    def test_no_phrase_no_warning(self) -> None:
        warn = detect_unsupported_task_state_claim(
            proposition="The user lives in Italy.",
            verified_by=[],
        )
        assert warn is None

    def test_phrase_with_pr_ref_no_warning(self) -> None:
        warn = detect_unsupported_task_state_claim(
            proposition="Cycle 99 is open",
            verified_by=["pr:#42:state=open"],
        )
        assert warn is None

    def test_phrase_with_gh_ref_no_warning(self) -> None:
        warn = detect_unsupported_task_state_claim(
            proposition="Task da chiudere prossimo cycle",
            verified_by=["gh:issue/12:open"],
        )
        assert warn is None

    def test_phrase_with_commit_ref_no_warning(self) -> None:
        """Commit ref also counts as tracker — closing commit links task
        to verifiable state."""
        warn = detect_unsupported_task_state_claim(
            proposition="Task is closed",
            verified_by=["commit:abc1234:closes_#42"],
        )
        assert warn is None


class TestEmpiricalReplayConfab1TaskState:
    """Cycle 115.F false flag su cycle #45 (confab #1, task-state).
    Must be caught by L1.7."""

    def test_replay_confab1_cycle45_da_chiudere(self) -> None:
        warn = detect_unsupported_task_state_claim(
            proposition=(
                "Cycle 45 stress concurrency è il prossimo da chiudere "
                "— candidato cycle dedicato per fix."
            ),
            verified_by=["session:2026-05-17:proactive_memory_hit"],
        )
        assert warn is not None


class TestSemanticStoreWiresL17Warning:
    """SemanticMemory.store() must log L1.7 warning."""

    def test_store_logs_l17_warning_on_task_state_without_tracker(
        self, tmp_path, caplog,
    ) -> None:
        import logging

        from engram.semantic import Fact, SemanticMemory

        sm = SemanticMemory(db_path=tmp_path / "s.db")
        fact = Fact(
            id="task-1",
            proposition="Cycle 99 da chiudere prossimo cycle dedicato",
            topic="test/cycle131",
            verified_by=["session:proactive_memory"],
            status="model_claim",
        )
        with caplog.at_level(logging.WARNING, logger="engram.semantic"):
            sm.store(fact)
        l17_messages = [
            r.getMessage() for r in caplog.records
            if "L1.7 anti-confabulation" in r.getMessage()
        ]
        assert l17_messages, (
            "Cycle #131: SemanticMemory.store() must log L1.7 warning "
            "for task-state claims without tracker refs."
        )
