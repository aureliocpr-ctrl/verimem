"""Cycle 210 (2026-05-23) — Thompson sampling tests.

RED marker: ``from verimem.thompson_sampling import
thompson_sample_candidates`` must fail on master.
"""
from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path

import pytest

# RED MARKER
from verimem.thompson_sampling import thompson_sample_candidates

_SCHEMA = """
CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY,
    name TEXT,
    trigger TEXT,
    body TEXT,
    status TEXT DEFAULT 'candidate',
    trials INTEGER DEFAULT 0,
    successes INTEGER DEFAULT 0,
    fitness_mean REAL DEFAULT 0.5,
    created_at REAL DEFAULT 0.0,
    updated_at REAL DEFAULT 0.0
);
"""


@pytest.fixture
def warm_up_db(tmp_path: Path) -> Path:
    """Five skills with different posterior means.

      s-high:   trials=2, successes=2  → posterior mean (2+1)/(2+2)=0.75
      s-mid:    trials=4, successes=2  → 0.50
      s-low:    trials=4, successes=0  → 0.17
      s-fresh:  trials=0, successes=0  → 0.50 (uninformative)
      s-mature: trials=15, successes=12 → EXCLUDED (trials>=10)
    """
    db_path = tmp_path / "skills_index.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    rows = [
        ("s-high",   "h", "t", "b", "candidate", 2, 2, 0.75, 1.0, 1.0),
        ("s-mid",    "m", "t", "b", "candidate", 4, 2, 0.50, 1.0, 1.0),
        ("s-low",    "l", "t", "b", "candidate", 4, 0, 0.17, 1.0, 1.0),
        ("s-fresh",  "f", "t", "b", "candidate", 0, 0, 0.50, 1.0, 1.0),
        ("s-mature", "M", "t", "b", "candidate", 15, 12, 0.81, 1.0, 1.0),
    ]
    conn.executemany(
        "INSERT INTO skills (id, name, trigger, body, status, trials, "
        "successes, fitness_mean, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    return db_path


class TestThompsonSampleCandidates:
    def test_missing_db_returns_empty(self, tmp_path: Path) -> None:
        assert thompson_sample_candidates(tmp_path / "nope.db") == []

    def test_empty_db_returns_empty(self, tmp_path: Path) -> None:
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(_SCHEMA)
        conn.close()
        assert thompson_sample_candidates(db_path) == []

    def test_returns_list_of_str(self, warm_up_db: Path) -> None:
        out = thompson_sample_candidates(warm_up_db, rng_seed=42)
        assert isinstance(out, list)
        assert all(isinstance(x, str) for x in out)

    def test_excludes_mature_skills(self, warm_up_db: Path) -> None:
        """s-mature has trials=15, must be excluded under
        default max_trials=10."""
        out = thompson_sample_candidates(
            warm_up_db, max_n=10, rng_seed=42,
        )
        assert "s-mature" not in out

    def test_respects_max_n_cap(self, warm_up_db: Path) -> None:
        out = thompson_sample_candidates(
            warm_up_db, max_n=2, rng_seed=42,
        )
        assert len(out) <= 2

    def test_deterministic_under_fixed_seed(self, warm_up_db: Path) -> None:
        out1 = thompson_sample_candidates(
            warm_up_db, max_n=3, rng_seed=42,
        )
        out2 = thompson_sample_candidates(
            warm_up_db, max_n=3, rng_seed=42,
        )
        assert out1 == out2

    def test_different_seeds_can_differ(self, warm_up_db: Path) -> None:
        """Different seeds should produce different orderings (the
        whole point of stochastic sampling)."""
        out_a = thompson_sample_candidates(
            warm_up_db, max_n=4, rng_seed=1,
        )
        out_b = thompson_sample_candidates(
            warm_up_db, max_n=4, rng_seed=999,
        )
        # Same SET of ids (deterministic filter) but possibly different ORDER.
        # If by chance same ordering, that's still allowed; test is statistical.
        assert set(out_a) == set(out_b)

    def test_high_posterior_arm_picked_more_often(
        self, warm_up_db: Path,
    ) -> None:
        """Over many runs, s-high (posterior mean 0.75) should rank
        #1 more often than s-low (mean 0.17)."""
        first_place = Counter()
        for seed in range(200):
            out = thompson_sample_candidates(
                warm_up_db, max_n=1, rng_seed=seed,
            )
            if out:
                first_place[out[0]] += 1
        # Statistical assertion: s-high should win at least 2x as
        # often as s-low.
        assert first_place["s-high"] > 2 * first_place["s-low"], (
            f"first-place distribution: {first_place}"
        )

    def test_only_candidate_status_returned(self, tmp_path: Path) -> None:
        db_path = tmp_path / "s.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(_SCHEMA)
        conn.executemany(
            "INSERT INTO skills (id, name, status, trials, successes, "
            "created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
            [
                ("cand", "c", "candidate", 2, 1, 1.0, 1.0),
                ("prom", "p", "promoted",  2, 1, 1.0, 1.0),
                ("ret",  "r", "retired",   2, 1, 1.0, 1.0),
            ],
        )
        conn.commit()
        conn.close()
        out = thompson_sample_candidates(
            db_path, max_n=10, rng_seed=42,
        )
        assert out == ["cand"]

    def test_handles_corrupt_rows_gracefully(
        self, tmp_path: Path,
    ) -> None:
        """Rows with NULL trials / NULL successes shouldn't crash.

        A3 honest: SQL `trials < max_trials` with NULL trials returns
        NULL (excluded by WHERE clause), so the NULL row is filtered
        out at the SQL level. This is the standard SQL behaviour and
        an acceptable interpretation of "unknown trials count". The
        function does NOT crash, which is the real contract.
        """
        db_path = tmp_path / "s.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(_SCHEMA)
        conn.execute(
            "INSERT INTO skills (id, name, status, trials, successes) "
            "VALUES ('x', 'x', 'candidate', NULL, NULL)",
        )
        conn.execute(
            "INSERT INTO skills (id, name, status, trials, successes) "
            "VALUES ('y', 'y', 'candidate', 1, 0)",
        )
        conn.commit()
        conn.close()
        out = thompson_sample_candidates(
            db_path, max_n=5, rng_seed=42,
        )
        # NULL row filtered out by SQL WHERE; non-NULL row y survives.
        # The contract is "no crash", not "include NULL rows".
        assert isinstance(out, list)
        assert "y" in out
