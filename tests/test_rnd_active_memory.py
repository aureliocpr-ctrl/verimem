"""Property tests for the R&D upgrades to the 6 active-memory mechanisms.

One ≥1 test per upgrade — see RND_MEMORIE.md for the rationale.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from engram.compilation import CompiledMacro, MacroStep
from engram.config import CONFIG
from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory
from engram.semantic import SemanticMemory
from engram.skill import Skill, SkillLibrary
from engram.sleep import SleepEngine, SleepReport
from engram.wake import WakeAgent, WakeConfig


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


# --- Fix #1: adaptive macro fast-path threshold ---------------------------


def test_adaptive_macro_threshold_lowers_with_high_confidence(tmp_data_dir):
    """A macro with high LLM-rated confidence is allowed to fire on tasks
    that are slightly less similar than the static threshold would allow."""
    from engram.tools import default_tools

    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    agent = WakeAgent(memory=mem, skills=lib,
                      tools=default_tools(),
                      llm=_ScriptedLLM([""]),
                      config=WakeConfig())

    base = CONFIG.compile_apply_min_similarity
    floor = CONFIG.compile_apply_floor_similarity

    # Confidence 0.5 → no adjustment, threshold == base
    assert agent._adaptive_macro_threshold(0.5) == base
    # Confidence 1.0 → drop by k * 0.5 = 0.15 by default
    high = agent._adaptive_macro_threshold(1.0)
    assert high < base
    # Hard floor never violated even at confidence 1.0
    assert high >= floor


def test_adaptive_threshold_disabled_returns_base(tmp_data_dir):
    from engram.tools import default_tools
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    agent = WakeAgent(memory=mem, skills=lib,
                      tools=default_tools(),
                      llm=_ScriptedLLM([""]),
                      config=WakeConfig())
    original = CONFIG.compile_adaptive_enabled
    object.__setattr__(CONFIG, "compile_adaptive_enabled", False)
    try:
        assert agent._adaptive_macro_threshold(0.99) == CONFIG.compile_apply_min_similarity
    finally:
        object.__setattr__(CONFIG, "compile_adaptive_enabled", original)


# --- Fix #2: forward replay with edge-case (failure) traces ---------------


def test_forward_replay_includes_avoid_path_for_recent_failure(tmp_data_dir):
    """When the recall returns a similar failed episode for the same skill,
    the AVOID path block surfaces in the forward-replay output."""
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    s = Skill(name="solve", trigger="solve numerical task",
              body="x", trials=10, successes=8, status="promoted")
    lib.store(s)

    success_ep = Episode(task_id="t", task_text="solve x", outcome="success",
                          final_answer="ok", skills_used=[s.id])
    success_ep.traces.append(Trace(step=1, thought="t", action="run_python",
                                    action_input="{}", observation="ok"))
    success_ep.traces.append(Trace(step=2, thought="t", action="submit_solution",
                                    action_input="{}", observation="ok"))
    fail_ep = Episode(task_id="t2", task_text="solve x", outcome="failure",
                       final_answer="", skills_used=[s.id],
                       critique="forgot to escape backslashes")
    fail_ep.traces.append(Trace(step=1, thought="t", action="run_python",
                                 action_input="{}", observation="ERROR"))
    mem.store(success_ep); mem.store(fail_ep)

    agent = WakeAgent(memory=mem, skills=lib, llm=_ScriptedLLM([""]),
                      config=WakeConfig())
    block = agent._forward_replay_block(
        task="solve x",
        skills=[s],
        episodes=[(success_ep, 0.95), (fail_ep, 0.92)],
    )
    assert "PREDICTED PATH" in block
    assert "Avoid path" in block
    assert "run_python" in block  # the failure prefix
    assert "Lesson:" in block
    assert "escape backslashes" in block


def test_forward_replay_no_avoid_path_when_no_failures(tmp_data_dir):
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    s = Skill(name="solve", trigger="solve task", body="x",
              trials=10, successes=9, status="promoted")
    lib.store(s)
    succ = Episode(task_id="t", task_text="x", outcome="success",
                    final_answer="ok", skills_used=[s.id])
    succ.traces.append(Trace(step=1, thought="t", action="submit_solution",
                              action_input="{}", observation="ok"))
    mem.store(succ)
    agent = WakeAgent(memory=mem, skills=lib, llm=_ScriptedLLM([""]),
                      config=WakeConfig())
    block = agent._forward_replay_block("x", [s], [(succ, 0.95)])
    assert "Avoid path" not in block


# --- Fix #3: Hebbian temporal decay ---------------------------------------


def test_decay_pulls_idle_skill_back_toward_canonical(tmp_data_dir):
    """A skill with a learned_embedding far from canonical, idle for >cutoff,
    should drift back when decay_idle_embeddings runs."""
    from engram import embedding as emb_mod

    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    s = Skill(name="solve quadratic", trigger="solving quadratic equations",
              body="x")
    # Seed with a strongly-drifted learned_embedding (encode an unrelated
    # task to simulate Hebbian lock-in to the wrong topic).
    s.learned_embedding = emb_mod.encode(
        "an entirely unrelated piece of text about gardening tomatoes"
    ).tolist()
    s.last_used_at = time.time() - (CONFIG.hebbian_decay_after_s + 100.0)
    lib.store(s)

    canonical = emb_mod.encode(f"{s.name}\n{s.trigger}")
    before_emb = np.asarray(s.learned_embedding, dtype=np.float32)
    sim_before = float(np.dot(before_emb, canonical))

    n = lib.decay_idle_embeddings()
    assert n == 1

    after = lib.get(s.id)
    assert after is not None
    if after.learned_embedding is None:
        # Decayed all the way to canonical → drop fallback path
        sim_after = 1.0
    else:
        after_emb = np.asarray(after.learned_embedding, dtype=np.float32)
        sim_after = float(np.dot(after_emb, canonical))
    # Decayed embedding must be CLOSER to canonical than before
    assert sim_after > sim_before


def test_decay_skips_recently_used_skills(tmp_data_dir):
    from engram import embedding as emb_mod
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    s = Skill(name="x", trigger="x", body="x")
    s.learned_embedding = emb_mod.encode("an unrelated text").tolist()
    s.last_used_at = time.time()  # used right now
    lib.store(s)
    before = list(s.learned_embedding)
    n = lib.decay_idle_embeddings()
    assert n == 0
    after = lib.get(s.id)
    assert after.learned_embedding == before


def test_decay_disabled_is_noop(tmp_data_dir):
    from engram import embedding as emb_mod
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    s = Skill(name="x", trigger="x", body="x")
    s.learned_embedding = emb_mod.encode("unrelated").tolist()
    s.last_used_at = time.time() - (CONFIG.hebbian_decay_after_s + 100.0)
    lib.store(s)
    original = CONFIG.hebbian_decay_enabled
    object.__setattr__(CONFIG, "hebbian_decay_enabled", False)
    try:
        n = lib.decay_idle_embeddings()
    finally:
        object.__setattr__(CONFIG, "hebbian_decay_enabled", original)
    assert n == 0


# --- Fix #4: counterfactual dedup ----------------------------------------


def test_counterfactual_skipped_when_alt_duplicates_existing_skill(tmp_data_dir):
    """A counterfactual whose name+trigger collides with an existing skill
    must be filtered before storage."""
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    sem = SemanticMemory(tmp_data_dir / "sem.db")

    failed = Skill(name="bad", trigger="when X", body="do Y",
                    trials=3, successes=0)
    duplicate = Skill(name="use Z first", trigger="when X with refined Z",
                      body="x", trials=0, successes=0)
    lib.store(failed); lib.store(duplicate)

    fail_ep = Episode(task_id="t", task_text="x", outcome="failure",
                       final_answer="", skills_used=[failed.id])
    fail_ep.traces.append(Trace(step=1, thought="t", action="run_python",
                                 action_input="{}", observation="err"))
    mem.store(fail_ep); mem.store(fail_ep); mem.store(fail_ep)

    duplicate_alt = """{
  "name": "use Z first",
  "trigger": "when X with refined Z",
  "body": "first analyse Z then proceed",
  "rationale": "the prior failure missed Z"
}"""
    engine = SleepEngine(memory=mem, skills=lib, semantic=sem,
                         llm=_ScriptedLLM([duplicate_alt]))
    report = SleepReport()
    engine._stage_counterfactual(report)
    assert report.n_counterfactuals == 0


# --- Fix #5: schema skip-if-covered ---------------------------------------


def test_schema_skips_cluster_already_covered_by_existing_schema(tmp_data_dir):
    """When a schema already specialises the same set of skills, the stage
    should NOT call the LLM again."""
    schema_json = """{
  "name": "Filesystem ops",
  "trigger": "any disk operation",
  "body": "use the right child",
  "rationale": "shared domain"
}"""
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    sem = SemanticMemory(tmp_data_dir / "sem.db")
    a = Skill(name="read file",
              trigger="read a file from disk to retrieve its contents", body="x")
    b = Skill(name="write file",
              trigger="write a file to disk to persist its contents", body="x")
    c = Skill(name="open file",
              trigger="open a file from disk to inspect its contents", body="x")
    for s in (a, b, c):
        lib.store(s)
    # Pre-existing schema covering exactly the cluster
    schema = Skill(name="prev schema", trigger="x", body="x", stage="schema",
                   status="candidate")
    lib.store(schema)
    lib.add_lineage_edge(schema.id, a.id, "specialises")
    lib.add_lineage_edge(schema.id, b.id, "specialises")
    lib.add_lineage_edge(schema.id, c.id, "specialises")

    llm = _ScriptedLLM([schema_json])
    engine = SleepEngine(memory=mem, skills=lib, semantic=sem, llm=llm)
    original = CONFIG.schema_cluster_threshold
    object.__setattr__(CONFIG, "schema_cluster_threshold", 0.40)
    try:
        report = SleepReport()
        engine._stage_schema(report)
    finally:
        object.__setattr__(CONFIG, "schema_cluster_threshold", original)
    # Cluster covered → no new schema, no LLM call
    assert report.n_schemas == 0
    assert llm.calls == 0


# --- Fix #6: practice prioritisation by fitness variance ------------------


def test_fitness_variance_higher_for_smaller_n(tmp_data_dir):
    """Two skills with the SAME posterior mean but different N should yield
    different variance; the smaller-N skill wins the practice slot."""
    small_n = Skill(name="small", trigger="small", body="x",
                     trials=4, successes=2)  # mean ≈ 0.50
    big_n = Skill(name="big", trigger="big", body="x",
                   trials=20, successes=10)  # mean ≈ 0.50
    assert abs(small_n.fitness_mean - big_n.fitness_mean) < 0.01
    assert small_n.fitness_variance > big_n.fitness_variance


def test_practice_prioritises_high_variance_skill(tmp_data_dir):
    """When budget = 1, the skill with higher posterior variance gets the
    practice prompt — not the one with mean closer to 0.5."""
    PROMPTS_JSON = """{"prompts": ["practice the operation on case A"]}"""
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    sem = SemanticMemory(tmp_data_dir / "sem.db")

    # Both skills are inside the practice fitness window (0.45–0.65 by default)
    high_var = Skill(name="hv", trigger="hv", body="x", trials=4, successes=2)  # mean 0.50, var ~0.045
    low_var = Skill(name="lv", trigger="lv", body="x", trials=20, successes=10)  # mean 0.50, var ~0.011
    lib.store(high_var); lib.store(low_var)

    engine = SleepEngine(memory=mem, skills=lib, semantic=sem,
                         llm=_ScriptedLLM([PROMPTS_JSON]))
    original = CONFIG.practice_max_skills_per_cycle
    object.__setattr__(CONFIG, "practice_max_skills_per_cycle", 1)
    try:
        report = SleepReport()
        engine._stage_practice(report)
    finally:
        object.__setattr__(CONFIG, "practice_max_skills_per_cycle", original)
    after_hv = lib.get(high_var.id)
    after_lv = lib.get(low_var.id)
    assert after_hv is not None and after_lv is not None
    assert after_hv.practice_prompts, "high-variance skill should get practice"
    assert after_lv.practice_prompts == [], "low-variance skill should NOT"


# --- Fix #7: working memory pruning --------------------------------------


def test_working_memory_pruning_compresses_old_observations(tmp_data_dir):
    """When the running message list exceeds the budget, mid-trajectory
    tool_result messages should be replaced by the placeholder."""
    from engram.tools import default_tools
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    agent = WakeAgent(memory=mem, skills=lib,
                      tools=default_tools(),
                      llm=_ScriptedLLM([""]),
                      config=WakeConfig())
    placeholder = CONFIG.working_memory_pruned_placeholder
    huge = "X" * 50_000
    messages = [
        {"role": "user", "content": "the original task"},
        # Anthropic-style tool_result blocks
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "1", "content": huge}
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "2", "content": huge}
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "3", "content": huge}
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "4", "content": "small recent"}
        ]},
    ]
    pruned = agent._prune_working_memory(messages)
    # The very first message (user task) is preserved verbatim
    assert pruned[0]["content"] == "the original task"
    # The last `keep_tail` tool_result is preserved
    assert pruned[-1]["content"][0]["content"] == "small recent"
    # At least one mid-trajectory observation was replaced
    assert any(
        isinstance(m.get("content"), list)
        and any(b.get("content") == placeholder
                for b in m["content"] if isinstance(b, dict))
        for m in pruned[1:-1]
    )


def test_working_memory_pruning_under_budget_is_noop(tmp_data_dir):
    """Sotto budget, _prune_working_memory NON modifica i messaggi (no-op REALE
    e falsificabile). NB (AUDIT 2026-06-02): il flag
    CONFIG.working_memory_pruning_enabled gat-a la CHIAMATA a prune nel wake loop
    (wake.py:1399), NON la funzione -> il no-op-da-flag e' proprieta' del loop
    (coperta li'); QUI testiamo il no-op-da-budget della funzione. Prima il test
    chiamava la funzione con un messaggio ENORME (over-budget!) e asseriva solo
    isinstance(out, list) = tautologico, non verificava alcun no-op."""
    from engram.tools import default_tools
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    agent = WakeAgent(memory=mem, skills=lib,
                      tools=default_tools(),
                      llm=_ScriptedLLM([""]),
                      config=WakeConfig())
    # Messaggi piccoli, BEN sotto il budget -> nessuna potatura attesa.
    small = [
        {"role": "user", "content": "the original task"},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "1", "content": "short observation"}
        ]},
    ]
    out = agent._prune_working_memory([dict(m) for m in small])
    assert out == small, (
        "sotto budget il pruning deve essere un no-op: nessuna mutazione "
        f"dei messaggi. got={out}")
