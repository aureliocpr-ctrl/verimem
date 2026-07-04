"""CYCLE #28 — test skill name dedup."""
from __future__ import annotations

import pytest

from engram.skill import Skill, SkillLibrary
from engram.skill_name_dedup import dedup_skills_by_name, find_name_duplicate_groups


@pytest.fixture
def library(tmp_path):
    return SkillLibrary(dir_path=tmp_path / "sk", db_path=tmp_path / "sk.db")


def _store(library, sid, name, status="candidate", trials=0, created_at=1000.0):
    library.store(Skill(
        id=sid, name=name, trigger=f"trig {sid}", body="b",
        status=status, trials=trials, created_at=created_at,
    ))


def test_find_no_dups_empty_result(library):
    _store(library, "a", "skill A")
    _store(library, "b", "skill B")
    assert find_name_duplicate_groups(list(library.all())) == []


def test_find_dups_identical_name_status(library):
    _store(library, "a", "use react", trials=5, created_at=100.0)
    _store(library, "b", "use react", trials=3, created_at=200.0)
    _store(library, "c", "use react", trials=10, created_at=50.0)
    groups = find_name_duplicate_groups(list(library.all()))
    assert len(groups) == 1
    g = groups[0]
    assert g["count"] == 3
    # Winner = max trials (c, trials=10)
    assert g["winner_id"] == "c"
    assert set(g["loser_ids"]) == {"a", "b"}


def test_find_dups_ignores_different_status(library):
    """name uguale ma status diverso → 2 gruppi distinti size=1 → niente dup."""
    _store(library, "a", "shared", status="candidate")
    _store(library, "b", "shared", status="promoted")
    assert find_name_duplicate_groups(list(library.all())) == []


def test_dedup_dry_run_no_changes(library):
    for i in range(5):
        _store(library, f"e{i}", "dup name", trials=i)
    r = dedup_skills_by_name(library, apply=False)
    assert r["dry_run"] is True
    assert r["groups_found"] == 1
    assert r["skills_to_retire"] == 4
    assert r["applied_retired"] == 0
    # Nessuna skill retired
    assert all(s.status == "candidate" for s in library.all())


def test_dedup_apply_retires_losers_keeps_winner(library):
    for i in range(5):
        _store(library, f"e{i}", "dup name", trials=i)
    # Winner = e4 (trials=4)
    r = dedup_skills_by_name(library, apply=True)
    assert r["applied_retired"] == 4
    assert library.get("e4").status == "candidate"
    for i in range(4):
        assert library.get(f"e{i}").status == "retired"


def test_dedup_respects_max_retire_cap(library):
    for i in range(10):
        _store(library, f"e{i}", "dup", trials=i)
    r = dedup_skills_by_name(library, apply=True, max_retire=3)
    assert r["applied_retired"] == 3
    assert r["applied_skipped_cap"] == 6


def test_dedup_only_status_filter(library):
    """Skill promoted NON deve essere toccata anche se duplicata."""
    _store(library, "p1", "shared name", status="promoted", trials=10)
    _store(library, "p2", "shared name", status="promoted", trials=5)
    _store(library, "c1", "another dup", status="candidate", trials=3)
    _store(library, "c2", "another dup", status="candidate", trials=1)
    r = dedup_skills_by_name(library, apply=True, only_status="candidate")
    # Solo c2 retired (winner c1)
    assert r["applied_retired"] == 1
    assert library.get("p1").status == "promoted"
    assert library.get("p2").status == "promoted"
    assert library.get("c1").status == "candidate"
    assert library.get("c2").status == "retired"
