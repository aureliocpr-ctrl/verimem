"""Native tool-use loop tests (regression for the parallel-call UNIQUE bug)."""
from __future__ import annotations

from typing import Any

from verimem.llm import LLMToolResponse, ToolCall
from verimem.memory import EpisodicMemory
from verimem.semantic import SemanticMemory
from verimem.skill import SkillLibrary
from verimem.tools import ToolResult, ToolSpec
from verimem.wake import WakeAgent


class ScriptedToolLLM:
    """LLM mock that supports the native tool-use API.

    Pass a list of `(text, [ToolCall, ...])` tuples — one per turn.
    """
    def __init__(self, script: list[tuple[str, list[ToolCall]]]):
        self._script = list(script)
        self.calls: list[Any] = []

    def supports_tools(self) -> bool:
        return True

    def complete(self, system, messages, model=None, temperature=0.0,
                 max_tokens=None, stop_sequences=None):
        # Used only by critic / fallback; never reached in these tests.
        from verimem.llm import LLMResponse
        return LLMResponse(text="", input_tokens=0, output_tokens=0,
                           model="mock", latency_s=0.0)

    def complete_with_tools(self, system, messages, tools, model=None,
                            temperature=0.0, max_tokens=None):
        self.calls.append({"messages": messages, "tools": tools})
        text, tool_calls = self._script.pop(0)
        # Anthropic-style raw_content (list of blocks)
        raw = []
        if text:
            raw.append({"type": "text", "text": text})
        for tc in tool_calls:
            raw.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.input})
        return LLMToolResponse(
            text=text, tool_calls=tool_calls,
            input_tokens=20, output_tokens=10,
            model="mock", latency_s=0.0, raw_content=raw,
        )


def _toolspec(name: str, handler):
    return ToolSpec(
        name=name, description=f"test {name}",
        schema={"type": "object", "properties": {"x": {"type": "string"}},
                "required": ["x"]},
        handler=handler,
    )


def test_native_tool_use_single_call(tmp_data_dir):
    """One tool call per turn, ending with submit_solution."""
    captured = []
    tools = {
        "echo": _toolspec("echo", lambda x: ToolResult(ok=True, output=f"got:{x}")),
        "submit_solution": _toolspec(
            "submit_solution",
            lambda answer: ToolResult(ok=True, output=str(answer)),
        ),
    }
    # First turn: echo "hi"; second turn: submit_solution
    script = [
        ("step1", [ToolCall(id="t1", name="echo", input={"x": "hi"})]),
        ("step2", [ToolCall(id="t2", name="submit_solution",
                            input={"answer": "done!"})]),
    ]
    llm = ScriptedToolLLM(script)
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    sk = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills.db")
    sem = SemanticMemory(tmp_data_dir / "sem.db")
    wake = WakeAgent(memory=mem, skills=sk, tools=tools, llm=llm)

    result = wake.run("t-single", "do something",
                       lambda ans: ("done!" in ans, "ok"))
    assert result.success
    assert "done!" in result.episode.final_answer
    assert mem.count() == 1
    # 2 traces from native tool calls
    eps = mem.all()[0]
    assert len(eps.traces) == 2
    assert {t.action for t in eps.traces} == {"echo", "submit_solution"}


def test_native_tool_use_parallel_calls(tmp_data_dir):
    """Multiple tool calls in ONE turn must produce unique trace.step values
    (regression for sqlite UNIQUE constraint on (episode_id, step))."""
    tools = {
        "echo": _toolspec("echo", lambda x: ToolResult(ok=True, output=f"got:{x}")),
        "submit_solution": _toolspec(
            "submit_solution",
            lambda answer: ToolResult(ok=True, output=str(answer)),
        ),
    }
    # Single LLM turn with 3 parallel tool calls
    script = [
        ("parallel", [
            ToolCall(id="t1", name="echo", input={"x": "a"}),
            ToolCall(id="t2", name="echo", input={"x": "b"}),
            ToolCall(id="t3", name="echo", input={"x": "c"}),
        ]),
        ("done", [ToolCall(id="t4", name="submit_solution",
                            input={"answer": "ok"})]),
    ]
    llm = ScriptedToolLLM(script)
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    sk = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills.db")
    sem = SemanticMemory(tmp_data_dir / "sem.db")
    wake = WakeAgent(memory=mem, skills=sk, tools=tools, llm=llm)

    result = wake.run("t-parallel", "parallel ops",
                       lambda ans: (ans == "ok", "ok"))
    assert result.success
    eps = mem.all()[0]
    # 3 echos + 1 submit = 4 traces, all with unique step
    steps = [t.step for t in eps.traces]
    assert len(steps) == 4
    assert len(set(steps)) == 4, f"steps must be unique, got {steps}"


def test_native_tool_use_handles_unknown_tool(tmp_data_dir):
    """Model invents a tool name → graceful failure, not crash."""
    tools = {
        "submit_solution": _toolspec(
            "submit_solution",
            lambda answer: ToolResult(ok=True, output=str(answer)),
        ),
    }
    script = [
        ("oops", [ToolCall(id="t1", name="nonexistent", input={"x": "1"})]),
        ("recover", [ToolCall(id="t2", name="submit_solution",
                               input={"answer": "fallback"})]),
    ]
    llm = ScriptedToolLLM(script)
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    sk = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills.db")
    sem = SemanticMemory(tmp_data_dir / "sem.db")
    wake = WakeAgent(memory=mem, skills=sk, tools=tools, llm=llm)

    result = wake.run("t-unk", "x", lambda a: ("fallback" in a, "ok"))
    assert result.success
    eps = mem.all()[0]
    # First trace: failed unknown tool. Second: success submit.
    assert any("unknown tool" in t.observation for t in eps.traces)
