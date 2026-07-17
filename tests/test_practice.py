"""Tests for self-suggested practice prompts (sleep stage 4d).

The dreamer writes practice prompts for skills in the uncertain fitness zone
(0.45–0.65). The user can run them from the dashboard to gather real
fitness signal.
"""
from __future__ import annotations

from dataclasses import dataclass

from verimem.memory import EpisodicMemory
from verimem.semantic import SemanticMemory
from verimem.skill import Skill, SkillLibrary
from verimem.sleep import SleepEngine, SleepReport


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


class _ScriptedLLM:
    def __init__(self, scripts: list[str]) -> None:
        self.scripts = scripts
        self.calls = 0

    def complete(self, system: str, messages, **kwargs) -> _LLMResp:
        idx = min(self.calls, len(self.scripts) - 1)
        self.calls += 1
        return _LLMResp(text=self.scripts[idx])


def _engine(tmp_data_dir, llm) -> tuple[SleepEngine, SkillLibrary]:
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    sem = SemanticMemory(tmp_data_dir / "sem.db")
    return SleepEngine(memory=mem, skills=lib, semantic=sem, llm=llm), lib


PROMPTS_JSON = """{
  "prompts": [
    "Save the text 'hello world' to a file named greeting.txt",
    "Create a backup of /tmp/notes.md to /tmp/notes.bak.md"
  ]
}"""


def test_practice_writes_prompts_for_uncertain_skills(tmp_data_dir):
    """A skill with fitness ≈0.5 (in the uncertain zone) should get
    practice prompts; promoted skills should not."""
    engine, lib = _engine(tmp_data_dir, _ScriptedLLM([PROMPTS_JSON, PROMPTS_JSON]))
    # 4 trials, 2 successes → posterior mean = 3/6 = 0.50 (uncertain)
    uncertain = Skill(name="save text", trigger="when saving text to file",
                       body="x", trials=4, successes=2)
    promoted = Skill(name="great", trigger="x", body="x",
                      trials=10, successes=9, status="promoted")
    lib.store(uncertain)
    lib.store(promoted)

    report = SleepReport()
    engine._stage_practice(report)

    after = lib.get(uncertain.id)
    assert after is not None
    assert len(after.practice_prompts) == 2
    assert "greeting.txt" in after.practice_prompts[0]
    assert report.n_practice_prompts == 2
    # Promoted skill should NOT receive practice prompts
    promoted_after = lib.get(promoted.id)
    assert promoted_after is not None
    assert promoted_after.practice_prompts == []


def test_practice_skips_failing_skills(tmp_data_dir):
    """Failing skills (fitness < min) are handled by counterfactual REM,
    not practice — practice targets the *uncertain middle*."""
    engine, lib = _engine(tmp_data_dir, _ScriptedLLM(["should-not-be-called"]))
    failing = Skill(name="bad", trigger="x", body="x",
                     trials=5, successes=0)  # fitness ~0.14
    lib.store(failing)

    report = SleepReport()
    engine._stage_practice(report)

    after = lib.get(failing.id)
    assert after is not None
    assert after.practice_prompts == []
    assert report.n_practice_prompts == 0
    assert engine.llm.calls == 0


def test_practice_does_not_regenerate_existing_prompts(tmp_data_dir):
    """Once a skill has practice prompts, subsequent sleep cycles should
    leave them alone (idempotent until they're tested and reset)."""
    engine, lib = _engine(tmp_data_dir, _ScriptedLLM(["should-not-be-called"]))
    s = Skill(name="x", trigger="x", body="x",
              trials=4, successes=2,
              practice_prompts=["pre-existing prompt"])
    lib.store(s)

    report = SleepReport()
    engine._stage_practice(report)

    after = lib.get(s.id)
    assert after is not None
    assert after.practice_prompts == ["pre-existing prompt"]
    assert report.n_practice_prompts == 0
    assert engine.llm.calls == 0


def test_practice_handles_invalid_llm_output(tmp_data_dir):
    engine, lib = _engine(tmp_data_dir, _ScriptedLLM(["this is not json at all"]))
    s = Skill(name="x", trigger="x", body="x", trials=4, successes=2)
    lib.store(s)

    report = SleepReport()
    engine._stage_practice(report)

    after = lib.get(s.id)
    assert after is not None
    assert after.practice_prompts == []
    assert report.n_practice_prompts == 0
