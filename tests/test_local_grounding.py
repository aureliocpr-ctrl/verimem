"""TDD for the LOCAL write-gate backend (engram/local_grounding.py) and the
ENGRAM_GROUNDING_BACKEND switch in grounding_gate.

Contract: default backend stays 'claude' (llm injected, behavior unchanged);
ENGRAM_GROUNDING_BACKEND=local routes fact_grounding_score/should_store_fact to a
LocalGroundingJudge (CE model under ~/.engram/models/local_gate_ce or
ENGRAM_LOCAL_GATE_MODEL) WITHOUT touching the llm. The judge is injection-friendly
(scorer callable) so no model download happens in tests. Env thresholds always win
over the model's own gate_config.json."""
from __future__ import annotations

import json

import pytest

from verimem import grounding_gate as G
from verimem.local_grounding import (
    LocalGroundingJudge,
    get_local_threshold,
    reset_local_judge,
    set_local_judge,
)


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    monkeypatch.delenv("ENGRAM_GROUNDING_BACKEND", raising=False)
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE_THRESHOLD", raising=False)
    monkeypatch.delenv("ENGRAM_GROUNDING_THRESHOLD", raising=False)
    monkeypatch.delenv("ENGRAM_LOCAL_GATE_MODEL", raising=False)
    reset_local_judge()
    yield
    reset_local_judge()


class _BoomLLM:
    """An llm that must never be called on the local path."""

    def complete(self, *a, **k):  # noqa: D401
        raise AssertionError("llm.complete called on local backend")


class _StubLLM:
    def __init__(self, text="SCORE: 77"):
        self.text = text

    def complete(self, *a, **k):
        return type("R", (), {"text": self.text})()


def test_local_judge_uses_injected_scorer_and_span_budget():
    seen = []

    def scorer(batch):
        seen.extend(batch)
        return [88.0] * len(batch)

    j = LocalGroundingJudge(scorer=scorer, focus_budget=60)
    long_source = "\n".join(f"line {i} about nothing" for i in range(50)) + "\nthe dog is called Rex"
    score = j.score(long_source, "The dog is called Rex")
    assert score == 88.0
    (span, fact), = seen
    assert fact == "The dog is called Rex"
    assert len(span) <= 60, "focus budget must be applied to the source"
    assert "Rex" in span, "the relevant line must survive span selection"


def test_fact_grounding_score_local_backend_bypasses_llm(monkeypatch):
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "local")
    set_local_judge(LocalGroundingJudge(scorer=lambda b: [61.0] * len(b)))
    s = G.fact_grounding_score(_BoomLLM(), "src text", "a fact")
    assert s == 61.0


def test_fact_grounding_score_default_backend_unchanged():
    s = G.fact_grounding_score(_StubLLM("SCORE: 77"), "src", "fact")
    assert s == 77.0


def test_should_store_fact_local_uses_model_gate_config(tmp_path, monkeypatch):
    (tmp_path / "gate_config.json").write_text(
        json.dumps({"threshold": 55.0, "focus_budget": 1500}), encoding="utf-8")
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(tmp_path))
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "local")
    set_local_judge(LocalGroundingJudge(model_dir=tmp_path,
                                        scorer=lambda b: [60.0] * len(b)))
    ok, score = G.should_store_fact(_BoomLLM(), "src", "fact")
    assert score == 60.0
    assert ok, "60 >= model threshold 55"
    set_local_judge(LocalGroundingJudge(model_dir=tmp_path,
                                        scorer=lambda b: [50.0] * len(b)))
    ok2, score2 = G.should_store_fact(_BoomLLM(), "src", "fact")
    assert (ok2, score2) == (False, 50.0), "50 < model threshold 55"


def test_env_threshold_beats_gate_config(tmp_path, monkeypatch):
    (tmp_path / "gate_config.json").write_text(
        json.dumps({"threshold": 55.0}), encoding="utf-8")
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(tmp_path))
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "local")
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE_THRESHOLD", "70")
    set_local_judge(LocalGroundingJudge(model_dir=tmp_path,
                                        scorer=lambda b: [60.0] * len(b)))
    ok, score = G.should_store_fact(_BoomLLM(), "src", "fact")
    assert (ok, score) == (False, 60.0), "env 70 must beat gate_config 55"


def test_get_local_threshold_reads_config(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(tmp_path))
    assert get_local_threshold() is None
    (tmp_path / "gate_config.json").write_text(
        json.dumps({"threshold": 42.5}), encoding="utf-8")
    reset_local_judge()
    assert get_local_threshold() == 42.5


