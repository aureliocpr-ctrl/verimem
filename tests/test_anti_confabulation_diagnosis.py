"""Cycle #130 (2026-05-17) — L1.5 diagnosis detector tests.

Aurelio direttiva: "lab + ricerca + sviluppo". Cycle 129 replay ha
empiricamente identificato 3/7 confabulations come ``diagnosis``
category (Bug #11 search miss, Bug #12 topic loss, Bug topic-loss
intermittent) — tutte saved con verified_by che descriveva il SINTOMO
non un test falsifying root cause.

L1.5 design: keyword ∈ {BUG #, DIAGNOSED, ROOT CAUSE, ...} +
verified_by con test-like ref (test:|pytest:|bash:|...) — altrimenti
warning.

Test plan TDD:
1. RED: pure detector emette warning su diagnosis senza test ref.
2. GREEN: negative cases (no keyword, OR test ref present) no warning.
3. Empirical: replica 3 confabulations storiche diagnosis-side e
   conferma cattura.
4. Wire: SemanticMemory.store() loggа L1.5 warning.
"""
from __future__ import annotations

import pytest

from engram.anti_confabulation import (
    DIAGNOSIS_KEYWORDS,
    detect_unsupported_diagnosis_claim,
)


class TestDetectUnsupportedDiagnosisClaim:
    """L1.5: fact diagnostic keyword DEVE avere almeno una ref test."""

    @pytest.mark.parametrize("keyword", sorted(DIAGNOSIS_KEYWORDS))
    def test_keyword_without_test_ref_yields_warning(
        self, keyword: str,
    ) -> None:
        if keyword == "BUG #":
            prop = "Bug #99 search miss diagnosed via observation"
        elif keyword == "BUG IDENT":
            prop = "Bug identificato: hippo_remember gap"
        elif keyword == "ROOT CAUSE":
            prop = "Root cause is XYZ in module"
        elif keyword == "ROOTCAUSE":
            prop = "Rootcause: timing bug"
        else:
            prop = f"{keyword.lower()}: X is symptom"
        warn = detect_unsupported_diagnosis_claim(
            proposition=prop, verified_by=["observation:sintomo"],
        )
        assert warn is not None, (
            f"L1.5: keyword '{keyword}' without test-like ref must warn."
        )

    def test_no_keyword_no_warning(self) -> None:
        warn = detect_unsupported_diagnosis_claim(
            proposition="The user lives in Italy.",
            verified_by=[],
        )
        assert warn is None

    def test_keyword_with_pytest_ref_no_warning(self) -> None:
        warn = detect_unsupported_diagnosis_claim(
            proposition="Bug #99 diagnosed",
            verified_by=["pytest:test_x_falsifies_pre_fix:FAILED"],
        )
        assert warn is None

    def test_keyword_with_bash_ref_no_warning(self) -> None:
        warn = detect_unsupported_diagnosis_claim(
            proposition="Root cause is module Y",
            verified_by=["bash:python -c repro:exit1"],
        )
        assert warn is None

    def test_keyword_with_irrelevant_refs_warns(self) -> None:
        warn = detect_unsupported_diagnosis_claim(
            proposition="Bug #99 is X",
            verified_by=["agent:diag", "observation:sintomo"],
        )
        assert warn is not None


class TestEmpiricalReplay3DiagnosisConfabulations:
    """Replay of confabulations #5, #6, #7 from session 2026-05-17.
    All three were diagnosis claims based on SYMPTOM observation only,
    no falsifying test ref. L1.5 must catch them all."""

    def test_replay_confab5_search_miss_wrong_diagnosis(self) -> None:
        warn = detect_unsupported_diagnosis_claim(
            proposition=(
                "Bug #11 identificato: hippo_facts_search ha gap reale, "
                "non trova fact con query similar to proposition."
            ),
            verified_by=["observation:items_empty_for_long_query"],
        )
        assert warn is not None

    def test_replay_confab6_topic_loss_wrong_diagnosis(self) -> None:
        warn = detect_unsupported_diagnosis_claim(
            proposition=(
                "Bug #12 identificato: hippo_remember con kwarg topic "
                "esplicito salva topic come stringa vuota."
            ),
            verified_by=["observation:topic_empty_in_response"],
        )
        assert warn is not None

    def test_replay_confab7_topic_loss_intermittent(self) -> None:
        warn = detect_unsupported_diagnosis_claim(
            proposition=(
                "Bug identificato topic-loss intermittent: stessa "
                "sintassi salva topic in alcune call non in altre."
            ),
            verified_by=["observation:3_fact_topic_empty_vs_others_ok"],
        )
        assert warn is not None


class TestSemanticStoreWiresL15Warning:
    """SemanticMemory.store() must log L1.5 warning."""

    def test_store_logs_l15_warning_on_bug_without_test_ref(
        self, tmp_path, caplog,
    ) -> None:
        import logging

        from engram.semantic import Fact, SemanticMemory

        sm = SemanticMemory(db_path=tmp_path / "s.db")
        fact = Fact(
            id="diag-1",
            proposition="Bug #99 is search miss",
            topic="test/cycle130",
            verified_by=["observation:items_empty"],
            status="model_claim",
        )
        with caplog.at_level(logging.WARNING, logger="engram.semantic"):
            sm.store(fact)
        l15_messages = [
            r.getMessage() for r in caplog.records
            if "L1.5 anti-confabulation" in r.getMessage()
        ]
        assert l15_messages, (
            "Cycle #130: SemanticMemory.store() must log an L1.5 "
            "warning for diagnostic claims without test refs."
        )
