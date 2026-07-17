"""FORGIA pezzo #91 — WakeAgent.metrics() API tests.

Pins the contract:
  1. Returns a dict with the documented keys.
  2. All values are int or float (JSON-serialisable).
  3. Empty agent reports zeros.
"""
from __future__ import annotations

from pathlib import Path


def test_wake_metrics_shape(tmp_path: Path):
    from verimem.memory import EpisodicMemory
    from verimem.skill import SkillLibrary
    from verimem.wake import WakeAgent

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    agent = WakeAgent(memory=mem, skills=skills)
    m = agent.metrics()

    expected = {"n_episodes", "n_skills", "n_skills_promoted",
                "n_skills_candidate", "n_skills_retired",
                "n_last_consideration"}
    assert expected <= m.keys(), m
    for k, v in m.items():
        assert isinstance(v, (int, float)), (k, v)


def test_wake_metrics_zeros_on_empty(tmp_path: Path):
    from verimem.memory import EpisodicMemory
    from verimem.skill import SkillLibrary
    from verimem.wake import WakeAgent

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    agent = WakeAgent(memory=mem, skills=skills)
    m = agent.metrics()
    assert m["n_episodes"] == 0
    assert m["n_skills"] == 0
    assert m["n_last_consideration"] == 0
    # FORGIA #93: success/failure breakdown
    assert m["n_episodes_success"] == 0
    assert m["n_episodes_failure"] == 0


def test_wake_metrics_reflects_stores(tmp_path: Path):
    """FORGIA #94: after store(), metrics() reflects new counts."""
    import time

    from verimem.episode import Episode, Trace
    from verimem.memory import EpisodicMemory
    from verimem.skill import SkillLibrary
    from verimem.wake import WakeAgent

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )

    def _ep(eid, outcome):
        return Episode(
            id=eid, task_id=eid, task_text=eid,
            outcome=outcome, final_answer="ok",
            traces=[Trace(step=1, thought="t", action="a",
                           action_input="", observation="o")],
            tokens_used=1, skills_used=[],
            created_at=time.time(),
        )

    for i in range(3):
        mem.store(_ep(f"s{i}", "success"))
    mem.store(_ep("f1", "failure"))

    agent = WakeAgent(memory=mem, skills=skills)
    m = agent.metrics()
    assert m["n_episodes"] == 4
    assert m["n_episodes_success"] == 3
    assert m["n_episodes_failure"] == 1


def test_wake_metrics_lifetime_success_rate(tmp_path: Path):
    """FORGIA pezzo #130: lifetime_success_rate = n_success / n_total."""
    import time

    from verimem.episode import Episode, Trace
    from verimem.memory import EpisodicMemory
    from verimem.skill import SkillLibrary
    from verimem.wake import WakeAgent

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )

    def _ep(eid, outcome):
        return Episode(
            id=eid, task_id=eid, task_text=eid,
            outcome=outcome, final_answer="ok",
            traces=[Trace(step=1, thought="t", action="a",
                           action_input="", observation="o")],
            tokens_used=1, skills_used=[],
            created_at=time.time(),
        )

    # Empty: 0.0
    agent = WakeAgent(memory=mem, skills=skills)
    assert agent.metrics()["lifetime_success_rate"] == 0.0

    # 3/4 success
    for i in range(3):
        mem.store(_ep(f"s{i}", "success"))
    mem.store(_ep("f1", "failure"))
    m = agent.metrics()
    assert m["lifetime_success_rate"] == 0.75


def test_wake_metrics_includes_token_fields(tmp_path: Path):
    """FORGIA pezzo #151: tokens_total/mean/max present in metrics output."""
    import time

    from verimem.episode import Episode, Trace
    from verimem.memory import EpisodicMemory
    from verimem.skill import SkillLibrary
    from verimem.wake import WakeAgent

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    mem.store(Episode(
        id="e1", task_id="e1", task_text="x",
        outcome="success", final_answer="ok",
        traces=[Trace(step=1, thought="t", action="a",
                       action_input="", observation="o")],
        tokens_used=120, skills_used=[], created_at=time.time(),
    ))
    agent = WakeAgent(memory=mem, skills=skills)
    m = agent.metrics()
    assert m["tokens_total"] == 120.0
    assert m["tokens_mean"] == 120.0
    assert m["tokens_max"] == 120.0


def test_wake_metrics_n_skills_with_macro(tmp_path: Path):
    """FORGIA pezzo #103: n_skills_with_macro counts only skills
    that have a compiled macro attached."""
    from verimem.memory import EpisodicMemory
    from verimem.skill import Skill, SkillLibrary
    from verimem.wake import WakeAgent

    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    s_no_macro = Skill(name="no-macro", trigger="x", body="y")
    s_macro = Skill(
        name="with-macro", trigger="x", body="y",
        compiled_macro={"skill_id": "abc", "steps": []},
    )
    skills.store(s_no_macro)
    skills.store(s_macro)

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    agent = WakeAgent(memory=mem, skills=skills)
    m = agent.metrics()
    assert m["n_skills_with_macro"] == 1
    assert m["n_skills"] == 2