def test_unknown_backend_falls_back_to_claude(monkeypatch):
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "banana")
    s = G.fact_grounding_score(_StubLLM("SCORE: 33"), "src", "fact")
    assert s == 33.0


def test_local_backend_missing_model_fails_over_to_llm(tmp_path, monkeypatch):
    """Model dir absent/unloadable: the gate must fail over to the injected llm at the
    CLAUDE-scale threshold (70), never raise, and never apply the local config cut to
    a claude-scale score."""
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "local")
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(tmp_path / "nope"))
    s = G.fact_grounding_score(_StubLLM("SCORE: 78"), "src", "fact")
    assert s == 78.0
    ok, score = G.should_store_fact(_StubLLM("SCORE: 78"), "src", "fact")
    assert (ok, score) == (True, 78.0), "78 >= claude write threshold 70"


def test_production_l4_gate_uses_calibrated_local_threshold(tmp_path, monkeypatch):
    """THE critic finding (caller_verification, 2026-07-02): the production write path
    is hippo_remember -> run_validation_gate L4 -> fact_grounding_score — NOT
    should_store_fact. The calibrated cut (gate_config.json) must reach L4: a local
    score of 60 vs config threshold 55 must PASS there, and 50 must WARN — never
    compared against the claude-scale 40."""
    from verimem.anti_confab_gate import run_validation_gate

    (tmp_path / "gate_config.json").write_text(
        json.dumps({"threshold": 55.0}), encoding="utf-8")
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(tmp_path))
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "local")
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")

    def gate_warnings(local_score):
        set_local_judge(LocalGroundingJudge(
            model_dir=tmp_path, scorer=lambda b: [local_score] * len(b)))
        r = run_validation_gate(proposition="a fact", verified_by=None, topic=None,
                                agent=None, source="some source text",
                                grounding_llm=_BoomLLM())
        return [w for w in r.warnings if w.get("layer") == "L4-grounding"], r

    warns, res = gate_warnings(60.0)
    assert warns == [], "60 >= calibrated 55 must pass (claude-scale 40 not involved)"
    assert res.grounding_score == 60.0
    warns, _ = gate_warnings(50.0)
    assert len(warns) == 1, "50 < calibrated 55 must warn at L4"
    # a score in (40, 55) is the regression tell: old code (fixed cut 40) passed it
    warns, _ = gate_warnings(47.0)
    assert len(warns) == 1, "47 must be rejected at the calibrated cut, not pass at 40"


def test_local_without_gate_config_warns_and_uses_default(tmp_path, monkeypatch):
    """Counterexample worker: local model loads but ships NO gate_config threshold and
    no env override — the gate must warn (uncalibrated) and fall to the default 70,
    visibly rather than silently."""
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(tmp_path))  # no gate_config.json
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "local")
    set_local_judge(LocalGroundingJudge(model_dir=tmp_path,
                                        scorer=lambda b: [75.0] * len(b)))
    with pytest.warns(RuntimeWarning, match="uncalibrated"):
        ok, score = G.should_store_fact(_BoomLLM(), "src", "fact")
    assert (ok, score) == (True, 75.0), "75 >= default 70"


def test_failover_uses_claude_scale_threshold_not_config(tmp_path, monkeypatch):
    """Symmetric hazard: the model dir carries a gate_config threshold 91 but NO model
    weights (load fails, fail-over to llm) — the claude-scale score (78) must be cut
    at 70, not at the CE-scale 91 (which would silently over-reject)."""
    (tmp_path / "gate_config.json").write_text(
        json.dumps({"threshold": 91.0}), encoding="utf-8")
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(tmp_path))  # config yes, model no
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "local")
    ok, score = G.should_store_fact(_StubLLM("SCORE: 78"), "src", "fact")
    assert (ok, score) == (True, 78.0), "fail-over must cut at claude-scale 70 (78<91: config not applied)"


def test_local_load_failure_is_cached_not_retried(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "local")
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(tmp_path / "nope"))
    from verimem import local_grounding as LG
    calls = {"n": 0}

    def boom_loader(*a, **k):
        calls["n"] += 1
        raise OSError("no model")

    monkeypatch.setattr(LG, "make_finetuned_scorer", boom_loader)
    for _ in range(3):
        assert LG.try_local_score("src", "fact") is None
    assert calls["n"] == 1, "load failure must be cached, not retried per call"
