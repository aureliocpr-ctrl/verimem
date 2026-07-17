"""When a compiled macro fails, the partial trace must be salvaged
into `episode.notes` before traces.clear() resets the step numbering.

The contract: even though traces[] gets wiped to make room for the
LLM-loop fallback, the information about WHAT the macro did and WHERE
it died lives on in episode.notes for post-hoc inspection (and for
trace alignment when this failure is later compared to its success-twin).
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from verimem.compilation import CompiledMacro, MacroRunResult, MacroStep
from verimem.episode import Episode
from verimem.skill import Skill, SkillLibrary
from verimem.wake import WakeAgent, WakeConfig


@pytest.fixture
def wake_with_failing_macro(tmp_data_dir, monkeypatch):
    """Build a WakeAgent whose top skill has a macro that returns
    not-ok (simulating a real macro abort)."""
    from verimem.memory import EpisodicMemory
    skills = SkillLibrary(
        dir_path=tmp_data_dir / "skills",
        db_path=tmp_data_dir / "skills_index.db",
    )
    memory = EpisodicMemory(db_path=tmp_data_dir / "ep.db")

    macro = CompiledMacro(
        skill_id="sk_compiled",
        steps=[
            MacroStep(tool="fs_read_file", args={"path": "{{TASK}}"}),
            MacroStep(tool="apply_edit",   args={}),
            MacroStep(tool="submit_solution", args={"answer": "ok"}),
        ],
        confidence=0.95,
    )
    skill = Skill(
        id="sk_compiled", name="bugfix",
        trigger="fix arithmetic bug", body="patch",
        # high fitness so the macro_apply_min_fitness gate (default 0.80)
        # passes deterministically
        status="promoted", trials=20, successes=20,
        compiled_macro=macro.to_dict(),
    )
    skills.store(skill)

    # Mock execute_macro to return a failed run with a couple of steps
    # already executed (mimicking a real abort at step 2).
    fake_result = MacroRunResult(
        ok=False,
        traces=[
            {"step": 1, "tool": "fs_read_file",
             "args": {"path": "calc.py"}, "observation": "ok",
             "ok": True},
            {"step": 2, "tool": "apply_edit", "args": {},
             "observation": "tool error: missing arg",
             "ok": False},
        ],
        aborted_at_step=2,
        reason="bad args for apply_edit: missing 'patch'",
    )
    monkeypatch.setattr(
        "verimem.wake.execute_macro",
        lambda macro, task_text, tools: fake_result,
    )

    agent = WakeAgent(
        memory=memory, skills=skills, llm=MagicMock(),
        config=WakeConfig(),
    )
    # Seed similarity high enough to fire the macro
    monkeypatch.setattr(
        agent, "_skill_similarity", lambda task, skill: 0.99,
    )
    return agent, skill


def test_aborted_macro_partial_trace_salvaged_to_notes(wake_with_failing_macro):
    agent, skill = wake_with_failing_macro
    ep = Episode(id="ep_x", task_id="t", task_text="fix calc.py")
    out = agent._try_compiled_macro(
        episode=ep, task_text="fix calc.py",
        skills=[skill], validator=lambda a: (True, "ok"),
    )
    # Macro path returns None on abort — caller falls back to LLM.
    assert out is None
    # Traces must have been cleared (so the LLM loop can renumber from 1).
    assert ep.traces == []
    # But the partial info lives on in notes.
    assert "macro_aborted" in ep.notes
    assert "step=2" in ep.notes
    assert "fs_read_file" in ep.notes  # the prefix that DID run
    assert "apply_edit" in ep.notes    # the step that aborted
    assert "missing 'patch'" in ep.notes  # the reason


def test_aborted_macro_with_no_partial_trace_does_not_crash(
    tmp_data_dir, monkeypatch,
):
    """If the macro aborts at step 1 with zero recorded traces, the
    salvage block must still produce a reasonable notes line — or
    leave notes empty without throwing."""
    from verimem.memory import EpisodicMemory
    skills = SkillLibrary(
        dir_path=tmp_data_dir / "skills",
        db_path=tmp_data_dir / "skills_index.db",
    )
    memory = EpisodicMemory(db_path=tmp_data_dir / "ep.db")

    macro = CompiledMacro(
        skill_id="sk", steps=[MacroStep(tool="fs_read_file", args={})],
        confidence=0.9,
    )
    skill = Skill(
        id="sk", name="x", trigger="y", body="z",
        # high fitness so the macro_apply_min_fitness gate (default 0.80)
        # passes deterministically
        status="promoted", trials=20, successes=20,
        compiled_macro=macro.to_dict(),
    )
    skills.store(skill)

    monkeypatch.setattr(
        "verimem.wake.execute_macro",
        lambda macro, task_text, tools: MacroRunResult(
            ok=False, traces=[], aborted_at_step=1, reason="unknown tool",
        ),
    )
    agent = WakeAgent(
        memory=memory, skills=skills, llm=MagicMock(),
        config=WakeConfig(),
    )
    monkeypatch.setattr(
        agent, "_skill_similarity", lambda task, skill: 0.99,
    )
    ep = Episode(id="ep_y", task_id="t", task_text="x")
    agent._try_compiled_macro(
        episode=ep, task_text="x", skills=[skill],
        validator=lambda a: (True, "ok"),
    )
    # No partial trace → notes left empty (or skipped). Just don't crash.
    assert ep.traces == []
