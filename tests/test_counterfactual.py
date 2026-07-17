"""Tests for counterfactual REM.

When a skill consistently fails (fitness < threshold, trials ≥ N), the dreamer
generates 1-2 alternative strategies that would plausibly have worked. These
are stored as candidate skills with the failing skill as parent.
"""
from __future__ import annotations

from dataclasses import dataclass

from verimem.episode import Episode, Trace
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
    """Returns each script entry in turn; cycles to last on overflow."""
    def __init__(self, scripts: list[str]) -> None:
        self.scripts = scripts
        self.calls = 0

    def complete(self, system, messages, **kwargs) -> _LLMResp:
        idx = min(self.calls, len(self.scripts) - 1)
        self.calls += 1
        return _LLMResp(text=self.scripts[idx])


def _failing_skill() -> Skill:
    # 3 trials, 0 successes → fitness ≈ 0.20
    return Skill(name="bad approach", trigger="when X",
                 body="do Y", trials=3, successes=0)


def _failure_episode(skill_id: str) -> Episode:
    ep = Episode(task_id="t", task_text="task that requires X", outcome="failure",
                  final_answer="", skills_used=[skill_id],
                  critique="approach Y did not consider Z")
    ep.traces.append(Trace(step=1, thought="will do Y", action="run_python",
                            action_input="{}", observation="error"))
    return ep


def test_counterfactual_creates_alternative_skill(tmp_data_dir):
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    sem = SemanticMemory(tmp_data_dir / "sem.db")

    failed = _failing_skill()
    lib.store(failed)
    mem.store(_failure_episode(failed.id))
    # Add 2 more episodes to satisfy sleep_min_episodes (config default = 2)
    mem.store(_failure_episode(failed.id))
    mem.store(_failure_episode(failed.id))

    alternative = """{
  "name": "use Z first",
  "trigger": "when X (alternative)",
  "body": "first analyse Z, then approach Y",
  "rationale": "the prior failure missed Z"
}"""
    # Multiple LLM stages may run during the cycle; return alt_json for all
    llm = _ScriptedLLM([alternative])

    engine = SleepEngine(memory=mem, skills=lib, semantic=sem, llm=llm)
    report = SleepReport()
    engine._stage_counterfactual(report)

    assert report.n_counterfactuals == 1, f"expected 1 cf skill, got {report.n_counterfactuals}"
    new_skills = [s for s in lib.all() if s.is_counterfactual]
    assert len(new_skills) == 1
    cf = new_skills[0]
    assert cf.parent_skills == [failed.id]
    assert cf.stage == "rem"
    assert cf.status == "candidate"
    assert "Z" in cf.body


def test_counterfactual_skips_high_fitness_skills(tmp_data_dir):
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    sem = SemanticMemory(tmp_data_dir / "sem.db")
    good = Skill(name="good", trigger="x", body="x", trials=10, successes=9)
    lib.store(good)
    mem.store(_failure_episode(good.id))

    llm = _ScriptedLLM(["should-not-be-called"])
    engine = SleepEngine(memory=mem, skills=lib, semantic=sem, llm=llm)
    report = SleepReport()
    engine._stage_counterfactual(report)
    assert report.n_counterfactuals == 0
    assert llm.calls == 0


def test_counterfactual_skips_when_few_trials(tmp_data_dir):
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    sem = SemanticMemory(tmp_data_dir / "sem.db")
    s = Skill(name="unproven", trigger="x", body="x", trials=1, successes=0)
    lib.store(s)
    mem.store(_failure_episode(s.id))

    llm = _ScriptedLLM(["should-not-be-called"])
    engine = SleepEngine(memory=mem, skills=lib, semantic=sem, llm=llm)
    report = SleepReport()
    engine._stage_counterfactual(report)
    assert report.n_counterfactuals == 0
    assert llm.calls == 0


def test_counterfactual_skill_does_not_recurse(tmp_data_dir):
    """A counterfactual skill that itself fails should NOT spawn another counterfactual."""
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    sem = SemanticMemory(tmp_data_dir / "sem.db")
    cf = Skill(name="cf", trigger="x", body="x",
               trials=3, successes=0, is_counterfactual=True)
    lib.store(cf)
    mem.store(_failure_episode(cf.id))

    llm = _ScriptedLLM(["should-not-be-called"])
    engine = SleepEngine(memory=mem, skills=lib, semantic=sem, llm=llm)
    report = SleepReport()
    engine._stage_counterfactual(report)
    assert report.n_counterfactuals == 0
    assert llm.calls == 0
