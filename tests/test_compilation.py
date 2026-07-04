"""Tests for procedural compilation: skill → deterministic macro.

Compilation distils successful traces into parameterised tool-call sequences
that bypass the LLM at wake time. Tests cover:
  • Compilation pipeline (LLM-driven, mocked).
  • Macro execution (placeholder substitution, error handling).
  • Wake-time fast-path: macro fires when applicable, falls through on failure.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engram.compilation import (
    CompiledMacro,
    MacroStep,
    compile_macro,
    execute_macro,
)
from engram.episode import Episode, Trace
from engram.skill import Skill, SkillLibrary
from engram.tools import ToolResult, ToolSpec

# --- Test doubles ----------------------------------------------------------


@dataclass
class _LLMResp:
    text: str
    input_tokens: int = 1
    output_tokens: int = 1
    model: str = "mock"
    latency_s: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class _MockLLM:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.calls = 0

    def supports_tools(self) -> bool:
        return False

    def complete(self, system, messages, **kwargs) -> _LLMResp:
        self.calls += 1
        return _LLMResp(text=self.response_text)


def _success_episode(skill_id: str, task: str, actions: list[tuple[str, str]]) -> Episode:
    ep = Episode(task_id="t", task_text=task, outcome="success",
                  final_answer="ok", skills_used=[skill_id])
    for i, (action, action_input) in enumerate(actions, start=1):
        ep.traces.append(Trace(step=i, thought="t", action=action,
                                action_input=action_input, observation="ok"))
    return ep


def _make_skill() -> Skill:
    return Skill(name="save to file", trigger="when asked to write content to disk",
                 body="x", successes=10, trials=10)


# --- Compilation -----------------------------------------------------------


def test_compile_macro_extracts_steps_from_llm_json():
    skill = _make_skill()
    eps = [
        _success_episode(skill.id, f"save '{w}' to file", [
            ("fs_write_file", '{"path": "out.txt", "content": "' + w + '"}'),
            ("submit_solution", '{"answer": "saved"}'),
        ])
        for w in ("hello", "world", "foo", "bar", "baz")
    ]
    llm_response = """{
  "steps": [
    {"tool": "fs_write_file", "args": {"path": "out.txt", "content": "{{TASK}}"}},
    {"tool": "submit_solution", "args": {"answer": "saved"}}
  ],
  "confidence": 0.9,
  "rationale": "consistent two-step pattern"
}"""
    macro = compile_macro(skill, eps, _MockLLM(llm_response))
    assert macro is not None
    assert len(macro.steps) == 2
    assert macro.steps[0].tool == "fs_write_file"
    assert macro.steps[1].tool == "submit_solution"
    assert macro.confidence == 0.9
    assert macro.skill_id == skill.id


def test_compile_macro_rejects_missing_terminator():
    skill = _make_skill()
    eps = [_success_episode(skill.id, "x", [("foo", "{}")])] * 5
    bad = """{"steps": [{"tool": "foo", "args": {}}], "confidence": 0.5}"""
    macro = compile_macro(skill, eps, _MockLLM(bad))
    assert macro is None  # no submit_solution at the end → reject


def test_compile_macro_rejects_invalid_json():
    skill = _make_skill()
    eps = [_success_episode(skill.id, "x", [("foo", "{}")])] * 5
    macro = compile_macro(skill, eps, _MockLLM("not even close to json"))
    assert macro is None


def test_compile_macro_needs_minimum_episodes():
    skill = _make_skill()
    eps = [_success_episode(skill.id, "x", [("submit_solution", "{}")])] * 2  # only 2
    response = """{"steps": [{"tool": "submit_solution", "args": {}}], "confidence": 1.0}"""
    macro = compile_macro(skill, eps, _MockLLM(response))
    assert macro is None  # below CONFIG.compile_min_successes


# --- Macro execution -------------------------------------------------------


def test_execute_macro_substitutes_task_placeholder():
    captured: dict[str, Any] = {}

    def write_handler(*, path: str, content: str) -> ToolResult:
        captured["path"] = path
        captured["content"] = content
        return ToolResult(ok=True, output="written")

    def submit_handler(*, answer: str) -> ToolResult:
        captured["answer"] = answer
        return ToolResult(ok=True, output="submitted")

    tools = {
        "fs_write_file": ToolSpec(
            name="fs_write_file", description="x", schema={}, handler=write_handler
        ),
        "submit_solution": ToolSpec(
            name="submit_solution", description="x", schema={}, handler=submit_handler
        ),
    }
    macro = CompiledMacro(
        skill_id="s1",
        steps=[
            MacroStep(tool="fs_write_file",
                      args={"path": "/tmp/out.txt", "content": "{{TASK}}"}),
            MacroStep(tool="submit_solution", args={"answer": "saved"}),
        ],
    )
    result = execute_macro(macro, "the quick brown fox", tools)
    assert result.ok
    assert result.final_answer == "saved"
    assert captured["content"] == "the quick brown fox"
    assert captured["path"] == "/tmp/out.txt"
    assert len(result.traces) == 2


def test_execute_macro_aborts_on_tool_error():
    def boom(**_: Any) -> ToolResult:
        raise RuntimeError("kaboom")

    tools = {
        "boom": ToolSpec(name="boom", description="", schema={}, handler=boom),
        "submit_solution": ToolSpec(
            name="submit_solution", description="", schema={},
            handler=lambda **kw: ToolResult(ok=True, output="ok"),
        ),
    }
    macro = CompiledMacro(
        skill_id="s",
        steps=[MacroStep(tool="boom", args={}),
               MacroStep(tool="submit_solution", args={"answer": "x"})],
    )
    result = execute_macro(macro, "task", tools)
    assert not result.ok
    assert result.aborted_at_step == 1
    assert "kaboom" in result.reason


def test_execute_macro_aborts_on_unknown_tool():
    tools: dict[str, ToolSpec] = {}
    macro = CompiledMacro(skill_id="s",
                          steps=[MacroStep(tool="ghost", args={})])
    result = execute_macro(macro, "task", tools)
    assert not result.ok
    assert result.aborted_at_step == 1
    assert "unknown tool" in result.reason


def test_execute_macro_threads_last_observation():
    seen: list[str] = []

    def step1(**_: Any) -> ToolResult:
        return ToolResult(ok=True, output="OBSERVATION_FROM_STEP_1")

    def step2(*, recap: str) -> ToolResult:
        seen.append(recap)
        return ToolResult(ok=True, output="ok")

    def submit(*, answer: str) -> ToolResult:
        return ToolResult(ok=True, output=answer)

    tools = {
        "step1": ToolSpec(name="step1", description="", schema={}, handler=step1),
        "step2": ToolSpec(name="step2", description="", schema={}, handler=step2),
        "submit_solution": ToolSpec(
            name="submit_solution", description="", schema={}, handler=submit
        ),
    }
    macro = CompiledMacro(
        skill_id="s",
        steps=[
            MacroStep(tool="step1", args={}),
            MacroStep(tool="step2", args={"recap": "prev was {{LAST_OBSERVATION}}"}),
            MacroStep(tool="submit_solution", args={"answer": "done"}),
        ],
    )
    result = execute_macro(macro, "task", tools)
    assert result.ok
    # to_observation() prepends ToolResult metadata; we just assert the
    # placeholder was substituted with the actual step-1 output content.
    assert len(seen) == 1
    assert "OBSERVATION_FROM_STEP_1" in seen[0]
    assert seen[0].startswith("prev was ")


# --- Skill persistence ----------------------------------------------------


def test_wake_fast_path_bypasses_llm_when_macro_applies(tmp_data_dir):
    """End-to-end: a high-fitness skill with a compiled macro is applied
    by WakeAgent without ever invoking the LLM."""
    from engram.memory import EpisodicMemory
    from engram.tools import default_tools
    from engram.wake import WakeAgent, WakeConfig, trivial_validator

    captured: dict[str, Any] = {}

    class _RecordingLLM:
        def __init__(self) -> None:
            self.complete_calls = 0
            self.tools_calls = 0

        def supports_tools(self) -> bool:
            return False

        def complete(self, *a, **kw):
            self.complete_calls += 1
            raise AssertionError("LLM must not be called when macro fires")

        def complete_with_tools(self, *a, **kw):
            self.tools_calls += 1
            raise AssertionError("LLM must not be called when macro fires")

    def submit(*, answer: str) -> ToolResult:
        captured["answer"] = answer
        return ToolResult(ok=True, output=answer)

    tools = dict(default_tools())
    tools["submit_solution"] = ToolSpec(
        name="submit_solution", description="finish",
        schema={"type": "object", "properties": {"answer": {"type": "string"}}},
        handler=submit,
    )

    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    s = Skill(
        name="echo task",
        trigger="when asked to echo a phrase back",
        body="just submit the phrase",
        trials=10, successes=10, status="promoted",
        compiled_macro=CompiledMacro(
            skill_id="x",  # rewritten when stored
            steps=[MacroStep(tool="submit_solution",
                             args={"answer": "echoed: {{TASK}}"})],
            confidence=0.95,
        ).to_dict(),
    )
    s.compiled_macro["skill_id"] = s.id
    lib.store(s)

    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    rec_llm = _RecordingLLM()
    agent = WakeAgent(memory=mem, skills=lib, tools=tools,
                      llm=rec_llm, config=WakeConfig())
    result = agent.run(task_id="t",
                       task_text="echo a phrase back",
                       validator=trivial_validator)

    assert result.success
    assert "echoed: echo a phrase back" in captured["answer"]
    assert rec_llm.complete_calls == 0
    assert rec_llm.tools_calls == 0


def test_compiled_macro_round_trips_through_skill_storage(tmp_data_dir):
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    s = Skill(name="x", trigger="x", body="x")
    macro = CompiledMacro(skill_id=s.id, steps=[
        MacroStep(tool="submit_solution", args={"answer": "x"}),
    ], confidence=0.7)
    s.compiled_macro = macro.to_dict()
    lib.store(s)
    reloaded = lib.get(s.id)
    assert reloaded is not None
    assert reloaded.compiled_macro is not None
    rebuilt = CompiledMacro.from_dict(reloaded.compiled_macro)
    assert rebuilt.skill_id == s.id
    assert rebuilt.steps[0].tool == "submit_solution"
    assert rebuilt.confidence == 0.7

def test_extract_json_rejects_non_object_payloads():
    """FORGIA pezzo #31 regression: a JSON scalar/list must not be
    returned by _extract_json — downstream `"key" in data` would crash."""
    from engram.compilation import _extract_json
    assert _extract_json("4") is None
    assert _extract_json('"hello"') is None
    assert _extract_json("[1, 2, 3]") is None
    assert _extract_json("null") is None
    assert _extract_json("true") is None
    assert _extract_json('{"name": "x"}') == {"name": "x"}
    assert _extract_json('```json\n{"name": "y"}\n```') == {"name": "y"}
    assert _extract_json("not json at all") is None

