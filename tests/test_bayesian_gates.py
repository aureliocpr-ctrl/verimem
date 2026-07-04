"""Tests for FORGIA pezzo #4: gates `fitness_mean → fitness_lower_bound`.

The macro fast-path and forward-replay block both gate on a skill's
Beta posterior. Before pezzo #4 they used the *mean* (optimistic for
small samples). Now they use the 5%-quantile (`fitness_lower_bound`):
"we are statistically confident the skill works" instead of "the
skill probably works in average".

Concrete invariant we test:

  Skill A: trials=3, successes=3 → mean ~0.80, lower_bound ~0.47
  Skill B: trials=20, successes=18 → mean ~0.86, lower_bound ~0.74

  Legacy gate (mean ≥ 0.80):    A passes,  B passes
  Bayesian gate (lower ≥ 0.65): A REJECTED, B passes

A is a textbook over-confidence trap: 3/3 looks good but is too few
trials to stake a deterministic macro on. The Bayesian gate is the
exact mechanism that closes that trap.
"""
from __future__ import annotations

import dataclasses
from unittest.mock import MagicMock

import pytest

from engram import config as config_mod
from engram.compilation import CompiledMacro, MacroRunResult, MacroStep
from engram.config import CONFIG
from engram.episode import Episode
from engram.memory import EpisodicMemory
from engram.skill import Skill, SkillLibrary
from engram.wake import WakeAgent, WakeConfig


def _patch_config(monkeypatch, **fields) -> None:
    """Frozen-dataclass-safe CONFIG mutation: replace the binding."""
    new = dataclasses.replace(CONFIG, **fields)
    monkeypatch.setattr(config_mod, "CONFIG", new)
    # wake.py / skill.py import CONFIG at module load — re-bind there too.
    from engram import skill as skill_mod
    from engram import wake as wake_mod
    monkeypatch.setattr(wake_mod, "CONFIG", new)
    monkeypatch.setattr(skill_mod, "CONFIG", new)


def _build_macro(skill_id: str = "sk") -> CompiledMacro:
    return CompiledMacro(
        skill_id=skill_id,
        steps=[MacroStep(tool="fs_read_file", args={"path": "x"})],
        confidence=0.95,
    )


def _build_skill(
    *, trials: int, successes: int, with_macro: bool = True,
) -> Skill:
    return Skill(
        id=f"sk_{trials}_{successes}",
        name="bugfix",
        trigger="fix",
        body="patch",
        status="promoted",
        trials=trials,
        successes=successes,
        compiled_macro=_build_macro().to_dict() if with_macro else None,
    )


def _build_agent(tmp_data_dir, monkeypatch, *, skill: Skill):
    skills = SkillLibrary(
        dir_path=tmp_data_dir / "skills",
        db_path=tmp_data_dir / "skills_index.db",
    )
    skills.store(skill)
    memory = EpisodicMemory(db_path=tmp_data_dir / "ep.db")
    monkeypatch.setattr(
        "engram.wake.execute_macro",
        lambda macro, task_text, tools: MacroRunResult(
            ok=True, traces=[], final_answer="done",
        ),
    )
    agent = WakeAgent(
        memory=memory, skills=skills, llm=MagicMock(),
        config=WakeConfig(),
    )
    # Force the macro similarity gate to always pass — we're testing
    # the FITNESS gate here, not the similarity one.
    monkeypatch.setattr(agent, "_skill_similarity", lambda task, sk: 0.99)
    return agent


# ---------- Bayesian gate REJECTS small-N high-mean skill -----------------


def test_macro_gate_rejects_immature_skill_under_bayesian_path(
    tmp_data_dir, monkeypatch,
):
    """Skill with 3/3 successes: mean ~0.80, lower_bound ~0.47.

    Legacy gate (mean ≥ 0.80) PASSES — over-confident.
    Bayesian gate (lower_bound ≥ 0.65) REJECTS — correct.
    """
    _patch_config(
        monkeypatch,
        compile_apply_use_lower_bound=True,
        compile_apply_min_lower_bound=0.65,
    )
    skill = _build_skill(trials=3, successes=3)
    agent = _build_agent(tmp_data_dir, monkeypatch, skill=skill)

    ep = Episode(id="ep_a", task_id="t", task_text="fix")
    out = agent._try_compiled_macro(
        episode=ep, task_text="fix", skills=[skill],
        validator=lambda a: (True, "ok"),
    )
    # Macro NOT applied → caller falls back to LLM loop.
    assert out is None, (
        "Bayesian gate let an immature skill (3/3 successes, "
        "lower_bound ~0.47) bypass the LLM via macro — that's the "
        "over-confidence trap pezzo #4 was meant to close"
    )


