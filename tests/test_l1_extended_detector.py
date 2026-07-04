"""Cycle 183 (2026-05-23) — L1 extended detector: FIX keyword family.

Closes gap §5 #3 of docs/sota/L0-L3-anti-confab-layers.md (cycle 180).
The cycle-128 detector covers SHIPPED/MERGED/WIRED/DEPLOYED — bug-fix
claims (e.g. ``"FIXED the race condition"``) without an evidence ref
slip through. This cycle adds a parallel detector family for the
``FIXED/RESOLVED/PATCHED/REPAIRED`` verbs.

Design choice: composable side-by-side module (no touch to
``anti_confab_gate.py``). The new detector returns the same Warning
shape as the cycle-128 family so a future gate-orchestrator cycle
can simply add it to the chain.

RED marker: import must fail on master.
"""
from __future__ import annotations

import pytest

# RED MARKER
from engram.l1_extended_detector import (
    FIX_KEYWORDS,
    FixClaimWarning,
    detect_unsupported_fix_claim,
)


class TestDetectUnsupportedFixClaim:
    def test_returns_none_when_no_keyword(self) -> None:
        """Plain text without FIX keywords → None."""
        out = detect_unsupported_fix_claim(
            proposition="A generic statement about something.",
            verified_by=[],
        )
        assert out is None

    def test_returns_warning_when_fixed_no_evidence(self) -> None:
        """FIXED + no evidence ref → Warning instance."""
        out = detect_unsupported_fix_claim(
            proposition="FIXED the race condition in semantic.py",
            verified_by=["bash:some_call"],
        )
        assert out is not None
        assert isinstance(out, FixClaimWarning)

    def test_returns_warning_when_resolved_no_evidence(self) -> None:
        out = detect_unsupported_fix_claim(
            proposition="RESOLVED the database lock issue",
            verified_by=[],
        )
        assert out is not None

    def test_returns_warning_when_patched_no_evidence(self) -> None:
        out = detect_unsupported_fix_claim(
            proposition="PATCHED the auth flow last night",
            verified_by=[],
        )
        assert out is not None

    def test_returns_warning_when_repaired_no_evidence(self) -> None:
        out = detect_unsupported_fix_claim(
            proposition="REPAIRED the corrupted index table",
            verified_by=[],
        )
        assert out is not None

    def test_case_insensitive_keyword_match(self) -> None:
        """``Fixed`` mixed-case must still trigger (consistent with
        cycle-128 ``SHIPPED`` family that uses ``.upper()``)."""
        out = detect_unsupported_fix_claim(
            proposition="I just fixed the bug",
            verified_by=[],
        )
        assert out is not None

    def test_returns_none_when_commit_ref_present(self) -> None:
        """FIXED + commit: ref → trusted, no warning."""
        out = detect_unsupported_fix_claim(
            proposition="FIXED the race condition",
            verified_by=["commit:abc123def", "file:engram/sem.py:710"],
        )
        assert out is None

    def test_returns_none_when_pytest_ref_present(self) -> None:
        """FIXED + pytest:test_x_PASS → trusted (bug-fix evidence)."""
        out = detect_unsupported_fix_claim(
            proposition="FIXED the regex in validate_claim",
            verified_by=["pytest:test_validate_claim_PASS"],
        )
        assert out is None

    def test_returns_none_when_bash_log_ref_present(self) -> None:
        """FIXED + bash:<cmd>:exit0 (clear evidence) → trusted."""
        out = detect_unsupported_fix_claim(
            proposition="FIXED the leak in connection pool",
            verified_by=["bash:pytest_pass:exit0:17280"],
        )
        # bash:<x>:exit0 is recognised as evidence (exit-code marker)
        assert out is None

    def test_warning_carries_keyword_and_advice(self) -> None:
        """Warning struct must include which keyword triggered + a
        human-readable advice string."""
        out = detect_unsupported_fix_claim(
            proposition="RESOLVED everything yesterday",
            verified_by=[],
        )
        assert out is not None
        assert out.keyword.upper() in FIX_KEYWORDS
        assert "evidence" in out.advice.lower() or "ref" in out.advice.lower()

    def test_keyword_set_has_four_canonical(self) -> None:
        """FIX_KEYWORDS must contain at least the 4 canonical verbs."""
        for kw in ("FIXED", "RESOLVED", "PATCHED", "REPAIRED"):
            assert kw in FIX_KEYWORDS, (
                f"missing canonical keyword {kw!r} in {FIX_KEYWORDS}"
            )

    def test_handles_none_verified_by_gracefully(self) -> None:
        """verified_by=None (not just empty list) must not crash."""
        out = detect_unsupported_fix_claim(
            proposition="FIXED something",
            verified_by=None,
        )
        # None verified_by is treated as no evidence → still a warning.
        assert out is not None


@pytest.mark.parametrize("keyword", ["FIXED", "RESOLVED", "PATCHED", "REPAIRED"])
def test_each_canonical_keyword_triggers(keyword: str) -> None:
    """Parametric coverage of every canonical keyword in the set."""
    prop = f"{keyword} the production hotfix without testing"
    out = detect_unsupported_fix_claim(
        proposition=prop, verified_by=["bash:some_unrelated_call"],
    )
    assert out is not None, f"keyword {keyword!r} did not trigger"
