"""CYCLE #12 — SleepEngine.cycle_light: promote+retire pass senza LLM.

Bug originale: il metodo NON ESISTEVA, mcp_server.py:_consolidate_light
chiamava `a.sleep.cycle_light()` → AttributeError → fallback con
threshold hardcoded (0.7/0.2/min5) NON allineati a CONFIG (0.6/0.25/3).
Effetto live: 1 candidate t=3 s=3 fit=0.80 (eligible su CONFIG) restava
candidate perché bloccata da min_trials=5 hardcoded.
"""
from __future__ import annotations

import pytest

from engram.memory import EpisodicMemory
from engram.semantic import SemanticMemory
from engram.skill import Skill, SkillLibrary
from engram.sleep import SleepEngine


@pytest.fixture
def engine(tmp_path, monkeypatch):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    sk = SkillLibrary(
        dir_path=tmp_path / "skills",
        db_path=tmp_path / "skills.db",
    )
    sem = SemanticMemory(db_path=tmp_path / "sem.db")

    class _NullLLM:
        def supports_tools(self): return False

        def complete(self, *a, **kw): return ""

    monkeypatch.setattr("engram.sleep.get_llm", lambda: _NullLLM())
    return SleepEngine(memory=mem, skills=sk, semantic=sem)


def _candidate(sid: str, *, trials: int, successes: int) -> Skill:
    return Skill(
        id=sid, name=f"sk-{sid}", trigger=f"trig-{sid}", body="b",
        status="candidate", trials=trials, successes=successes,
    )


def test_cycle_light_method_exists(engine):
    assert hasattr(engine, "cycle_light")
    assert callable(engine.cycle_light)


def test_cycle_light_returns_sleep_report(engine):
    report = engine.cycle_light()
    assert hasattr(report, "promoted")
    assert hasattr(report, "retired")
    assert hasattr(report, "duration_s")
    assert hasattr(report, "n_episodes_replayed")
    assert report.n_episodes_replayed == 0  # light cycle non itera episodi


def test_cycle_light_promotes_eligible_candidate(engine):
    """trials >= min_trials AND fitness >= promote_threshold → promoted."""
    # CONFIG: min_trials=3, promote_threshold=0.6
    # t=3 s=3 fitness_mean = (1+3)/(2+3) = 0.80 ≥ 0.6 → PROMOTE
    sk = _candidate("good", trials=3, successes=3)
    engine.skills.store(sk)
    report = engine.cycle_light()
    assert "good" in report.promoted
    refreshed = engine.skills.get("good")
    assert refreshed.status == "promoted"


def test_cycle_light_retires_failing_candidate(engine):
    """fitness < retire_threshold → retired."""
    # CONFIG: retire_threshold=0.25, min_trials=3
    # t=6 s=0 fitness_mean = 1/8 = 0.125 < 0.25 → RETIRE
    sk = _candidate("bad", trials=6, successes=0)
    engine.skills.store(sk)
    report = engine.cycle_light()
    assert "bad" in report.retired
    refreshed = engine.skills.get("bad")
    assert refreshed.status == "retired"


def test_cycle_light_skips_below_min_trials(engine):
    """trials < min_trials → no action."""
    # t=2 s=2 fitness=0.75 ma trials < 3 → skip
    sk = _candidate("young", trials=2, successes=2)
    engine.skills.store(sk)
    report = engine.cycle_light()
    assert "young" not in report.promoted
    assert "young" not in report.retired
    assert engine.skills.get("young").status == "candidate"


def test_cycle_light_no_llm_call(engine, monkeypatch):
    """Light cycle deve essere COMPLETAMENTE LLM-free (safe in hosted mode)."""
    call_count = {"n": 0}

    def _spy(*a, **kw):
        call_count["n"] += 1
        return ""

    monkeypatch.setattr(engine.llm, "complete", _spy, raising=False)
    engine.skills.store(_candidate("x", trials=3, successes=3))
    engine.skills.store(_candidate("y", trials=6, successes=0))
    engine.cycle_light()
    assert call_count["n"] == 0


def test_cycle_light_empty_corpus(engine):
    """Corpus vuoto → report con liste vuote, no crash."""
    report = engine.cycle_light()
    assert report.promoted == []
    assert report.retired == []
    assert report.duration_s >= 0.0
