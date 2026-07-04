"""Cycle #48b — extend opt-in `return_replaced` observability to
Memory.store (Episodes) and SkillLibrary.store (Skills).

Cycle #46 added the kwarg to SemanticMemory.store; this cycle extends
the SAME pattern to the other two stores for architectural consistency.

Design note (NOT content-hash idempotency):
  - Episodes are temporal phenomena (task X executed at time T).
    Re-executing the same task task_text legitimately produces a fresh
    row — Episode.id remains uuid4().hex (random).
  - Skills get UPDATES (promote/retire/edit/fitness-update) all
    expressed as `store(skill_with_same_id)`. The INSERT OR REPLACE
    path is exercised on every update.

For both, `return_replaced=True` returns a bool reflecting whether a
row with that id existed before the write. Default returns None
(backwards compat).
"""
from __future__ import annotations

import pytest

from engram.episode import Episode
from engram.memory import EpisodicMemory
from engram.skill import Skill, SkillLibrary

# ---------------------------------------------------------------------------
# Memory.store (Episodes)
# ---------------------------------------------------------------------------


@pytest.fixture
def mem(tmp_path):
    return EpisodicMemory(db_path=tmp_path / "episodes.db")


def test_memory_store_fresh_returns_false(mem: EpisodicMemory) -> None:
    ep = Episode(id="ep1", task_text="hello", final_answer="hi")
    replaced = mem.store(ep, return_replaced=True)
    assert replaced is False


def test_memory_store_existing_returns_true(mem: EpisodicMemory) -> None:
    ep = Episode(id="ep1", task_text="hello", final_answer="hi")
    mem.store(ep)
    ep2 = Episode(id="ep1", task_text="hello updated", final_answer="hi v2")
    replaced = mem.store(ep2, return_replaced=True)
    assert replaced is True


def test_memory_store_default_returns_none(mem: EpisodicMemory) -> None:
    ep = Episode(id="ep1", task_text="hello", final_answer="hi")
    result = mem.store(ep)  # no kwarg
    assert result is None


def test_memory_store_overwrite_keeps_new_content(mem: EpisodicMemory) -> None:
    e1 = Episode(id="ep1", task_text="OLD", final_answer="x")
    e2 = Episode(id="ep1", task_text="NEW", final_answer="y")
    mem.store(e1)
    mem.store(e2)
    # Retrieve by id and check
    got = mem.get("ep1")
    assert got is not None
    assert got.task_text == "NEW"


# ---------------------------------------------------------------------------
# SkillLibrary.store (Skills)
# ---------------------------------------------------------------------------


@pytest.fixture
def skills(tmp_path):
    return SkillLibrary(
        db_path=tmp_path / "skills_index.db",
        dir_path=tmp_path / "skills",
    )


def test_skill_store_fresh_returns_false(skills: SkillLibrary) -> None:
    sk = Skill(id="sk1", name="example", trigger="trig", body="do thing")
    replaced = skills.store(sk, return_replaced=True)
    assert replaced is False


def test_skill_store_update_returns_true(skills: SkillLibrary) -> None:
    sk = Skill(id="sk1", name="example", trigger="trig", body="v1")
    skills.store(sk)
    sk2 = Skill(id="sk1", name="example", trigger="trig", body="v2")
    replaced = skills.store(sk2, return_replaced=True)
    assert replaced is True


def test_skill_store_default_returns_none(skills: SkillLibrary) -> None:
    sk = Skill(id="sk1", name="example", trigger="trig", body="x")
    result = skills.store(sk)  # no kwarg
    assert result is None


def test_skill_store_update_keeps_new_body(skills: SkillLibrary) -> None:
    s1 = Skill(id="sk1", name="example", trigger="trig", body="OLD")
    s2 = Skill(id="sk1", name="example", trigger="trig", body="NEW")
    skills.store(s1)
    skills.store(s2)
    got = skills.get("sk1")
    assert got is not None
    assert got.body == "NEW"
