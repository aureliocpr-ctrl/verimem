"""Cycle 191 (2026-05-23) — RRF primitive tests.

Reference: Cormack-Clarke-Buettcher 2009 §2 RRF formula:
  score(d) = Σ_signal  1 / (k + rank_signal(d))

RED marker: ``from verimem.multi_signal_fusion import rrf_fuse`` must
fail on master.
"""
from __future__ import annotations

# RED MARKER
from verimem.multi_signal_fusion import DEFAULT_K, rrf_fuse


class TestRrfFuse:
    def test_empty_input_returns_empty(self) -> None:
        assert rrf_fuse([]) == []
        assert rrf_fuse([[], []]) == []

    def test_single_list_preserves_order(self) -> None:
        """One signal → output rank matches input rank (ties impossible)."""
        out = rrf_fuse([["a", "b", "c", "d"]])
        ids = [fid for fid, _ in out]
        assert ids == ["a", "b", "c", "d"]

    def test_identical_lists_double_score(self) -> None:
        """Same id ranked first in two lists → score doubles relative
        to one-list-only id."""
        out = rrf_fuse([["a", "b"], ["a", "c"]])
        score_by_id = dict(out)
        # a appears at rank 1 in both lists; b only in first; c only second.
        expected_a = 2 * (1.0 / (DEFAULT_K + 1))
        expected_b = 1.0 / (DEFAULT_K + 2)
        expected_c = 1.0 / (DEFAULT_K + 2)
        assert abs(score_by_id["a"] - expected_a) < 1e-12
        assert abs(score_by_id["b"] - expected_b) < 1e-12
        assert abs(score_by_id["c"] - expected_c) < 1e-12

    def test_returns_sorted_desc(self) -> None:
        """Output must be sorted by score DESC."""
        out = rrf_fuse([["x", "y"], ["y", "z"], ["z", "w"]])
        scores = [s for _, s in out]
        assert scores == sorted(scores, reverse=True)

    def test_deterministic_under_ties(self) -> None:
        """Ties broken by rank in the FIRST list (the primary signal), then
        alphabetically (WF3 2026-06-20). 'c' is the sole member of list 0 so it
        wins the score tie; 'a'/'b' (absent from list 0) fall back to alpha."""
        out = rrf_fuse([["c"], ["a"], ["b"]])
        ids = [fid for fid, _ in out]
        assert ids == ["c", "a", "b"]  # first-list priority, then alpha

    def test_first_list_wins_score_tie(self) -> None:
        """WF3: a fact ranked by the PRIMARY signal (dense/CE = list 0) must NOT be
        displaced at a score tie by a random fact_id from a secondary signal. Both
        are rank-1 (equal RRF score); the list-0 fact must rank first regardless of
        how its id sorts alphabetically."""
        # 'zzz' is dense-rank-1; 'aaa' is bm25-rank-1 — equal score, alpha would
        # have put 'aaa' first and buried the CE-top result.
        out = rrf_fuse([["zzz"], ["aaa"]])
        assert [fid for fid, _ in out][0] == "zzz"

    def test_alpha_is_final_fallback_off_first_list(self) -> None:
        """Two facts both ABSENT from the first list and equal score → deterministic
        alphabetical fallback (the first-list key is identical for both)."""
        out = rrf_fuse([["x"], ["b"], ["a"]])
        ids = [fid for fid, _ in out]
        assert ids == ["x", "a", "b"]  # x leads (list 0); a<b alpha

    def test_disjoint_lists_all_ids_appear(self) -> None:
        """No overlap across lists → every id surfaces in fused output."""
        out = rrf_fuse([["a", "b"], ["c", "d"], ["e", "f"]])
        ids = {fid for fid, _ in out}
        assert ids == {"a", "b", "c", "d", "e", "f"}

    def test_custom_k_changes_scores(self) -> None:
        """k=1 makes top ranks dominate much more strongly than k=60."""
        out_k1 = dict(rrf_fuse([["a", "b"]], k=1.0))
        out_k60 = dict(rrf_fuse([["a", "b"]], k=60.0))
        # Top-rank id 'a' gets 1/(1+1)=0.5 with k=1, 1/(60+1)≈0.0164 with k=60
        assert out_k1["a"] > out_k60["a"]

    def test_non_positive_k_falls_back_to_default(self) -> None:
        """Defensive: k=0 or k=-1 → coerce to DEFAULT_K, no crash."""
        out_zero = dict(rrf_fuse([["a"]], k=0))
        out_neg = dict(rrf_fuse([["a"]], k=-5))
        out_default = dict(rrf_fuse([["a"]], k=DEFAULT_K))
        assert out_zero == out_default
        assert out_neg == out_default

    def test_skips_non_string_entries(self) -> None:
        """Malformed entries (None / int) MUST be skipped, not raise."""
        out = rrf_fuse([["a", None, 42, "b"]])  # type: ignore[list-item]
        ids = [fid for fid, _ in out]
        assert ids == ["a", "b"]

    def test_rank_position_dominates_within_one_list(self) -> None:
        """Within a single list, rank 1 > rank 2 > rank N."""
        out = rrf_fuse([["a", "b", "c"]])
        score_by_id = dict(out)
        assert score_by_id["a"] > score_by_id["b"] > score_by_id["c"]

    def test_cormack_2009_table1_style_basic(self) -> None:
        """Sanity: matches the spirit of Cormack et al. 2009 RRF
        formula. Two systems: S1 ranks A first, S2 ranks A second.
        With k=60 the fused score is 1/61 + 1/62."""
        out = rrf_fuse([["A", "X"], ["Y", "A"]])
        score_by_id = dict(out)
        expected_A = (1.0 / 61.0) + (1.0 / 62.0)
        assert abs(score_by_id["A"] - expected_A) < 1e-12
