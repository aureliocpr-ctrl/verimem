"""Cycle 214 (2026-05-23) — topic normalisation tests.

RED marker: ``from verimem.topic_normalization import normalize_topic``
must fail on master.
"""
from __future__ import annotations

# RED MARKER
from verimem.topic_normalization import (
    group_by_topic_family,
    normalize_topic,
    topic_similarity,
)


class TestNormalizeTopic:
    def test_none_returns_empty(self) -> None:
        assert normalize_topic(None) == ""

    def test_empty_returns_empty(self) -> None:
        assert normalize_topic("") == ""
        assert normalize_topic("   ") == ""

    def test_lowercase_and_strip(self) -> None:
        assert normalize_topic("  HippoAgent  ") == "hippoagent"

    def test_drops_scope_prefix(self) -> None:
        """'project/hippoagent/cycle175' should drop 'project' scope."""
        out = normalize_topic("project/hippoagent/cycle175")
        assert out == "hippoagent/cycle"

    def test_strips_trailing_date(self) -> None:
        out = normalize_topic("hippoagent/cycle175-2026-05-23")
        assert "2026" not in out
        assert "hippoagent" in out

    def test_normalises_separator_variants(self) -> None:
        a = normalize_topic("project::hippoagent::cycle175")
        b = normalize_topic("project/hippoagent/cycle175")
        c = normalize_topic("project_hippoagent_cycle175")
        assert a == b == c

    def test_strips_trailing_cycle_id(self) -> None:
        """'cycle175' → 'cycle'."""
        out = normalize_topic("hippoagent/cycle175")
        assert "175" not in out

    def test_strips_trailing_decimal_cycle_id(self) -> None:
        out = normalize_topic("hippoagent/cycle175.1")
        assert "175" not in out
        assert "hippoagent" in out

    def test_drops_pure_numeric_segments(self) -> None:
        """'cycle/175' → 'cycle'."""
        out = normalize_topic("cycle/175")
        assert "175" not in out

    def test_keeps_meaningful_segment(self) -> None:
        out = normalize_topic("project/hippoagent/auto-dream")
        assert "auto-dream" in out or "hippoagent" in out


class TestTopicSimilarity:
    def test_identical_returns_one(self) -> None:
        assert topic_similarity("hippoagent/cycle", "hippoagent/cycle") == 1.0

    def test_disjoint_returns_zero(self) -> None:
        assert topic_similarity("foo", "bar") == 0.0

    def test_partial_overlap(self) -> None:
        # 'a/b' vs 'a/c' → intersection={a}, union={a,b,c} → 1/3
        sim = topic_similarity("a/b", "a/c")
        assert abs(sim - 1 / 3) < 1e-9

    def test_normalised_variants_collapse(self) -> None:
        """'project/hippoagent/cycle175' and 'cycle/175.1' should have
        non-trivial similarity after normalisation."""
        sim = topic_similarity(
            "project/hippoagent/cycle175",
            "project/hippoagent/cycle175.1",
        )
        assert sim > 0.5

    def test_both_empty_returns_one(self) -> None:
        assert topic_similarity(None, "") == 1.0
        assert topic_similarity("", "") == 1.0

    def test_one_empty_returns_zero(self) -> None:
        assert topic_similarity("foo", "") == 0.0
        assert topic_similarity(None, "foo") == 0.0


class TestGroupByTopicFamily:
    def test_empty_input(self) -> None:
        assert group_by_topic_family([]) == {}

    def test_groups_similar_topics(self) -> None:
        raws = [
            "project/hippoagent/cycle175",
            "project/hippoagent/cycle175.1",
            "project/hippoagent/cycle176",
            "project/clp/loop169",
        ]
        out = group_by_topic_family(raws, threshold=0.4)
        # Expect at least 2 families (hippoagent group vs clp group).
        assert len(out) >= 2
        all_members = [m for ms in out.values() for m in ms]
        assert set(all_members) == set(raws)

    def test_isolated_topic_gets_own_family(self) -> None:
        out = group_by_topic_family(
            ["alpha", "beta-completely-different"], threshold=0.9,
        )
        assert len(out) == 2

    def test_skips_empty_topics(self) -> None:
        out = group_by_topic_family(["", None, "foo"])  # type: ignore[list-item]
        all_members = [m for ms in out.values() for m in ms]
        assert "foo" in all_members
        # Should not have created a family for "" or None
        assert len(out) == 1
