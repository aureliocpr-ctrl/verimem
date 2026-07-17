"""Integration test: a full sleep cycle that exercises all five
active-memory mechanisms in one pass.

Stages we expect to fire (with fixtures designed to satisfy each gate):
  1. NREM consolidation       — clustered episodes → at least one new skill
  2. REM recombination        — promoted-skill pool ≥2 → hybrid attempt
  3. Curator de-duplication   — at least one near-duplicate pair → merge
  4. Procedural compilation   — skill with N successes → macro distilled
  5. Counterfactual REM       — failing skill with N trials → alternative
  6. Schema formation         — cluster ≥3 of related skills → meta-skill
  7. Pruning                  — promote_or_retire over fitness thresholds

A scripted multi-response LLM is used so we don't hit the network and the
test is deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass

from verimem.config import CONFIG
from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory
from verimem.semantic import SemanticMemory
from verimem.skill import Skill, SkillLibrary
from verimem.sleep import SleepEngine


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


class _MultiStageLLM:
    """Cycles through different responses based on call count.

    Order matches the sleep stages: NREM, REM, Curator, Compilation,
    Counterfactual, Schema. We return a response that's syntactically
    valid for *any* of those stages so they all do something.
    """
    GENERIC_SKILL = """{
  "name": "synthetic skill",
  "trigger": "when handling synthetic test inputs",
  "body": "do the right thing",
  "rationale": "ad-hoc test heuristic"
}"""
    # Counterfactual must yield a NAME+TRIGGER that does NOT collide with the
    # generic synthesis above, otherwise the new pre-store dedup will (rightly)
    # filter it out as a duplicate of the just-created NREM skill.
    COUNTERFACTUAL_SKILL = """{
  "name": "counterfactual alternative",
  "trigger": "when prior approach Y failed because it skipped Z",
  "body": "first analyse Z then apply a refined heuristic",
  "rationale": "the failed trajectory ignored Z"
}"""
    MACRO = """{
  "steps": [
    {"tool": "submit_solution", "args": {"answer": "ok"}}
  ],
  "confidence": 0.9,
  "rationale": "single-step pattern"
}"""

    def __init__(self) -> None:
        self.calls = 0
        self.responses: list[str] = []

    def complete(self, system: str, messages, **_) -> _LLMResp:
        self.calls += 1
        # Stage detection by system-prompt fingerprint
        if "COMPILER" in system:
            return _LLMResp(text=self.MACRO)
        if "COUNTERFACTUAL" in system:
            return _LLMResp(text=self.COUNTERFACTUAL_SKILL)
        if "REJECT" in system:  # SCHEMA_SYSTEM mentions REJECT in its rules
            return _LLMResp(text=self.GENERIC_SKILL)
        return _LLMResp(text=self.GENERIC_SKILL)


def _success_episode(skill_id: str, task: str, n_traces: int = 1) -> Episode:
    ep = Episode(task_id="t", task_text=task, outcome="success",
                  final_answer="ok", skills_used=[skill_id])
    for i in range(1, n_traces + 1):
        ep.traces.append(Trace(step=i, thought="t",
                                action="submit_solution",
                                action_input='{"answer": "ok"}',
                                observation="ok"))
    return ep


def _failure_episode(skill_id: str) -> Episode:
    ep = Episode(task_id="t", task_text="task that fails", outcome="failure",
                  final_answer="", skills_used=[skill_id], critique="missed Z")
    ep.traces.append(Trace(step=1, thought="t", action="run_python",
                            action_input='{"code": "x"}', observation="error"))
    return ep


def test_full_sleep_cycle_runs_all_stages(tmp_data_dir):
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    sem = SemanticMemory(tmp_data_dir / "sem.db")

    # Skill A: high-fitness, lots of successes → compilation candidate
    skill_a = Skill(
        name="echo phrase",
        trigger="echo a phrase back to the user verbatim",
        body="just submit", trials=10, successes=10, status="promoted",
    )
    # Skill B: also fs-flavoured for clustering
    skill_b = Skill(
        name="open file",
        trigger="open a file from disk to inspect its contents",
        body="x", trials=4, successes=3, status="promoted",
    )
    # Skill C: similar trigger to B → near-duplicate (Curator)
    skill_c = Skill(
        name="open file 2",
        trigger="open a file from disk to inspect its contents",
        body="y", trials=3, successes=2, status="candidate",
    )
    # Skill D: also fs-themed for schema formation
    skill_d = Skill(
        name="read file",
        trigger="read a file from disk to retrieve its contents",
        body="x", trials=3, successes=2, status="promoted",
    )
    # Skill E: fs again
    skill_e = Skill(
        name="write file",
        trigger="write a file to disk to persist its contents",
        body="x", trials=3, successes=2, status="promoted",
    )
    # Skill F: failing (counterfactual target)
    skill_f = Skill(
        name="bad approach", trigger="when X", body="do Y",
        trials=3, successes=0,
    )

    for s in (skill_a, skill_b, skill_c, skill_d, skill_e, skill_f):
        lib.store(s)

    # Episodes — enough successful runs of skill_a for compilation,
    # plus one failure of skill_f, plus a couple of generic episodes for NREM.
    for i in range(6):
        mem.store(_success_episode(skill_a.id, f"echo phrase iteration {i}"))
    for _ in range(3):
        mem.store(_failure_episode(skill_f.id))

    llm = _MultiStageLLM()
    engine = SleepEngine(memory=mem, skills=lib, semantic=sem, llm=llm)

    # Lower the schema threshold so the test is robust to embedding noise
    original_threshold = CONFIG.schema_cluster_threshold
    object.__setattr__(CONFIG, "schema_cluster_threshold", 0.40)
    try:
        report = engine.cycle()
    finally:
        object.__setattr__(CONFIG, "schema_cluster_threshold", original_threshold)

    # The cycle ran without error — primary success criterion
    assert report.duration_s > 0
    # Compilation: skill_a should now have a compiled macro
    a_after = lib.get(skill_a.id)
    assert a_after is not None
    assert a_after.compiled_macro is not None, "skill_a should have a compiled macro"
    macro_steps = a_after.compiled_macro.get("steps") or []
    assert len(macro_steps) == 1
    # Counterfactual: at least one skill marked is_counterfactual
    cfs = [s for s in lib.all() if s.is_counterfactual]
    assert cfs, "expected at least one counterfactual skill"
    # Schema: at least one schema-stage skill
    schemas = [s for s in lib.all() if s.stage == "schema"]
    assert schemas, "expected at least one schema-stage skill"
    # Pruning: skill_f (3 trials, 0 successes, fitness ≈ 0.20) should retire
    f_after = lib.get(skill_f.id)
    assert f_after is not None
    assert f_after.status == "retired"
