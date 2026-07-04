"""Write-path admission threshold: distinct from (and lower than) the answer-path 85,
calibrated on the bimodal fact-vs-source distribution. A fact the source grounds at 50
must be ADMITTED on the write path (it would be wrongly rejected at the answer-path 85)."""
from __future__ import annotations

import types

import pytest

from engram import grounding_gate as G
from engram.anti_confab_gate import run_validation_gate


def test_write_threshold_default_is_calibrated(monkeypatch):
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE_THRESHOLD", raising=False)
    monkeypatch.delenv("ENGRAM_GROUNDING_THRESHOLD", raising=False)
    assert G._resolve_write_threshold() == G.WRITE_DEFAULT_THRESHOLD == 40.0
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
    """The public write-path helper defaults to the write threshold (40), not 85: a fact
    grounded at 50 is STORED (would be rejected at the answer-path 85)."""
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE_THRESHOLD", raising=False)
    monkeypatch.delenv("ENGRAM_GROUNDING_THRESHOLD", raising=False)
    store, score = G.should_store_fact(_StubLLM(50), "src", "fact")
    assert score == 50.0 and store is True
    # explicit threshold still honored
    store2, _ = G.should_store_fact(_StubLLM(50), "src", "fact", threshold=85)
    assert store2 is False


@pytest.mark.parametrize("score,expect_warn", [(50, False), (20, True)])
def test_l4_uses_write_threshold(monkeypatch, score, expect_warn):
    """At the write threshold (40), a 50-grounded fact passes L4 (would fail at 85);
    a 20-grounded fact still warns."""
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
