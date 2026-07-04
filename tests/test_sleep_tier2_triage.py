"""The consolidation Tier-2 triage stage: SleepEngine._stage_tier2_triage runs the validated
triage and quarantines coincidental-noise facts via the LLM judge. Hermetic — ENGRAM_DATA_DIR
tmp + a stub LLM returning NOISE (no claude -p). Also asserts the cycle gate is opt-in."""
from __future__ import annotations

import types

import pytest


@pytest.fixture
def _isolated(tmp_path, monkeypatch):
    # Patch the EXISTING (frozen) CONFIG instance in-place + restore — NOT importlib.reload,
    # which swaps the module object and pollutes every other test's CONFIG reference.
    from engram.config import CONFIG
    d = tmp_path / "engram"
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(d))
    orig = {a: getattr(CONFIG, a) for a in ("data_dir", "project_root") if hasattr(CONFIG, a)}
    for a in orig:
        object.__setattr__(CONFIG, a, d)
    try:
        yield
    finally:
        for a, v in orig.items():
            object.__setattr__(CONFIG, a, v)


class _NoiseLLM:
    def complete(self, system, messages, *, model=None, max_tokens=None):
        return types.SimpleNamespace(text="NOISE")


def test_stage_quarantines_noise(_isolated):
    from engram.semantic import Fact, SemanticMemory
    from engram.sleep import SleepEngine, SleepReport

    sm = SemanticMemory()
    sm.store(Fact(proposition="The loop ran 3 steps before exiting.", topic="diary",
                  confidence=0.8), embed="sync")
    sleep = SleepEngine(semantic=sm)
    sleep.llm = _NoiseLLM()  # the judge will say NOISE -> declass

    sleep._stage_tier2_triage(SleepReport())
    assert sm.all()[0].status == "quarantined"


def test_cycle_gate_is_opt_in(_isolated, monkeypatch):
    """evidence_requirement_enabled() OFF (default) -> the stage is not invoked."""
    import engram.evidence_requirement as er
    monkeypatch.delenv("ENGRAM_EVIDENCE_REQUIREMENT", raising=False)
    assert er.evidence_requirement_enabled() is False
    monkeypatch.setenv("ENGRAM_EVIDENCE_REQUIREMENT", "1")
    # reload not needed: the function reads the env at call time
    assert er.evidence_requirement_enabled() is True
