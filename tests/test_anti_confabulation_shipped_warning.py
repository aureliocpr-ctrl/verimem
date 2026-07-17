"""Cycle #128 (2026-05-17) — L1 anti-confabulation warning on shipped claims.

Aurelio direttiva: "studiamo confabulazioni, come prevenirle in memoria".

Empirical motivation (sessione 2026-05-17):
* 7 confabulazioni mie ammesse, 2 dirette al pattern "X SHIPPED PR #N
  commit_hash" — salvate pre-merge come model_claim, nessuna validation.
* Fact reali implicati: 90326a635c96 (Cycle 119 WIRE production SHIPPED
  PR #61 c37fa87) + 201dd68bb40b (Cycle 120 SHIPPED PR #62).
* Cycle 111 v2 `provenance_validator` valida solo `status=verified`
  con I/O check. Model_claim con keyword forte passa silenziosamente.

L1 design (subagent #7 fact 8be6bdd34903): pre-write warning quando
proposition contiene keyword [SHIPPED|MERGED|WIRED|DEPLOYED] e
verified_by NON contiene refs commit-like (commit:|pr:|file:).

NO BREAKING: solo emit + counter. Fact viene salvato comunque (back-compat).

Test plan TDD:
1. RED: proposition "X SHIPPED PR #N" + verified_by=[] → today no warning.
2. GREEN: warning emitted with reason.
3. Negative: proposition senza keyword → no warning.
4. Negative: proposition con keyword + verified_by con commit ref → no warning.
5. Coverage: tutte e 4 keyword (SHIPPED|MERGED|WIRED|DEPLOYED).
"""
from __future__ import annotations

import pytest

from verimem.anti_confabulation import (
    SHIPPED_KEYWORDS,
    detect_unsupported_shipped_claim,
)


class TestDetectUnsupportedShippedClaim:
    """L1 warning: fact con keyword SHIPPED/MERGED/WIRED/DEPLOYED
    DEVE avere almeno una ref commit/pr/file in verified_by."""

    @pytest.mark.parametrize("keyword", sorted(SHIPPED_KEYWORDS))
    def test_keyword_without_refs_yields_warning(self, keyword: str) -> None:
        """Keyword + verified_by vuoto → warning."""
        prop = f"Cycle 999 feature X is {keyword} in main PR #99"
        warn = detect_unsupported_shipped_claim(
            proposition=prop, verified_by=[],
        )
        assert warn is not None, (
            f"Cycle #128 L1: keyword '{keyword}' in proposition with "
            f"empty verified_by must trigger anti-confabulation warning."
        )
        assert keyword in warn or keyword.lower() in warn.lower()

    def test_no_keyword_no_warning(self) -> None:
        """Proposition senza keyword forte → no warning."""
        warn = detect_unsupported_shipped_claim(
            proposition="The user lives in Italy.",
            verified_by=[],
        )
        assert warn is None

    def test_keyword_with_commit_ref_no_warning(self) -> None:
        """Keyword + verified_by con commit:abc123 → no warning."""
        warn = detect_unsupported_shipped_claim(
            proposition="Cycle 999 X is SHIPPED in main",
            verified_by=["commit:abc123def456", "file:engram/x.py:42"],
        )
        assert warn is None

    def test_keyword_with_pr_ref_no_warning(self) -> None:
        """Keyword + verified_by con pr:#99 → no warning."""
        warn = detect_unsupported_shipped_claim(
            proposition="Feature MERGED in main",
            verified_by=["pr:99:merged"],
        )
        assert warn is None

    def test_keyword_with_file_ref_no_warning(self) -> None:
        """Keyword + verified_by con file:path:N → no warning."""
        warn = detect_unsupported_shipped_claim(
            proposition="Cycle X DEPLOYED to production",
            verified_by=["file:engram/mcp_server.py:9301"],
        )
        assert warn is None

    def test_keyword_with_irrelevant_refs_warns(self) -> None:
        """Keyword + verified_by senza commit/pr/file refs → warning."""
        warn = detect_unsupported_shipped_claim(
            proposition="X is WIRED in production",
            verified_by=["url:somesite.com", "agent:abc123"],
        )
        assert warn is not None
        assert "WIRED" in warn or "wired" in warn

    def test_empirical_historical_fact_would_warn(self) -> None:
        """The two real confabulation facts from session 2026-05-17
        (90326a635c96 / 201dd68bb40b) would have triggered warning if
        L1 was in place. We replay one of them here for documentation."""
        # 90326a635c96 historical proposition:
        prop = (
            "Cycle 119 WIRE production SHIPPED 2026-05-17 PR #61 c37fa87. "
            "hippo_remember MCP ora passa default coherence_hook."
        )
        # The historical verified_by was tool-call refs without
        # commit:|pr:|file: markers.
        historical_vb = [
            "tool:hippo_remember:cycle_119_wire",
            "agent:cycle_119_decision",
        ]
        warn = detect_unsupported_shipped_claim(
            proposition=prop, verified_by=historical_vb,
        )
        assert warn is not None, (
            "Empirical: confabulazione storica 90326a635c96 deve "
            "essere catturata da L1 anti-confabulation warning."
        )


class TestSemanticStoreWiresL1Warning:
    """Cycle #128 wire: SemanticMemory.store() must log the L1
    warning via stdlib logging so it lands in observability."""

    def test_store_logs_warning_on_shipped_without_ref(
        self, tmp_path, caplog,
    ) -> None:
        import logging

        from verimem.semantic import Fact, SemanticMemory

        sm = SemanticMemory(db_path=tmp_path / "s.db")
        fact = Fact(
            id="conf-1",
            proposition="Cycle 999 feature X is SHIPPED in main PR #99",
            topic="test/cycle128",
            verified_by=["tool:agent:no_commit_ref"],
            status="model_claim",
        )
        with caplog.at_level(logging.WARNING, logger="verimem.semantic"):
            sm.store(fact)
        anti_confab_messages = [
            r.getMessage() for r in caplog.records
            if "L1 anti-confabulation" in r.getMessage()
        ]
        assert anti_confab_messages, (
            "Cycle #128 wire: SemanticMemory.store() must log an "
            "L1 anti-confabulation warning for shipped-like claims "
            "without commit refs."
        )

    def test_store_silent_on_normal_fact(
        self, tmp_path, caplog,
    ) -> None:
        import logging

        from verimem.semantic import Fact, SemanticMemory

        sm = SemanticMemory(db_path=tmp_path / "s.db")
        fact = Fact(
            id="ok-1",
            proposition="The user lives in Italy.",
            topic="user_facts",
            status="model_claim",
        )
        with caplog.at_level(logging.WARNING, logger="verimem.semantic"):
            sm.store(fact)
        for r in caplog.records:
            assert "L1 anti-confabulation" not in r.getMessage(), (
                "No warning expected for normal facts."
            )
