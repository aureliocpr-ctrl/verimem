"""Cycle 211 (2026-05-23) — dream_thompson_hook tests.

Same composable pattern as cycle 175.1 dream_stuck_hook + cycle 187
dream_community_hook. RED marker: ``from
verimem.dream_thompson_hook import build_thompson_seed`` must fail.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

# RED MARKER
from verimem.dream_thompson_hook import build_thompson_seed

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
def skill_db_warmup(tmp_path: Path) -> Path:
    db_path = tmp_path / "skills_index.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    conn.executemany(
        "INSERT INTO skills (id, name, trigger, body, status, trials, "
        "successes, fitness_mean, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            ("s1", "high", "t", "b", "candidate", 2, 2, 0.75, 1.0, 1.0),
            ("s2", "mid",  "t", "b", "candidate", 4, 2, 0.50, 1.0, 1.0),
            ("s3", "low",  "t", "b", "candidate", 4, 0, 0.17, 1.0, 1.0),
        ],
    )
    conn.commit()
    conn.close()
    return db_path


class TestBuildThompsonSeed:
    def test_missing_db_returns_empty_seed(self, tmp_path: Path) -> None:
        out = build_thompson_seed(tmp_path / "nope.db")
        assert out == {"thompson_skill_ids": [], "instructions_suffix": ""}

    def test_returns_dict_with_required_keys(
        self, skill_db_warmup: Path,
    ) -> None:
        out = build_thompson_seed(skill_db_warmup, rng_seed=42)
        assert "thompson_skill_ids" in out
        assert "instructions_suffix" in out

    def test_skill_ids_is_list_of_str(self, skill_db_warmup: Path) -> None:
        out = build_thompson_seed(skill_db_warmup, rng_seed=42)
        assert isinstance(out["thompson_skill_ids"], list)
        assert all(isinstance(x, str) for x in out["thompson_skill_ids"])

    def test_respects_max_n(self, skill_db_warmup: Path) -> None:
        out = build_thompson_seed(
            skill_db_warmup, max_n=1, rng_seed=42,
        )
        assert len(out["thompson_skill_ids"]) <= 1

    def test_instructions_suffix_mentions_thompson(
        self, skill_db_warmup: Path,
    ) -> None:
        out = build_thompson_seed(skill_db_warmup, rng_seed=42)
        suffix_lower = out["instructions_suffix"].lower()
        assert "thompson" in suffix_lower or "posterior" in suffix_lower

    def test_delegates_to_thompson_sample_candidates(
        self, skill_db_warmup: Path,
    ) -> None:
        """Composition contract: forwards to cycle 210 primitive."""
        with patch(
            "verimem.dream_thompson_hook.thompson_sample_candidates",
            return_value=["mocked-id-1", "mocked-id-2"],
        ) as mock_sampler:
            out = build_thompson_seed(
                skill_db_warmup, max_n=5, rng_seed=42,
            )
        mock_sampler.assert_called_once()
        assert out["thompson_skill_ids"] == ["mocked-id-1", "mocked-id-2"]
        # IDs must appear in suffix for traceability.
        assert "mocked-id-1" in out["instructions_suffix"]

    def test_empty_when_no_candidates(self, tmp_path: Path) -> None:
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(_SCHEMA)
        conn.close()
        out = build_thompson_seed(db_path, rng_seed=42)
        assert out["thompson_skill_ids"] == []
        assert out["instructions_suffix"] == ""

    def test_handles_sampler_exception_gracefully(
        self, skill_db_warmup: Path,
    ) -> None:
        """thompson_sample_candidates raise → empty seed, no crash."""
        with patch(
            "verimem.dream_thompson_hook.thompson_sample_candidates",
            side_effect=RuntimeError("sampler down"),
        ):
            out = build_thompson_seed(skill_db_warmup, rng_seed=42)
        assert out == {"thompson_skill_ids": [], "instructions_suffix": ""}