def test_macro_gate_accepts_mature_skill_under_bayesian_path(
    tmp_data_dir, monkeypatch,
):
    """Skill with 20 trials, 18 successes: mean ~0.86, lower ~0.74.
    Both gates pass. Bayesian gate doesn't break the happy path."""
    _patch_config(
        monkeypatch,
        compile_apply_use_lower_bound=True,
        compile_apply_min_lower_bound=0.65,
    )
    skill = _build_skill(trials=20, successes=18)
    agent = _build_agent(tmp_data_dir, monkeypatch, skill=skill)

    ep = Episode(id="ep_b", task_id="t", task_text="fix")
    out = agent._try_compiled_macro(
        episode=ep, task_text="fix", skills=[skill],
        validator=lambda a: (True, "ok"),
    )
    assert out is not None
    success, _msg = out
    assert success is True


# ---------- Legacy mode preserves old behaviour ---------------------------


def test_macro_gate_legacy_path_unaffected_by_lower_bound_when_flag_off(
    tmp_data_dir, monkeypatch,
):
    """With `compile_apply_use_lower_bound=False` the gate falls back to
    `fitness_mean ≥ compile_apply_min_fitness` — same as before pezzo #4.
    A skill with 3/3 successes (mean 0.80) PASSES legacy path."""
    _patch_config(
        monkeypatch,
        compile_apply_use_lower_bound=False,
        compile_apply_min_fitness=0.80,
    )
    skill = _build_skill(trials=3, successes=3)
    agent = _build_agent(tmp_data_dir, monkeypatch, skill=skill)

    ep = Episode(id="ep_c", task_id="t", task_text="fix")
    out = agent._try_compiled_macro(
        episode=ep, task_text="fix", skills=[skill],
        validator=lambda a: (True, "ok"),
    )
    # Legacy path: 3/3 has mean = 4/(4+1) = 0.80 ≥ threshold → macro fires.
    assert out is not None


# ---------- Forward replay block uses lower_bound when enabled ------------


def test_forward_replay_block_rejects_immature_skill_under_bayesian(
    tmp_data_dir, monkeypatch,
):
    """Forward-replay block is informational — anchors the LLM with a
    'predicted path' from past traces. Same rationale as macro: don't
    anchor with a skill we're not statistically confident in.

    With `forward_replay_use_lower_bound=True` and lower=0.30 floor,
    a skill with 1/1 (lower ~0.22) gets no replay block.
    """
    _patch_config(
        monkeypatch,
        forward_replay_use_lower_bound=True,
        forward_replay_min_lower_bound=0.30,
    )
    skill = _build_skill(trials=1, successes=1, with_macro=False)
    agent = _build_agent(tmp_data_dir, monkeypatch, skill=skill)

    block = agent._forward_replay_block("fix the bug", [skill], [])
    # Empty string means "no block emitted" — gate did its job.
    assert block == ""


def test_forward_replay_block_accepts_mature_skill_under_bayesian(
    tmp_data_dir, monkeypatch,
):
    """A mature skill (10 trials, 9 successes; lower ~0.62) passes the
    0.30 lower-bound floor and the block is emitted (when episodes exist
    and the existing predicates hold)."""
    _patch_config(
        monkeypatch,
        forward_replay_use_lower_bound=True,
        forward_replay_min_lower_bound=0.30,
        forward_replay_enabled=True,
    )
    skill = _build_skill(trials=10, successes=9, with_macro=False)
    agent = _build_agent(tmp_data_dir, monkeypatch, skill=skill)
    # Build a successful episode that used this skill.
    ep_success = Episode(
        id="ep_past", task_id="t_past", task_text="fix the bug",
        outcome="success", final_answer="done",
        skills_used=[skill.id],
    )
    # Add a single-step trace so action_seq is non-empty.
    from engram.episode import Trace
    ep_success.traces.append(Trace(
        step=1, thought="t", action="fs_read_file",
        action_input='{"path":"x"}', observation="ok",
    ))

    block = agent._forward_replay_block(
        "fix the bug", [skill], [(ep_success, 0.99)],
    )
    assert "PREDICTED PATH" in block, (
        "Mature skill got blocked by the new lower_bound gate when it "
        "shouldn't — threshold tuning is too aggressive"
    )


# ---------- Sanity: numerical math for the test thresholds ----------------


def test_lower_bound_numerics_match_test_assumptions():
    """Documents the lower_bound math the other tests rely on. If
    `Skill.fitness_lower_bound`'s scipy.stats import breaks or its
    formula drifts, this test fails first with a clear cause."""
    from engram.skill import Skill as S

    # 3/3 successes → mean ~0.80, lower ~0.47
    s = S(id="x", name="x", trigger="x", body="x", trials=3, successes=3)
    assert s.fitness_mean == pytest.approx(0.80, abs=0.01)
    assert s.fitness_lower_bound == pytest.approx(0.47, abs=0.05)

    # 20/18 → mean ~0.86, lower ~0.74
    s = S(id="x", name="x", trigger="x", body="x", trials=20, successes=18)
    assert s.fitness_mean == pytest.approx(0.864, abs=0.01)
    assert s.fitness_lower_bound == pytest.approx(0.74, abs=0.05)

    # 1/1 → mean ~0.67, lower ~0.22
    s = S(id="x", name="x", trigger="x", body="x", trials=1, successes=1)
    assert s.fitness_mean == pytest.approx(0.667, abs=0.01)
    assert s.fitness_lower_bound == pytest.approx(0.22, abs=0.05)
