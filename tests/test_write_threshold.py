"""Write-path admission threshold: distinct from (and lower than) the answer-path 85.

RECALIBRATED 40 -> 70 (2026-07-17) on three independent measurements: the judge's own
rubric (_FACT_SYSTEM: 1-60 = "only related/partial" -> not entailed), the real-corpus
n=90 curve (block 0.70 -> 0.93 for -1.7pt admit), and external held-out corpora
(HaluEval block 0.45 -> 0.68 for -1.7pt admit; TruthfulQA block 0.97 -> 0.98). The
realistic e2e cases separate 0/100 and are unaffected. A fact the judge scores 50
("partial") is now correctly QUARANTINED; 75+ ("entailed") is admitted."""
from __future__ import annotations

import types

import pytest

from engram import grounding_gate as G
from engram.anti_confab_gate import run_validation_gate


def test_write_threshold_default_is_calibrated(monkeypatch):
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE_THRESHOLD", raising=False)
    monkeypatch.delenv("ENGRAM_GROUNDING_THRESHOLD", raising=False)
    assert G._resolve_write_threshold() == G.WRITE_DEFAULT_THRESHOLD == 70.0
    # answer-path default is unchanged (still 85)
    assert G._resolve_threshold(None) == 85.0


def test_write_threshold_env_override(monkeypatch):
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE_THRESHOLD", "55")
    assert G._resolve_write_threshold() == 55.0


def test_write_threshold_falls_back_to_general(monkeypatch):
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE_THRESHOLD", raising=False)
    monkeypatch.setenv("ENGRAM_GROUNDING_THRESHOLD", "30")
    assert G._resolve_write_threshold() == 30.0


class _StubLLM:
    def __init__(self, score):
        self._score = score

    def complete(self, system, messages, *, model=None, max_tokens=None):
        return types.SimpleNamespace(text=f"SCORE: {self._score}")


def test_fact_grounding_score_system_override():
    """fact_grounding_score honors a custom judge prompt (for A/B calibration) and falls
    back to the default _FACT_SYSTEM otherwise."""
    seen = {}

    class _Cap:
        def complete(self, system, messages, *, model=None, max_tokens=None):
            seen["system"] = system
            return types.SimpleNamespace(text="SCORE: 77")

    custom = "CUSTOM JUDGE PROMPT for A/B. Reply 'SCORE: N'."
    G.fact_grounding_score(_Cap(), "src", "fact", system=custom)
    assert seen["system"] is custom
    G.fact_grounding_score(_Cap(), "src", "fact")
    assert seen["system"] is G._FACT_SYSTEM  # default fallback


def test_should_store_fact_uses_write_default(monkeypatch):
    """The public write-path helper defaults to the write threshold (70), not 85: a fact
    the judge calls entailed (75) is STORED; one the judge calls only partial (50) is
    NOT (rubric: 1-60 = related/partial)."""
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE_THRESHOLD", raising=False)
    monkeypatch.delenv("ENGRAM_GROUNDING_THRESHOLD", raising=False)
    store, score = G.should_store_fact(_StubLLM(75), "src", "fact")
    assert score == 75.0 and store is True
    store_partial, _ = G.should_store_fact(_StubLLM(50), "src", "fact")
    assert store_partial is False   # partial support no longer admits
    # explicit threshold still honored
    store2, _ = G.should_store_fact(_StubLLM(75), "src", "fact", threshold=85)
    assert store2 is False


@pytest.mark.parametrize("score,expect_warn", [(75, False), (50, True), (20, True)])
def test_l4_uses_write_threshold(monkeypatch, score, expect_warn):
    """At the write threshold (70), a 75-grounded fact passes L4; a 50-grounded fact
    (judge rubric: 'only related/partial') now warns, as does a 20-grounded one."""
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE_THRESHOLD", raising=False)
    monkeypatch.delenv("ENGRAM_GROUNDING_THRESHOLD", raising=False)
    res = run_validation_gate(
        proposition="The deployment uses PostgreSQL 16.", verified_by=None,
        topic="infra", agent=None, validate="fast",
        source="We moved the deployment to PostgreSQL 16 last week.",
        grounding_llm=_StubLLM(score),
    )
    assert res.grounding_score == float(score)
    l4 = [w for w in res.warnings if isinstance(w, dict) and w.get("layer") == "L4-grounding"]
    assert bool(l4) == expect_warn
