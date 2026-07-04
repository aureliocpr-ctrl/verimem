"""Test the wake loop with a mock LLM and a known-good submission."""
from __future__ import annotations

from engram.agent import HippoAgent
from engram.llm import MockLLM
from engram.memory import EpisodicMemory
from engram.semantic import SemanticMemory
from engram.skill import SkillLibrary
from engram.sleep import SleepEngine
from engram.wake import WakeAgent, parse_react_step


def test_parse_react_step():
    text = (
        "Thought: I should solve this\n"
        'Action: submit_solution\n'
        'ActionInput: {"answer": "42"}\n'
    )
    out = parse_react_step(text)
    assert out is not None
    thought, action, ai = out
    assert action == "submit_solution"
    assert "42" in ai


def test_wake_loop_submits_with_mock(tmp_data_dir):
    scripted = [
        "Thought: I will answer now\n"
        'Action: submit_solution\n'
        'ActionInput: {"answer": "hello world"}\n'
    ]
    llm = MockLLM(scripted=scripted)
    mem = EpisodicMemory(tmp_data_dir / "episodes" / "ep.db")
    sk = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    sem = SemanticMemory(tmp_data_dir / "semantic" / "sem.db")
    wake = WakeAgent(memory=mem, skills=sk, llm=llm)
    sleep = SleepEngine(memory=mem, skills=sk, semantic=sem, llm=llm)
    agent = HippoAgent(memory=mem, skills=sk, semantic=sem, wake=wake, sleep=sleep)

    def val(ans): return ("hello" in ans, "ok")
    result = agent.run_task("t1", "say hello world", val)
    assert result.success
    assert "hello" in result.episode.final_answer
    assert mem.count() == 1


def test_wake_loop_handles_unknown_tool(tmp_data_dir):
    scripted = [
        "Thought: try unknown\n"
        "Action: nonexistent_tool\n"
        'ActionInput: {"x": 1}\n',
        "Thought: ok give up\n"
        'Action: submit_solution\n'
        'ActionInput: {"answer": "fallback"}\n',
    ]
    llm = MockLLM(scripted=scripted)
    mem = EpisodicMemory(tmp_data_dir / "episodes" / "ep.db")
    sk = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    sem = SemanticMemory(tmp_data_dir / "semantic" / "sem.db")
    wake = WakeAgent(memory=mem, skills=sk, llm=llm)
    sleep = SleepEngine(memory=mem, skills=sk, semantic=sem, llm=llm)
    agent = HippoAgent(memory=mem, skills=sk, semantic=sem, wake=wake, sleep=sleep)

    def val(ans): return ("fallback" in ans, "ok")
    result = agent.run_task("t1", "x", val)
    assert result.success
    assert result.episode.num_steps == 2
