"""Test sleep cycle with mock LLM."""
from __future__ import annotations

import json

from verimem.episode import Episode, Trace
from verimem.llm import MockLLM
from verimem.memory import EpisodicMemory
from verimem.semantic import SemanticMemory
from verimem.skill import Skill, SkillLibrary
from verimem.sleep import SleepEngine, replay_priority


def _ep(task_id, text, outcome="success"):
    return Episode(
        task_id=task_id, task_text=text, outcome=outcome, final_answer="x",
        traces=[Trace(step=1, thought="t", action="a", action_input="{}", observation="o")],
        tokens_used=10,
    )


def test_replay_priority_prefers_failures():
    import time
    now = time.time()
    s = _ep("a", "x", outcome="success")
    f = _ep("b", "y", outcome="failure")
    assert replay_priority(f, now, 1.0) > replay_priority(s, now, 1.0)


# FORGIA pezzo #29 regression: an LLM that emits a non-object JSON like
# `"4"` or `"null"` for a NREM/REM/Schema synthesis prompt used to crash
# downstream `"key" in data` checks with `TypeError: argument of type
# 'int' is not iterable`. _extract_json must filter non-object payloads.

def test_extract_json_rejects_non_object_payloads():
    from verimem.sleep import _extract_json
    # bare int, string, list — all valid JSON but NOT objects
    assert _extract_json("4") is None
    assert _extract_json('"hello"') is None
    assert _extract_json("[1, 2, 3]") is None
    assert _extract_json("null") is None
    assert _extract_json("true") is None
    # legit object still works
    assert _extract_json('{"name": "x"}') == {"name": "x"}
    # Code-fence wrapping still works
    assert _extract_json('```json\n{"name": "y"}\n```') == {"name": "y"}
    # Garbage text still returns None (was None before too)
    assert _extract_json("not json at all") is None


def test_nrem_synthesizes_skill(tmp_data_dir):
    mem = EpisodicMemory(tmp_data_dir / "episodes" / "ep.db")
    sk = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    sem = SemanticMemory(tmp_data_dir / "semantic" / "sem.db")
    # Two similar tasks → one cluster → one synthesized skill
    for i in range(3):
        mem.store(_ep(f"t{i}", "Reverse a string in Python"))
    canned = json.dumps({
        "name": "reverse-via-slicing",
        "trigger": "when reversing a sequence in Python",
        "body": "Use s[::-1] for strings.",
        "rationale": "Slicing is idiomatic and O(n).",
    })
    llm = MockLLM(scripted=[canned])
    engine = SleepEngine(memory=mem, skills=sk, semantic=sem, llm=llm)
    report = engine.cycle()
    assert report.n_nrem_skills >= 1
    found = sk.all()
    assert len(found) >= 1
    assert any("reverse-via-slicing" == s.name for s in found)
    assert any("s[::-1]" in s.body for s in found)


def test_pruning_promotes_high_fitness(tmp_data_dir):
    mem = EpisodicMemory(tmp_data_dir / "episodes" / "ep.db")
    sk = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    sem = SemanticMemory(tmp_data_dir / "semantic" / "sem.db")
    # Need at least sleep_min_episodes to trigger cycle stages
    for i in range(3):
        mem.store(_ep(f"t{i}", f"task {i}"))
    s = Skill(name="x", trigger="x", body="x")
    sk.store(s)
    for _ in range(4):
        sk.update_fitness(s.id, success=True, tokens=50)
    llm = MockLLM(scripted=["{\"name\":\"x\",\"trigger\":\"x\",\"body\":\"x\",\"rationale\":\"x\"}"] * 10)
    engine = SleepEngine(memory=mem, skills=sk, semantic=sem, llm=llm)
    report = engine.cycle()
    assert s.id in report.promoted


# FORGIA pezzo #50: count_llm_calls

def test_sleep_cycle_reports_n_llm_calls(tmp_data_dir):
    """SleepReport.n_llm_calls reports the count for this cycle."""
    from verimem.episode import Episode
    mem = EpisodicMemory(tmp_data_dir / "episodes" / "ep.db")
    sk = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    sem = SemanticMemory(tmp_data_dir / "semantic" / "sem.db")
    # Seed enough episodes for sleep_min_episodes
    for i in range(5):
        mem.store(_ep(f"t{i}", "Reverse a string in Python"))
    canned = json.dumps({
        "name": "reverse-via-slicing",
        "trigger": "when reversing a sequence in Python",
        "body": "Use s[::-1] for strings.",
        "rationale": "concise idiom",
    })
    # MockLLM returns the canned response over and over
    llm = MockLLM(scripted=[canned] * 30)
    eng = SleepEngine(memory=mem, skills=sk, semantic=sem, llm=llm)
    report = eng.cycle()
    # The cycle should have made at least one call (NREM synth)
    assert report.n_llm_calls >= 1
    # And the report's n_llm_calls should match what MockLLM saw
    assert report.n_llm_calls == len(llm.calls)
