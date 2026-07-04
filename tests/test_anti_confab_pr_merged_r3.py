"""Audit 3-round R1 #6 (anti-confab): a SHIPPED/MERGED/DEPLOYED claim must NOT be
anchored by a bare or open ``pr:`` ref — only by a *merged* one.

detect_unsupported_shipped_claim accepted any ``pr:`` (its _has_commit_ref regex
was ``^(commit:|pr:|file:|git:)``), so "Feature X SHIPPED PR #99" with
``verified_by=["pr:99"]`` passed silently — exactly the 2026-05-17 confab pattern
(claim saved before the PR merged). commit:/file:/git: are landed by nature and
stay accepted; a pr: now anchors only when it says merged.
"""
from __future__ import annotations

from engram.anti_confabulation import detect_unsupported_shipped_claim


def test_shipped_with_bare_pr_warns() -> None:
    warn = detect_unsupported_shipped_claim(
        proposition="Feature X SHIPPED in main PR #99",
        verified_by=["pr:99"],
    )
    assert warn is not None, "un pr: bare (non-merged) non deve ancorare un SHIPPED"


def test_shipped_with_open_pr_warns() -> None:
    warn = detect_unsupported_shipped_claim(
        proposition="Feature X DEPLOYED to production",
        verified_by=["pr:#99:state=open"],
    )
    assert warn is not None, "un pr: open non deve ancorare un DEPLOYED"


def test_shipped_with_merged_pr_accepted() -> None:
    """Guard: a merged pr: is a genuine landed anchor (no over-tightening)."""
    for vb in (["pr:99:merged"], ["pr:#80:merged"], ["pr:1234_merged"]):
        assert detect_unsupported_shipped_claim(
            proposition="Feature MERGED in main", verified_by=vb,
        ) is None, f"un pr merged deve restare accettato: {vb}"


def test_shipped_with_commit_or_file_accepted() -> None:
    """Guard: commit/file/git refs are landed by nature, still accepted."""
    for vb in (["commit:abc123def"], ["file:engram/x.py:42"], ["git:abc123"]):
        assert detect_unsupported_shipped_claim(
            proposition="X SHIPPED in main", verified_by=vb,
        ) is None, f"ref landed deve restare accettato: {vb}"


def test_shipped_with_negated_or_future_pr_warns() -> None:
    """A pr: that merely CONTAINS 'merged' as a substring but is negated or
    in the future is NOT landed and must still warn — the regex hole the
    sincerity re-review exposed: unmerged / not_merged / to_be_merged."""
    for vb in (
        ["pr:99:unmerged"], ["pr:99:not_merged"], ["pr:7:to_be_merged"],
        ["pr:42:awaiting_merge"], ["pr:5:will_be_merged"],
    ):
        assert detect_unsupported_shipped_claim(
            proposition="Feature X SHIPPED in main", verified_by=vb,
        ) is not None, f"un pr: non-merged (negato/futuro) deve warnare: {vb}"


def test_shipped_with_uncertainty_qualifier_pr_warns() -> None:
    """Fail-safe redesign: a 'merged' token shadowed by an UNKNOWN/uncertainty
    qualifier (almost/partially/mostly/branch-name) is not provably landed and
    must warn — the deny-list-isn't-exhaustive hole the critic flagged."""
    for vb in (
        ["pr:99:almost_merged"], ["pr:99:partially_merged"],
        ["pr:99:mostly_merged"], ["pr:99:merged_to_somebranch"],
    ):
        assert detect_unsupported_shipped_claim(
            proposition="Feature X SHIPPED", verified_by=vb,
        ) is not None, f"qualifier ignoto vicino a merged deve warnare: {vb}"


def test_shipped_with_known_landed_qualifier_accepted() -> None:
    """Guard: genuine merge-mode qualifiers (auto/squash/rebase merged) pass."""
    for vb in (["pr:99:auto_merged"], ["pr:80:squash_merged"],
               ["pr:7:rebase_merged"]):
        assert detect_unsupported_shipped_claim(
            proposition="Feature MERGED", verified_by=vb,
        ) is None, f"qualifier di merge noto deve essere accettato: {vb}"
