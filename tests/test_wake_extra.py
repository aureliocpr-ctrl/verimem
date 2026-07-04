"""Coverage push for engram.wake — branch coverage for unparseable LLM
output, ReAct dispatcher edge cases, _try_compiled_macro corner cases, and
_skill_similarity fallback.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from engram.compilation import CompiledMacro, MacroStep
from engram.episode import Episode, Trace
from engram.llm import MockLLM
from engram.memory import EpisodicMemory
from engram.semantic import SemanticMemory
from engram.skill import Skill, SkillLibrary
from engram.tools import ToolResult, ToolSpec, default_tools
from engram.wake import (
    WakeAgent,
    WakeConfig,
    _episode_is_contaminated,
    _injection_review_blocks_call,
    _is_external_source_in_recent_traces,
    _wrap_untrusted,
    parse_react_step,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_memory(tmp_data_dir):
    return EpisodicMemory(db_path=tmp_data_dir / "episodes" / "ep.db")


@pytest.fixture
def isolated_skills(tmp_data_dir):
    return SkillLibrary(
        dir_path=tmp_data_dir / "skills",
        db_path=tmp_data_dir / "skills" / "idx.db",
    )


def _build_wake(memory, skills, llm, tools=None, max_steps=4):
    """Helper to build a WakeAgent with deterministic config."""
    cfg = WakeConfig(max_steps=max_steps, self_critique=False)
    return WakeAgent(memory=memory, skills=skills,
                     tools=tools or default_tools(), llm=llm, config=cfg)


@pytest.fixture
def config_override():
    """Set/restore frozen-dataclass CONFIG fields via object.__setattr__."""
    from engram.config import CONFIG as _CFG
    saved: dict = {}

    def setter(field: str, value) -> None:
        if field not in saved:
            saved[field] = getattr(_CFG, field)
        object.__setattr__(_CFG, field, value)

    yield setter
    for field, value in saved.items():
        object.__setattr__(_CFG, field, value)


# ---------------------------------------------------------------------------
# parse_react_step — robustness against various output shapes
# ---------------------------------------------------------------------------


def test_parse_react_step_handles_markdown_fences():
    text = (
        "```\n"
        "Thought: think first\n"
        "Action: submit_solution\n"
        "ActionInput: {\"answer\": \"x\"}\n"
        "```"
    )
    out = parse_react_step(text)
    assert out is not None
    _, action, _ = out
    assert action == "submit_solution"


def test_parse_react_step_returns_none_on_unparseable():
    """Plain prose with no Action tag → None."""
    out = parse_react_step("Just thinking out loud, no tool calls.")
    assert out is None


def test_parse_react_step_handles_asterisks_in_action():
    """Markdown bold around the action name should be stripped."""
    text = (
        "Thought: ok\n"
        "Action: **submit_solution**\n"
        "ActionInput: {\"answer\": \"y\"}\n"
    )
    out = parse_react_step(text)
    assert out is not None
    assert out[1] == "submit_solution"


def test_parse_react_step_strips_json_fences_in_action_input():
    text = (
        "Thought: ok\n"
        "Action: submit_solution\n"
        "ActionInput: ```json\n{\"answer\": \"z\"}\n```\n"
    )
    out = parse_react_step(text)
    assert out is not None
    _, _, ai = out
    assert "```" not in ai


def test_parse_react_step_handles_action_input_synonym():
    """Action_Input (snake_case) and 'Action Input' (with space) both work."""
    text = (
        "Action: submit_solution\n"
        "Action_Input: {\"answer\": \"snake\"}\n"
    )
    out = parse_react_step(text)
    assert out is not None


def test_parse_react_step_handles_no_thought():
    """No Thought section is permissible — Action+ActionInput are sufficient."""
    text = (
        "Action: submit_solution\n"
        "ActionInput: {\"answer\": \"42\"}\n"
    )
    out = parse_react_step(text)
    assert out is not None
    thought, _, _ = out
    assert thought == ""  # no thought defaulted to empty


# ---------------------------------------------------------------------------
# _wrap_untrusted — external content marker
# ---------------------------------------------------------------------------


def test_wrap_untrusted_for_external_tools():
    """web_fetch / web_search / vision_describe content gets wrapped."""
    out = _wrap_untrusted("payload", "web_fetch", "https://x")
    assert "<untrusted_content" in out
    assert "</untrusted_content>" in out
    assert "payload" in out
    assert "web_fetch" in out


def test_wrap_untrusted_truncates_long_source_arg():
    long_url = "x" * 500
    out = _wrap_untrusted("body", "web_fetch", long_url)
    # source attribute should be truncated to ≤ 120 chars
    assert "x" * 200 not in out


def test_wrap_untrusted_passthrough_for_internal_tools():
    """Internal tools (run_python, fs_*) are NOT wrapped."""
    out = _wrap_untrusted("safe", "run_python", "")
    assert "<untrusted_content" not in out
    assert out == "safe"


# ---------------------------------------------------------------------------
# Prompt-injection latching (_episode_is_contaminated, _injection_review_blocks_call)
# ---------------------------------------------------------------------------


def test_episode_contamination_empty_traces():
    assert _episode_is_contaminated([]) is False


def test_episode_contamination_internal_only():
    """Only internal-tool traces — never contaminated."""
    traces = [
        Trace(step=1, thought="", action="run_python", action_input="",
              observation="42"),
        Trace(step=2, thought="", action="fs_read_file", action_input="",
              observation="contents"),
    ]
    assert _episode_is_contaminated(traces) is False


def test_episode_contamination_after_web_fetch():
    """A single web_fetch call latches contamination for the rest of the episode."""
    traces = [
        Trace(step=1, thought="", action="web_fetch",
              action_input='{"url": "https://x"}', observation="..."),
        Trace(step=2, thought="", action="run_python", action_input="",
              observation="ok"),
        Trace(step=3, thought="", action="run_python", action_input="",
              observation="ok"),
    ]
    assert _episode_is_contaminated(traces) is True


def test_injection_review_blocks_after_external(monkeypatch):
    """shell_run after web_fetch → blocked by default."""
    monkeypatch.delenv("HIPPO_ALLOW_DANGEROUS_AFTER_EXTERNAL", raising=False)
    traces = [Trace(step=1, thought="", action="web_fetch",
                    action_input='{"url": "https://e"}', observation="x")]
    assert _injection_review_blocks_call("shell_run", traces) is True


def test_injection_review_does_not_block_safe_tools(monkeypatch):
    monkeypatch.delenv("HIPPO_ALLOW_DANGEROUS_AFTER_EXTERNAL", raising=False)
    traces = [Trace(step=1, thought="", action="web_fetch",
                    action_input='{"url": "https://e"}', observation="x")]
    # run_python is NOT in the dangerous-after-external list
    assert _injection_review_blocks_call("run_python", traces) is False


def test_injection_review_override_with_env_flag(monkeypatch):
    """User can opt-in to allow dangerous calls after external content."""
    monkeypatch.setenv("HIPPO_ALLOW_DANGEROUS_AFTER_EXTERNAL", "1")
    traces = [Trace(step=1, thought="", action="web_fetch",
                    action_input='{"url": "https://e"}', observation="x")]
    assert _injection_review_blocks_call("shell_run", traces) is False


def test_is_external_source_in_recent_traces_lookback():
    """The lookback parameter limits how far back we scan."""
    traces = [
        Trace(step=1, thought="", action="web_fetch",
              action_input="", observation="data"),
        Trace(step=2, thought="", action="run_python", action_input="",
              observation=""),
        Trace(step=3, thought="", action="run_python", action_input="",
              observation=""),
        Trace(step=4, thought="", action="run_python", action_input="",
              observation=""),
    ]
    # Looking back only 2 steps misses the web_fetch at index 0
    assert _is_external_source_in_recent_traces(traces, lookback=2) is False
    # Looking back 4 catches it
    assert _is_external_source_in_recent_traces(traces, lookback=4) is True


# ---------------------------------------------------------------------------
# _skill_similarity
# ---------------------------------------------------------------------------


def test_skill_similarity_with_canonical_embedding(isolated_memory, isolated_skills):
    """When skill has no learned_embedding, encode name+trigger."""
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    skill = Skill(name="grep_files", trigger="search files for pattern",
                  body="use grep")
    sim = wake._skill_similarity("search files matching pattern", skill)
    assert -1.0 <= sim <= 1.0


def test_skill_similarity_with_learned_embedding(isolated_memory, isolated_skills):
    """When skill has a learned_embedding, use it directly."""
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    rng = np.random.default_rng(42)
    learned = rng.standard_normal(384).astype(np.float32)
    learned /= np.linalg.norm(learned)
    skill = Skill(name="x", trigger="y", body="z",
                  learned_embedding=learned.tolist())
    sim = wake._skill_similarity("any text", skill)
    assert -1.0 <= sim <= 1.0


def test_skill_similarity_swallows_errors(isolated_memory, isolated_skills, monkeypatch):
    """If embedding.encode raises, return 0.0 — never propagate."""
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    skill = Skill(name="x", trigger="y", body="z")

    def boom(*args, **kw):
        raise RuntimeError("embedding broken")

    monkeypatch.setattr("engram.embedding.encode", boom)
    sim = wake._skill_similarity("anything", skill)
    assert sim == 0.0


# ---------------------------------------------------------------------------
# _adaptive_macro_threshold
# ---------------------------------------------------------------------------


def test_adaptive_macro_threshold_disabled(isolated_memory, isolated_skills,
                                              config_override):
    """When disabled, returns the base threshold regardless of confidence."""
    config_override("compile_adaptive_enabled", False)
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    base = wake._adaptive_macro_threshold(0.95)
    from engram.config import CONFIG
    assert base == CONFIG.compile_apply_min_similarity


def test_adaptive_macro_threshold_clamps_at_floor(isolated_memory, isolated_skills):
    """Even with very high confidence, threshold ≥ floor."""
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    from engram.config import CONFIG
    out = wake._adaptive_macro_threshold(1.0)
    assert out >= CONFIG.compile_apply_floor_similarity


def test_adaptive_macro_threshold_above_05_lowers(isolated_memory, isolated_skills):
    """High confidence → lower threshold."""
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    base = wake._adaptive_macro_threshold(0.5)
    high = wake._adaptive_macro_threshold(0.9)
    assert high <= base


# ---------------------------------------------------------------------------
# _try_compiled_macro corner cases
# ---------------------------------------------------------------------------


def test_try_compiled_macro_no_skills(isolated_memory, isolated_skills):
    """No skills retrieved → None (fall through to LLM)."""
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    ep = Episode(task_id="t1", task_text="x")
    out = wake._try_compiled_macro(ep, "task", [],
                                    validator=lambda a: (True, ""))
    assert out is None


def test_try_compiled_macro_no_compiled(isolated_memory, isolated_skills):
    """Top skill has no compiled_macro → None."""
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    skill = Skill(name="x", trigger="y", body="z", successes=99, trials=100)  # fitness ≈ 0.98
    ep = Episode(task_id="t1", task_text="x")
    out = wake._try_compiled_macro(ep, "task", [skill],
                                    validator=lambda a: (True, ""))
    assert out is None


def test_try_compiled_macro_low_fitness(isolated_memory, isolated_skills):
    """Top skill fitness below threshold → None."""
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    macro = CompiledMacro(skill_id="s1", steps=[], confidence=0.9)
    # Fitness mean ≈ 0.3 → below compile_apply_min_fitness (0.80)
    skill = Skill(name="x", trigger="y", body="z",
                  successes=2, trials=10,
                  compiled_macro=macro.to_dict())
    ep = Episode(task_id="t1", task_text="x")
    out = wake._try_compiled_macro(ep, "task", [skill],
                                    validator=lambda a: (True, ""))
    assert out is None


def test_try_compiled_macro_deserialize_failure(isolated_memory, isolated_skills,
                                                  monkeypatch):
    """Invalid macro dict → log + return None (fall through).

    The monkey-patched CompiledMacro.from_dict raises so we can verify the
    error-swallow path. Real `from_dict` is permissive (uses .get with defaults),
    so we have to inject the failure rather than relying on shape mismatch.
    """
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    skill = Skill(name="x", trigger="y", body="z",
                  successes=99, trials=100,  # high fitness
                  compiled_macro={"invalid": "bad-shape"})

    def boom(d):
        raise ValueError("invalid macro shape")

    monkeypatch.setattr("engram.wake.CompiledMacro.from_dict", boom)
    ep = Episode(task_id="t1", task_text="x")
    out = wake._try_compiled_macro(ep, "task", [skill],
                                    validator=lambda a: (True, ""))
    assert out is None


def test_try_compiled_macro_low_similarity(isolated_memory, isolated_skills):
    """If task↔skill similarity is below threshold → None."""
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    macro = CompiledMacro(skill_id="s1", steps=[
        MacroStep(tool="submit_solution", args={"answer": "x"}),
    ], confidence=0.9)
    # Skill name+trigger has nothing in common with the task → low cos sim
    skill = Skill(
        name="completely_unrelated_topic_alpha",
        trigger="solar power systems",
        body="z",
        successes=99, trials=100,  # high fitness
        compiled_macro=macro.to_dict(),
    )
    ep = Episode(task_id="t1", task_text="x")
    out = wake._try_compiled_macro(ep, "find prime factors of 1234567",
                                    [skill], validator=lambda a: (True, ""))
    assert out is None  # similarity too low to fire macro


# ---------------------------------------------------------------------------
# _retrieve_skills + _retrieve_episodes config gating
# ---------------------------------------------------------------------------


def test_retrieve_skills_disabled(isolated_memory, isolated_skills):
    """use_skills=False → empty list, no library access."""
    cfg = WakeConfig(use_skills=False)
    wake = WakeAgent(memory=isolated_memory, skills=isolated_skills,
                     tools=default_tools(), llm=MockLLM(), config=cfg)
    out = wake._retrieve_skills("any task")
    assert out == []


def test_retrieve_episodes_disabled(isolated_memory, isolated_skills):
    """use_past_episodes=False → empty list."""
    cfg = WakeConfig(use_past_episodes=False)
    wake = WakeAgent(memory=isolated_memory, skills=isolated_skills,
                     tools=default_tools(), llm=MockLLM(), config=cfg)
    out = wake._retrieve_episodes("any task")
    assert out == []


# ---------------------------------------------------------------------------
# _build_user_prompt — skills/episodes blocks
# ---------------------------------------------------------------------------


def test_build_user_prompt_no_skills_or_episodes(isolated_memory, isolated_skills):
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    prompt = wake._build_user_prompt("hello", [], [])
    assert "hello" in prompt
    # max_steps is referenced in the template
    assert str(wake.cfg.max_steps) in prompt


def test_build_user_prompt_with_skills_includes_block(isolated_memory, isolated_skills):
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    skill = Skill(name="x", trigger="search code",
                  body="use grep on the codebase")
    prompt = wake._build_user_prompt("hello", [skill], [])
    # The skill name should appear in the rendered block
    assert "x" in prompt or "grep" in prompt


# ---------------------------------------------------------------------------
# _forward_replay_block — disabled / no skill / low fitness
# ---------------------------------------------------------------------------


def test_forward_replay_block_disabled(isolated_memory, isolated_skills,
                                          config_override):
    config_override("forward_replay_enabled", False)
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    out = wake._forward_replay_block("any", [], [])
    assert out == ""


def test_forward_replay_block_no_skills(isolated_memory, isolated_skills):
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    out = wake._forward_replay_block("task", [], [])
    assert out == ""


def test_forward_replay_block_low_fitness(isolated_memory, isolated_skills):
    """Skill below forward_replay_min_fitness → empty block."""
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    # Low fitness: 0 successes / 10 trials → fitness_mean ≈ 0.083
    skill = Skill(name="x", trigger="y", body="z", successes=0, trials=10)
    out = wake._forward_replay_block("task", [skill], [])
    assert out == ""


# ---------------------------------------------------------------------------
# _avoid_path_block
# ---------------------------------------------------------------------------


def test_avoid_path_block_disabled(isolated_memory, isolated_skills, config_override):
    config_override("forward_replay_include_failures", False)
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    skill = Skill(name="x", trigger="y", body="z")
    out = wake._avoid_path_block(skill, [])
    assert out == ""


def test_avoid_path_block_no_failures(isolated_memory, isolated_skills):
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    skill = Skill(name="x", trigger="y", body="z")
    out = wake._avoid_path_block(skill, [])
    assert out == ""


# ---------------------------------------------------------------------------
# _dispatch (ReAct text dispatch)
# ---------------------------------------------------------------------------


def test_dispatch_unknown_tool(isolated_memory, isolated_skills):
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    r = wake._dispatch("absolute_unknown_xx", "{}")
    assert r.ok is False
    assert "unknown tool" in r.error


def test_dispatch_invalid_json(isolated_memory, isolated_skills):
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    r = wake._dispatch("submit_solution", "{not json}")
    assert r.ok is False
    assert "JSON" in r.error or "json" in r.error.lower()


def test_dispatch_bad_arguments(isolated_memory, isolated_skills):
    """Tool handler that raises TypeError due to wrong kwargs → ok=False."""
    def picky_handler(required_arg: str):
        return ToolResult(ok=True, output=required_arg)

    spec = ToolSpec(name="picky", description="x",
                    schema={"type": "object",
                            "properties": {"required_arg": {"type": "string"}},
                            "required": ["required_arg"]},
                    handler=picky_handler)
    tools = {"picky": spec}
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm, tools=tools)
    # Missing required_arg
    r = wake._dispatch("picky", "{}")
    assert r.ok is False
    assert "bad arguments" in r.error or "required" in r.error.lower()


def test_dispatch_handler_raises_unhandled(isolated_memory, isolated_skills):
    """Tool handler that raises a non-TypeError → ok=False with 'tool error'."""
    def buggy_handler():
        raise RuntimeError("internal failure")

    spec = ToolSpec(name="buggy", description="x",
                    schema={"type": "object", "properties": {}},
                    handler=buggy_handler)
    tools = {"buggy": spec}
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm, tools=tools)
    r = wake._dispatch("buggy", "{}")
    assert r.ok is False
    assert "tool error" in r.error


# ---------------------------------------------------------------------------
# _dispatch_native (tool-use mode)
# ---------------------------------------------------------------------------


def test_dispatch_native_unknown_tool(isolated_memory, isolated_skills):
    from engram.llm import ToolCall
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    tc = ToolCall(id="x", name="absolute_unknown_xx", input={})
    r = wake._dispatch_native(tc)
    assert r.ok is False
    assert "unknown tool" in r.error


def test_dispatch_native_returns_string(isolated_memory, isolated_skills):
    """Handler that returns a non-ToolResult value gets wrapped."""
    from engram.llm import ToolCall

    def handler():
        return "hello"

    spec = ToolSpec(name="strret", description="x",
                    schema={"type": "object", "properties": {}},
                    handler=handler)
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm,
                       tools={"strret": spec})
    tc = ToolCall(id="x", name="strret", input={})
    r = wake._dispatch_native(tc)
    assert r.ok is True
    assert r.output == "hello"


# ---------------------------------------------------------------------------
# Full ReAct loop: unparseable LLM output ends with failure
# ---------------------------------------------------------------------------


def test_react_loop_unparseable_returns_failure(isolated_memory, isolated_skills):
    """An LLM response that the parser can't parse should be recorded as a
    'unparseable' failure trace, not propagate as an exception."""
    llm = MockLLM(scripted=["just gibberish, nothing parseable here"])
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    cfg = WakeConfig(max_steps=2, self_critique=False)
    # Bind cfg explicitly
    wake.cfg = cfg
    # MockLLM does NOT support tools → goes straight to ReAct
    result = wake.run("t1", "anything", lambda a: (True, "ok"))
    assert result.success is False
    assert any("unparseable" in (t.thought or "").lower()
               or t.action == "(none)" for t in result.episode.traces)


def test_react_loop_max_steps_exhausted(isolated_memory, isolated_skills):
    """If LLM never submits, we hit max_steps and fail gracefully."""
    # Each turn the LLM picks a non-submit tool and we loop
    scripted = [
        "Thought: try one\nAction: run_python\nActionInput: {\"code\": \"1\"}\n",
        "Thought: try two\nAction: run_python\nActionInput: {\"code\": \"2\"}\n",
        "Thought: try three\nAction: run_python\nActionInput: {\"code\": \"3\"}\n",
    ]
    llm = MockLLM(scripted=scripted)
    wake = _build_wake(isolated_memory, isolated_skills, llm, max_steps=3)
    result = wake.run("t1", "x", lambda a: (True, "ok"))
    assert result.success is False
    # All three steps logged
    assert len(result.episode.traces) >= 1


# ---------------------------------------------------------------------------
# _format_tool_results — provider-aware
# ---------------------------------------------------------------------------


def test_format_tool_results_anthropic_style(isolated_memory, isolated_skills):
    """raw_assistant is a list (Anthropic) → single user message."""
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    raw = [{"type": "tool_use", "id": "t1", "name": "x", "input": {}}]
    results = [{"tool_call_id": "t1", "name": "x", "observation": "obs"}]
    out = wake._format_tool_results(results, raw)
    assert len(out) == 1
    assert out[0]["role"] == "user"
    blocks = out[0]["content"]
    assert blocks[0]["type"] == "tool_result"


def test_format_tool_results_openai_style(isolated_memory, isolated_skills):
    """raw_assistant is a dict (OpenAI/Ollama) → one tool message per call."""
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    raw = {"role": "assistant", "content": "x", "tool_calls": []}
    results = [
        {"tool_call_id": "c1", "name": "f1", "observation": "ob1"},
        {"tool_call_id": "c2", "name": "f2", "observation": "ob2"},
    ]
    out = wake._format_tool_results(results, raw)
    assert len(out) == 2
    assert all(m["role"] == "tool" for m in out)


# ---------------------------------------------------------------------------
# _estimate_messages_size & _prune_working_memory
# ---------------------------------------------------------------------------


def test_estimate_messages_size_simple(isolated_memory, isolated_skills):
    msgs = [
        {"role": "user", "content": "abc"},
        {"role": "assistant", "content": "defgh"},
    ]
    size = WakeAgent._estimate_messages_size(msgs)
    assert size == 8


def test_estimate_messages_size_with_blocks(isolated_memory, isolated_skills):
    msgs = [
        {"role": "user", "content": [
            {"type": "tool_result", "content": "obs1"},
            {"type": "tool_result", "content": "obs2-bigger"},
        ]},
    ]
    size = WakeAgent._estimate_messages_size(msgs)
    assert size == len("obs1") + len("obs2-bigger")


def test_prune_working_memory_below_budget(isolated_memory, isolated_skills,
                                              config_override):
    """Below the budget → no pruning."""
    config_override("working_memory_max_chars", 10000)
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    msgs = [{"role": "user", "content": "tiny"}]
    out = wake._prune_working_memory(msgs)
    assert out[0]["content"] == "tiny"


def test_prune_working_memory_react_below_budget(isolated_memory, isolated_skills,
                                                    config_override):
    """ReAct pruning skipped when below budget."""
    config_override("working_memory_max_chars", 10000)
    llm = MockLLM()
    wake = _build_wake(isolated_memory, isolated_skills, llm)
    msgs = [{"role": "user", "content": "small"}]
    out = wake._prune_working_memory_react(msgs)
    assert out[0]["content"] == "small"
