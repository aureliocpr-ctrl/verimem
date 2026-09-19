"""Cycle 175.1 (2026-05-22) — dream_stuck_hook contract tests.

Hook between ``verimem.active_learning.select_stuck_candidates`` and the
Auto-Dream pipeline. Pure seed builder: returns a dict that
``auto_dream_worker._propose_via_engram`` can splice into the
``instructions`` text passed to ``propose_dream_tasks``.

Scope cycle 175.1 — SOFT retry:
  The cluster algorithm in ``dream.py`` is free to ignore the hint. We
  only augment the human-readable instructions string. Hard retry
  (a dedicated ``priority_skill_ids`` param threaded through
  ``propose_dream_tasks``) is deferred to cycle 175.3 if H1 (4.3% →
  >10% promotion rate in 20 dream cycles) does NOT fire with the soft
  retry alone — see ``docs/cycle174_active_learning_design.md``.

RED marker: ``import verimem.dream_stuck_hook`` must fail on master.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

# RED MARKER
from verimem.dream_stuck_hook import build_stuck_retry_seed
from verimem.skill import Skill, SkillLibrary

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def skill_db_with_stuck(tmp_path: Path) -> Path:
    """Seed skills_index.db with 3 stuck-band candidates.

    Matches cycle 175 fact d778cce2faa8 semantics: trials ∈ [3, 10],
    smoothed fitness (s+1)/(t+2) ∈ (0.3, 0.5).
    """
    db_path = tmp_path / "skills_index.db"
    lib = SkillLibrary(
        dir_path=tmp_path / "skills_dir",
        db_path=db_path,
    )
    stuck_specs = [
        ("stuck one", 4, 1),  # fitness 2/6 = 0.333
        ("stuck two", 4, 1),  # fitness 2/6 = 0.333
        ("stuck three", 3, 1),  # fitness 2/5 = 0.400
    ]
    for name, trials, succ in stuck_specs:
        lib.store(Skill(
            name=name,
            trigger=f"trigger for {name}",
            body=f"body for {name}",
            status="candidate",
            trials=trials,
            successes=succ,
        ))
    return db_path


@pytest.fixture
def empty_skill_db(tmp_path: Path) -> Path:
    """Empty corpus → no stuck candidates."""
    db_path = tmp_path / "skills_index.db"
    SkillLibrary(
        dir_path=tmp_path / "skills_dir",
        db_path=db_path,
    )
    return db_path


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------


class TestBuildStuckRetrySeed:
    def test_returns_dict_with_required_keys(
        self, skill_db_with_stuck: Path,
    ) -> None:
        out = build_stuck_retry_seed(skill_db_with_stuck)
        assert isinstance(out, dict)
        assert "stuck_skill_ids" in out
        assert "instructions_suffix" in out

    def test_stuck_skill_ids_is_list_of_str(
        self, skill_db_with_stuck: Path,
    ) -> None:
        out = build_stuck_retry_seed(skill_db_with_stuck)
        assert isinstance(out["stuck_skill_ids"], list)
        assert all(isinstance(x, str) for x in out["stuck_skill_ids"])

    def test_empty_when_no_stuck_candidates(
        self, empty_skill_db: Path,
    ) -> None:
        """Empty corpus → empty stuck list + empty suffix.

        Caller can safely splice the empty suffix into instructions
        without producing dangling/misleading hints.
        """
        out = build_stuck_retry_seed(empty_skill_db)
        assert out["stuck_skill_ids"] == []
        assert out["instructions_suffix"] == ""

    def test_includes_three_stuck_when_seeded(
        self, skill_db_with_stuck: Path,
    ) -> None:
        out = build_stuck_retry_seed(skill_db_with_stuck, max_n=10)
        assert len(out["stuck_skill_ids"]) == 3, (
            f"expected 3 stuck, got {len(out['stuck_skill_ids'])}: "
            f"{out['stuck_skill_ids']}"
        )

    def test_instructions_suffix_mentions_active_learning_and_ids(
        self, skill_db_with_stuck: Path,
    ) -> None:
        """Human-readable suffix: must mention 'active learning' AND
        reference each stuck skill id for traceability in the dream
        artifact + audit log."""
        out = build_stuck_retry_seed(skill_db_with_stuck)
        suffix_lower = out["instructions_suffix"].lower()
        assert "active learning" in suffix_lower, (
            f"suffix missing 'active learning' marker: "
            f"{out['instructions_suffix']!r}"
        )
        for sid in out["stuck_skill_ids"]:
            assert sid in out["instructions_suffix"], (
                f"id {sid!r} not present in suffix "
                f"{out['instructions_suffix']!r}"
            )

    def test_handles_missing_db_defensive(self, tmp_path: Path) -> None:
        """Missing DB path → empty result, never raise.

        Auto-Dream worker hook is called on every cycle even when
        the user has not yet built a skill corpus.
        """
        out = build_stuck_retry_seed(tmp_path / "nope.db")
        assert out == {"stuck_skill_ids": [], "instructions_suffix": ""}

    def test_respects_max_n_cap(
        self, skill_db_with_stuck: Path,
    ) -> None:
        """max_n bounds the number of ids included in the seed."""
        out = build_stuck_retry_seed(skill_db_with_stuck, max_n=2)
        assert len(out["stuck_skill_ids"]) <= 2

    def test_delegates_to_select_stuck_candidates(
        self, skill_db_with_stuck: Path,
    ) -> None:
        """Composition contract: build_stuck_retry_seed must forward to
        verimem.active_learning.select_stuck_candidates with the same DB
        path + max_n kwarg. Falsifies any future implementation that
        re-implements the SELECT logic instead of composing."""
        with patch(
            "verimem.dream_stuck_hook.select_stuck_candidates",
            return_value=["id-alpha", "id-beta"],
        ) as mock_sel:
            out = build_stuck_retry_seed(
                skill_db_with_stuck, max_n=5,
            )
        mock_sel.assert_called_once_with(
            skill_db_with_stuck, max_n=5,
        )
        assert out["stuck_skill_ids"] == ["id-alpha", "id-beta"]
        # Suffix must still be built from the mocked ids
        assert "id-alpha" in out["instructions_suffix"]
        assert "id-beta" in out["instructions_suffix"]


# ---------------------------------------------------------------------------
# Integration: verimem.auto_dream_worker._propose_via_engram now calls the
# hook and splices the suffix into ``instructions`` passed to
# ``propose_dream_tasks``. These two tests pin the wiring; the unit tests
# above already cover seed semantics in isolation.
# ---------------------------------------------------------------------------


class TestProposeViaEngramHookWiring:
    def test_augments_instructions_when_stuck_present(
        self, tmp_path: Path,
    ) -> None:
        from verimem.auto_dream_worker import _propose_via_engram

        engram_dir = tmp_path / "engram"
        skills_dir = engram_dir / "skills"
        skill_db = skills_dir / "skills_index.db"
        lib = SkillLibrary(dir_path=skills_dir, db_path=skill_db)
        # 1 stuck candidate (fitness 2/6 = 0.333, in band 0.3-0.5,
        # trials 4 in band 3-10)
        lib.store(Skill(
            name="integration stuck candidate",
            trigger="t-int", body="b-int",
            status="candidate", trials=4, successes=1,
        ))

        with patch(
            "verimem.dream.propose_dream_tasks",
            return_value={"dream_id": "x", "pending_tasks": []},
        ) as mock_propose:
            _propose_via_engram(engram_dir=engram_dir)

        mock_propose.assert_called_once()
        instructions = mock_propose.call_args.kwargs["instructions"]
        assert "Auto-Dream cycle #69" in instructions
        assert "Active learning retry" in instructions, (
            f"hook suffix missing in instructions: {instructions!r}"
        )

    def test_no_augment_when_no_stuck(self, tmp_path: Path) -> None:
        """Empty corpus → instructions is the base text, byte-identical."""
        from verimem.auto_dream_worker import _propose_via_engram

        engram_dir = tmp_path / "engram"
        skills_dir = engram_dir / "skills"
        skill_db = skills_dir / "skills_index.db"
        SkillLibrary(dir_path=skills_dir, db_path=skill_db)

        with patch(
            "verimem.dream.propose_dream_tasks",
            return_value={"dream_id": "y", "pending_tasks": []},
        ) as mock_propose:
            _propose_via_engram(engram_dir=engram_dir)

        instructions = mock_propose.call_args.kwargs["instructions"]
        assert instructions == (
            "Auto-Dream cycle #69 — observe patterns since last trigger."
        )
        assert "Active learning" not in instructions
