"""Tests for the user-feedback endpoint (👍/👎 → Bayesian fitness).

Closes the loop between explicit user signal and the same fitness machinery
used by automatic outcomes. Tests use the FastAPI TestClient against the live
dashboard route.

Cycle 167 (2026-05-19): these tests pre-date the cycle 124 secure-by-default
auth flip and used to rely on an env-var leak from
``tests/test_auth_secure_default.py``'s ``clean_env`` fixture (fixed in
cycle 167b). Disable auth explicitly via autouse fixture so the tests stay
focused on the feedback endpoint behaviour rather than the dashboard auth.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from verimem import dashboard
from verimem.episode import Episode, Trace
from verimem.skill import Skill


@pytest.fixture(autouse=True)
def _disable_dashboard_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the feedback POSTs reach the handler instead of the 401 wall.

    Pre-cycle-167 the var leaked into the process from an unrelated test
    and these tests happened to pass; cycle 167 plugged the leak, so this
    fixture now declares the dependency explicitly.
    """
    monkeypatch.setenv("HIPPO_DASHBOARD_AUTH_DISABLED", "1")


@pytest.fixture
def isolated_agent(tmp_path, monkeypatch):
    """Wire the dashboard's _ag() to a fresh agent rooted at tmp_path so the
    test does not pollute the user's real database."""
    from verimem.agent import HippoAgent
    from verimem.memory import EpisodicMemory
    from verimem.semantic import SemanticMemory
    from verimem.skill import SkillLibrary
    from verimem.sleep import SleepEngine
    from verimem.wake import WakeAgent

    mem = EpisodicMemory(tmp_path / "ep.db")
    skills = SkillLibrary(tmp_path / "skills", tmp_path / "skills" / "idx.db")
    sem = SemanticMemory(tmp_path / "sem.db")
    wake = WakeAgent(memory=mem, skills=skills, llm=None)  # not used here
    sleep = SleepEngine(memory=mem, skills=skills, semantic=sem, llm=None)
    agent = HippoAgent(memory=mem, skills=skills, semantic=sem,
                        wake=wake, sleep=sleep)
    monkeypatch.setattr(dashboard, "_AGENT", agent, raising=False)
    monkeypatch.setattr(dashboard, "_ag", lambda: agent)
    return agent


def _seed_episode(agent, skill: Skill) -> Episode:
    agent.skills.store(skill)
    ep = Episode(
        task_id="t", task_text="some task that the user cares about",
        outcome="success", final_answer="done", skills_used=[skill.id],
    )
    ep.traces.append(Trace(step=1, thought="t",
                            action="submit_solution",
                            action_input='{"answer": "done"}',
                            observation="ok"))
    agent.memory.store(ep)
    return ep


def test_thumbs_up_boosts_fitness(isolated_agent):
    s = Skill(name="s", trigger="x", body="x", trials=4, successes=2)
    ep = _seed_episode(isolated_agent, s)
    before_trials = isolated_agent.skills.get(s.id).trials
    before_successes = isolated_agent.skills.get(s.id).successes

    client = TestClient(dashboard.app)
    r = client.post("/api/feedback", json={"episode_id": ep.id, "kind": "up"})
    assert r.status_code == 200
    assert r.json()["skills_updated"] == 1

    after = isolated_agent.skills.get(s.id)
    assert after.trials == before_trials + 1
    assert after.successes == before_successes + 1


def test_thumbs_down_records_failure_and_flips_outcome(isolated_agent):
    s = Skill(name="s", trigger="x", body="x", trials=4, successes=4)
    ep = _seed_episode(isolated_agent, s)

    client = TestClient(dashboard.app)
    r = client.post("/api/feedback", json={"episode_id": ep.id, "kind": "down"})
    assert r.status_code == 200

    after = isolated_agent.skills.get(s.id)
    assert after.trials == 5  # +1 trial
    assert after.successes == 4  # NOT +1 (because down-vote)

    ep_after = isolated_agent.memory.get(ep.id)
    assert ep_after.outcome == "failure"  # flipped from success
    assert "user-feedback:down" in ep_after.notes


def test_feedback_with_unknown_episode_returns_404(isolated_agent):
    client = TestClient(dashboard.app)
    r = client.post("/api/feedback", json={"episode_id": "ghost", "kind": "up"})
    assert r.status_code == 404


def test_feedback_with_invalid_kind_rejected(isolated_agent):
    s = Skill(name="s", trigger="x", body="x")
    ep = _seed_episode(isolated_agent, s)
    client = TestClient(dashboard.app)
    r = client.post("/api/feedback", json={"episode_id": ep.id, "kind": "maybe"})
    assert r.status_code == 400


def test_feedback_with_no_skills_used_is_safe(isolated_agent):
    """An episode with empty skills_used should still accept feedback —
    just nothing to update."""
    ep = Episode(task_id="t", task_text="orphan task",
                  outcome="success", final_answer="done", skills_used=[])
    isolated_agent.memory.store(ep)
    client = TestClient(dashboard.app)
    r = client.post("/api/feedback", json={"episode_id": ep.id, "kind": "up"})
    assert r.status_code == 200
    assert r.json()["skills_updated"] == 0
