"""Cycle 204 (2026-05-23) — cross-encoder rerank tests.

NO sentence-transformers / CrossEncoder model load required — all
tests use a mock ``scorer`` callable that returns deterministic
scores.

RED marker: ``from engram.cross_encoder_rerank import
rerank_candidates`` must fail on master.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

# RED MARKER
from engram.cross_encoder_rerank import rerank_candidates

_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    proposition TEXT,
    topic TEXT,
    created_at REAL
);
"""


@pytest.fixture
def seeded_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "semantic.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    rows = [
        ("f1", "Python is a programming language", "lang", 1.0),
        ("f2", "Java is a programming language", "lang", 2.0),
        ("f3", "Banana is a fruit", "food", 3.0),
        ("f4", "Cat is an animal", "animal", 4.0),
    ]
    conn.executemany(
        "INSERT INTO facts (id, proposition, topic, created_at) "
        "VALUES (?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    return db_path


def _make_known_scorer(score_map: dict[str, float]):
    """Build a deterministic scorer keyed by proposition substring."""

    def scorer(pairs: list[tuple[str, str]]) -> list[float]:
        out = []
        for _q, doc in pairs:
            sc = 0.0
            for needle, val in score_map.items():
                if needle in doc:
                    sc = max(sc, val)
            out.append(sc)
        return out

    return scorer


class TestRerankCandidates:
    def test_empty_candidates_returns_empty(self, seeded_db: Path) -> None:
        out = rerank_candidates(
            "any query", [],
            semantic_db=seeded_db, scorer=lambda pairs: [],
        )
        assert out == []

    def test_missing_db_returns_empty(self, tmp_path: Path) -> None:
        out = rerank_candidates(
            "q", ["f1"],
            semantic_db=tmp_path / "nope.db", scorer=lambda pairs: [1.0],
        )
        assert out == []

    def test_reranks_by_scorer_output(self, seeded_db: Path) -> None:
        """f3 (banana) should outrank f1 (python) under a banana-loving
        scorer."""
        scorer = _make_known_scorer({
            "Banana": 10.0,
            "Python": 5.0,
            "Java": 4.0,
        })
        out = rerank_candidates(
            "what is a fruit?", ["f1", "f2", "f3", "f4"],
            semantic_db=seeded_db, scorer=scorer, top_n=4,
        )
        assert out[0][0] == "f3"

    def test_top_n_caps(self, seeded_db: Path) -> None:
        scorer = _make_known_scorer({"Python": 1.0, "Java": 2.0,
                                      "Banana": 3.0, "Cat": 4.0})
        out = rerank_candidates(
            "q", ["f1", "f2", "f3", "f4"],
            semantic_db=seeded_db, scorer=scorer, top_n=2,
        )
        assert len(out) == 2

    def test_scorer_raises_falls_back_to_input_order(
        self, seeded_db: Path,
    ) -> None:
        """If the model raises, return input order with score 0.0."""

        def bad_scorer(pairs: list[tuple[str, str]]) -> list[float]:
            raise RuntimeError("model OOM")

        out = rerank_candidates(
            "q", ["f1", "f2", "f3"],
            semantic_db=seeded_db, scorer=bad_scorer, top_n=10,
        )
        assert len(out) == 3
        assert all(score == 0.0 for _, score in out)

    def test_missing_fact_ids_skipped(self, seeded_db: Path) -> None:
        """Stale id in candidate list → silently dropped, no crash."""
        scorer = _make_known_scorer({"Python": 1.0, "Banana": 2.0})
        out = rerank_candidates(
            "q", ["f1", "ghost-id", "f3"],
            semantic_db=seeded_db, scorer=scorer, top_n=10,
        )
        ids = {fid for fid, _ in out}
        assert "ghost-id" not in ids
        assert "f1" in ids
        assert "f3" in ids

    def test_scorer_wrong_length_zeros_out(self, seeded_db: Path) -> None:
        """If scorer returns the wrong number of values, fall back."""

        def bad_len_scorer(pairs):
            return [1.0]  # only 1 score for 3 pairs

        out = rerank_candidates(
            "q", ["f1", "f2", "f3"],
            semantic_db=seeded_db, scorer=bad_len_scorer, top_n=10,
        )
        assert all(s == 0.0 for _, s in out)

    def test_pairs_carry_query_and_proposition(
        self, seeded_db: Path,
    ) -> None:
        """Verify the scorer sees the query + proposition correctly."""
        captured = []

        def capturing_scorer(pairs):
            captured.extend(pairs)
            return [1.0] * len(pairs)

        rerank_candidates(
            "my query string", ["f1"],
            semantic_db=seeded_db, scorer=capturing_scorer, top_n=1,
        )
        assert len(captured) == 1
        q, doc = captured[0]
        assert q == "my query string"
        assert "Python" in doc

    def test_returns_sorted_desc(self, seeded_db: Path) -> None:
        scorer = _make_known_scorer({"Python": 10.0, "Java": 5.0,
                                      "Banana": 1.0, "Cat": 7.0})
        out = rerank_candidates(
            "q", ["f1", "f2", "f3", "f4"],
            semantic_db=seeded_db, scorer=scorer, top_n=4,
        )
        scores = [s for _, s in out]
        assert scores == sorted(scores, reverse=True)
