"""Tests for forward replay (predict before act).

Before the wake loop runs, we project a 'predicted path' built from past
successful trajectories that used the most relevant skill. This anchors LLM
reasoning and lets us detect divergence (a learning signal).

The block is built deterministically — no LLM calls — so we can test it
without a model.
"""
from __future__ import annotations

from verimem.config import CONFIG
from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory
from verimem.skill import Skill, SkillLibrary
from verimem.wake import WakeAgent, WakeConfig


class _NullLLM:
    def supports_tools(self) -> bool:
        return False


def _make_agent(tmp_data_dir, skills_lib, memory) -> WakeAgent:
    return WakeAgent(memory=memory, skills=skills_lib, llm=_NullLLM(),
                      config=WakeConfig())


def _high_fitness_skill(name: str = "use sieve") -> Skill:
    # Posterior mean = (1+9)/(1+9+1+1) = 10/12 ≈ 0.83
    return Skill(name=name, trigger="when computing primes",
                 body="apply sieve of Eratosthenes",
                 trials=10, successes=9, status="promoted")


def _passing_episode(skill_id: str, task: str, actions: list[str]) -> Episode:
    ep = Episode(
        task_id="t", task_text=task, outcome="success",
        final_answer="ok", skills_used=[skill_id],
    )
    for i, action in enumerate(actions, start=1):
        ep.traces.append(Trace(step=i, thought="t", action=action,
                                action_input="{}", observation="ok"))
    return ep


def test_forward_replay_emits_predicted_path(tmp_data_dir):
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    s = _high_fitness_skill()
    lib.store(s)
    ep = _passing_episode(s.id, "compute primes ≤ 100",
                          ["run_python", "submit_solution"])
    mem.store(ep)

    agent = _make_agent(tmp_data_dir, lib, mem)
    block = agent._forward_replay_block(
        task="find primes up to 50",
        skills=[s],
        episodes=[(ep, 0.9)],
    )
    assert block, "expected a non-empty forward-replay block"
    assert "PREDICTED PATH" in block
    assert "run_python" in block
    assert "submit_solution" in block


def test_forward_replay_silent_below_fitness_threshold(tmp_data_dir):
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    weak = Skill(name="weak", trigger="x", body="x", trials=10, successes=2)  # ~0.27
    lib.store(weak)
    ep = _passing_episode(weak.id, "x", ["run_python", "submit_solution"])
    mem.store(ep)
    agent = _make_agent(tmp_data_dir, lib, mem)
    block = agent._forward_replay_block(task="x", skills=[weak], episodes=[(ep, 0.9)])
    assert block == ""


def test_forward_replay_silent_when_no_episodes(tmp_data_dir):
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    s = _high_fitness_skill()
    lib.store(s)
    agent = _make_agent(tmp_data_dir, lib, mem)
    block = agent._forward_replay_block(task="x", skills=[s], episodes=[])
    assert block == ""


def test_forward_replay_silent_when_disabled(tmp_data_dir):
    """CONFIG is frozen — bypass via object.__setattr__ with cleanup."""
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    s = _high_fitness_skill()
    lib.store(s)
    ep = _passing_episode(s.id, "x", ["run_python", "submit_solution"])
    mem.store(ep)
    agent = _make_agent(tmp_data_dir, lib, mem)
    original = CONFIG.forward_replay_enabled
    object.__setattr__(CONFIG, "forward_replay_enabled", False)
    try:
        block = agent._forward_replay_block(
            task="x", skills=[s], episodes=[(ep, 0.9)]
        )
        assert block == ""
    finally:
        object.__setattr__(CONFIG, "forward_replay_enabled", original)


def test_forward_replay_block_appears_in_user_prompt(tmp_data_dir):
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    s = _high_fitness_skill()
    lib.store(s)
    ep = _passing_episode(s.id, "compute primes",
                          ["run_python", "submit_solution"])
    mem.store(ep)
    agent = _make_agent(tmp_data_dir, lib, mem)
    prompt = agent._build_user_prompt("find primes", [s], [(ep, 0.9)])
    assert "PREDICTED PATH" in prompt
    assert "TASK: find primes" in prompt
