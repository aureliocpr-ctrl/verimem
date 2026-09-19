"""Cycle 175 (2026-05-22) — Active Learning Design B implementation tests.

Closes the gap empirically observed in fact ``d778cce2faa8``:
  - 233/326 skills (71%) untrialed
  - 3 candidate stuck at fitness 0.33-0.40 (verbatim names cited in
    docs/cycle174_active_learning_design.md)
  - candidate→promoted rate = 7/163 = 4.3%

Design B (greenlit by Aurelio 2026-05-22) is the *stuck-list cron*:
deterministic SELECT, no bandit / no randomness. Pure function
``select_stuck_candidates`` returns a list of skill ids to retry on
the next Auto-Dream cycle. Falsifiable hypothesis H1 lives in the
design doc; this file pins the function's contract.

RED→GREEN: this file must fail import on verimem.active_learning.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

# RED MARKER
from verimem.active_learning import select_stuck_candidates
from verimem.skill import Skill, SkillLibrary

# ---------------------------------------------------------------------------
# Fixture builders — seed a skills_index.db that mimics the production
# corpus shape (fact d778cce2faa8): mix of trialed/untrialed candidates,
# promoted (healthy), retired (low-fitness), and a few "stuck" ones in
# the target band.
# ---------------------------------------------------------------------------


@pytest.fixture
def skill_db(tmp_path: Path) -> Path:
    """Build a small but representative skills_index.db."""
    db_path = tmp_path / "skills_index.db"
    lib = SkillLibrary(
        dir_path=tmp_path / "skills_dir",
        db_path=db_path,
    )

    # 3 STUCK candidates — exactly the target of Design B.
    # fitness = (s+1)/(t+2) → in [0.3, 0.5] band
    stuck_specs = [
        ("Trivial formatting direct output", 4, 1),  # fitness 0.333
        ("Always output valid ReAct format", 4, 1),  # fitness 0.333
        ("Sequential custom string transform", 3, 1),  # fitness 0.400
    ]
    for name, trials, succ in stuck_specs:
        s = Skill(
            name=name,
            trigger=f"trigger for {name}",
            body=f"body for {name}",
            status="candidate",
            trials=trials,
            successes=succ,
        )
        lib.store(s)

    # 1 PROMOTED healthy — fitness > 0.5, must NOT be selected.
    healthy = Skill(
        name="healthy promoted skill",
        trigger="trigger healthy",
        body="body healthy",
        status="promoted",
        trials=10,
        successes=9,  # fitness 10/12 ≈ 0.833
    )
    lib.store(healthy)

    # 1 RETIRED low-fitness — must NOT be selected (wrong status).
    retired = Skill(
        name="correctly retired skill",
        trigger="trigger retired",
        body="body retired",
        status="retired",
        trials=8,
        successes=0,  # fitness 1/10 = 0.1
    )
    lib.store(retired)

    # 1 UNDER-TRIALED candidate (trials=2) — too little evidence, NOT
    # in Design B's target band [3, 10].
    undertrialed = Skill(
        name="too few trials skill",
        trigger="trigger few",
        body="body few",
        status="candidate",
        trials=2,
        successes=1,  # fitness 2/4 = 0.5 (edge)
    )
    lib.store(undertrialed)

    # 1 OVER-TRIALED candidate (trials=15) — past the cron's interest
    # window; if still stuck after 15 trials, retire policy handles it.
    overtrialed = Skill(
        name="over trials stuck skill",
        trigger="trigger over",
        body="body over",
        status="candidate",
        trials=15,
        successes=5,  # fitness 6/17 ≈ 0.353 (in band, but excluded by max_trials)
    )
    lib.store(overtrialed)

    # 1 CANDIDATE in trial range but outside fitness band (too high).
    high_fit = Skill(
        name="high fitness in band skill",
        trigger="trigger high",
        body="body high",
        status="candidate",
        trials=5,
        successes=4,  # fitness 5/7 ≈ 0.714 (above band)
    )
    lib.store(high_fit)

    # 1 untrialed candidate (trials=0) — separate concern (warm-up),
    # NOT what Design B targets.
    untrialed = Skill(
        name="never trialed skill",
        trigger="trigger un",
        body="body un",
        status="candidate",
        trials=0,
        successes=0,
    )
    lib.store(untrialed)

    return db_path


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------


class TestSelectStuckCandidates:
    def test_returns_list_of_ids(self, skill_db: Path) -> None:
        out = select_stuck_candidates(skill_db)
        assert isinstance(out, list)
        assert all(isinstance(x, str) for x in out)

    def test_selects_only_three_stuck_candidates(
        self, skill_db: Path,
    ) -> None:
        """The 3 seeded stuck-band candidates must be selected; the
        healthy/retired/undertrialed/overtrialed/highfit/untrialed
        MUST be excluded."""
        out = select_stuck_candidates(skill_db, max_n=10)
        # We seeded exactly 3 stuck candidates.
        assert len(out) == 3, (
            f"expected 3 stuck candidates, got {len(out)}: {out}"
        )

    def test_excludes_promoted_status(self, skill_db: Path) -> None:
        from verimem.skill import SkillLibrary
        lib = SkillLibrary(
            dir_path=skill_db.parent / "skills_dir",
            db_path=skill_db,
        )
        promoted_ids = {s.id for s in lib.all() if s.status == "promoted"}
        out = set(select_stuck_candidates(skill_db, max_n=10))
        assert out.isdisjoint(promoted_ids), (
            f"promoted skills leaked into selection: "
            f"{out & promoted_ids}"
        )

    def test_excludes_retired_status(self, skill_db: Path) -> None:
        from verimem.skill import SkillLibrary
        lib = SkillLibrary(
            dir_path=skill_db.parent / "skills_dir",
            db_path=skill_db,
        )
        retired_ids = {s.id for s in lib.all() if s.status == "retired"}
        out = set(select_stuck_candidates(skill_db, max_n=10))
        assert out.isdisjoint(retired_ids)

    def test_excludes_under_trialed(self, skill_db: Path) -> None:
        """trials < min_trials must be skipped — separate warm-up
        concern (untrialed/scarce-evidence skills) is a future cycle."""
        from verimem.skill import SkillLibrary
        lib = SkillLibrary(
            dir_path=skill_db.parent / "skills_dir",
            db_path=skill_db,
        )
        too_few = {
            s.id for s in lib.all()
            if s.status == "candidate" and s.trials < 3
        }
        out = set(select_stuck_candidates(
            skill_db, min_trials=3, max_n=10,
        ))
        assert out.isdisjoint(too_few)

    def test_excludes_over_trialed(self, skill_db: Path) -> None:
        """trials > max_trials must be skipped — retire policy domain."""
        from verimem.skill import SkillLibrary
        lib = SkillLibrary(
            dir_path=skill_db.parent / "skills_dir",
            db_path=skill_db,
        )
        too_many = {
            s.id for s in lib.all()
            if s.status == "candidate" and s.trials > 10
        }
        out = set(select_stuck_candidates(
            skill_db, max_trials=10, max_n=10,
        ))
        assert out.isdisjoint(too_many)

    def test_excludes_outside_fitness_band(self, skill_db: Path) -> None:
        """fitness > upper band must be skipped — healthy candidate."""
        from verimem.skill import SkillLibrary
        lib = SkillLibrary(
            dir_path=skill_db.parent / "skills_dir",
            db_path=skill_db,
        )
        healthy = {
            s.id for s in lib.all()
            if s.status == "candidate"
            and (s.successes + 1) / (s.trials + 2) > 0.5
            and 3 <= s.trials <= 10
        }
        out = set(select_stuck_candidates(
            skill_db, fitness_band=(0.3, 0.5), max_n=10,
        ))
        assert out.isdisjoint(healthy)

    def test_max_n_caps_result_size(self, skill_db: Path) -> None:
        out = select_stuck_candidates(skill_db, max_n=2)
        assert len(out) <= 2

    def test_returns_empty_on_empty_db(self, tmp_path: Path) -> None:
        empty_db = tmp_path / "empty.db"
        SkillLibrary(
            dir_path=tmp_path / "empty_dir",
            db_path=empty_db,
        )
        out = select_stuck_candidates(empty_db)
        assert out == []

    def test_returns_empty_on_missing_db(self, tmp_path: Path) -> None:
        """Defensive: nonexistent path → [] (not crash)."""
        out = select_stuck_candidates(tmp_path / "nope.db")
        assert out == []

    def test_default_band_matches_design_doc(self, skill_db: Path) -> None:
        """Sanity: default fitness_band should be (0.3, 0.5) per the
        design doc. Calling without explicit band returns same 3 stuck."""
        out_default = set(select_stuck_candidates(skill_db, max_n=10))
        out_explicit = set(select_stuck_candidates(
            skill_db, fitness_band=(0.3, 0.5), max_n=10,
        ))
        assert out_default == out_explicit

    def test_order_is_deterministic_oldest_updated_first(
        self, tmp_path: Path,
    ) -> None:
        """Cron fairness: oldest updated_at first. Pure function returns
        ids in a deterministic order so two consecutive calls without
        intervening trials produce the same list."""
        db_path = tmp_path / "ordered.db"
        lib = SkillLibrary(
            dir_path=tmp_path / "ordered_dir",
            db_path=db_path,
        )
        # Seed 2 stuck candidates with distinct updated_at.
        s_old = Skill(
            name="older stuck",
            trigger="t1", body="b1",
            status="candidate", trials=4, successes=1,
            updated_at=1000.0,
        )
        s_new = Skill(
            name="newer stuck",
            trigger="t2", body="b2",
            status="candidate", trials=4, successes=1,
            updated_at=2000.0,
        )
        lib.store(s_old)
        lib.store(s_new)
        out1 = select_stuck_candidates(db_path, max_n=2)
        out2 = select_stuck_candidates(db_path, max_n=2)
        # Determinism.
        assert out1 == out2
        # Oldest first.
        assert out1[0] == s_old.id
