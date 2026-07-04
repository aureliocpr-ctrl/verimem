"""S1/S2 (2026-07-04 adversarial review): the entailment moat must be
REACHABLE from Memory.add(), and the honest default must be explicit.

The critic falsified the headline claim in 3 lines of SDK: add() never ran
the source⊢fact entailment (L4) because it (a) had no per-call switch and
(b) required the ENGRAM_GROUNDING_WRITE env var; and reject-mode was
unreachable (no gate_mode param). These tests lock the fix:
- ground=True runs L4 per-call WITHOUT the env var (given a judge);
- an unsupported inference is downgraded when ground=True;
- gate_mode='reject' is reachable from add();
- default add() (ground=False, no env) does NOT run L4 (fast path intact).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from engram import Memory


class _FakeJudge:
    """Claude-scale 0-100 grounding LLM: returns the score it's told to."""
    def __init__(self, score: int):
        self._score = score

    def complete(self, system, messages, *, model=None, max_tokens=None):
        class _R:
            text = f"Score: {self._score}"  # the L4 prompt asks for "Score: NN"
        return _R()


def _mem(score: int) -> Memory:
    tmp = Path(tempfile.mkdtemp(prefix="s1s2_")) / "mem.db"
    return Memory(path=tmp, grounding_llm=_FakeJudge(score))


def test_ground_true_runs_L4_without_env_var(monkeypatch):
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE", raising=False)
    m = _mem(score=90)
    r = m.add("Paris is the capital of France.", topic="geo",
              source="The capital of France is Paris.", ground=True)
    assert r["stored"] and r["grounding_score"] == 90.0  # L4 actually ran


def test_ground_true_downgrades_unsupported_inference(monkeypatch):
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE", raising=False)
    m = _mem(score=5)  # source does NOT entail the fact
    r = m.add("The user is an expert in quantum computing.", topic="bio",
              source="The user mentioned they once read an article about physics.",
              ground=True)
    assert r["status"] == "quarantined"      # confabulated inference caught
    assert r["grounding_score"] == 5.0


def test_reject_mode_reachable_from_add(monkeypatch):
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE", raising=False)
    m = _mem(score=5)
    r = m.add("The user is an expert in quantum computing.", topic="bio",
              source="The user mentioned they once read an article about physics.",
              ground=True, gate_mode="reject")
    assert r["stored"] is False and r["status"] == "rejected"


def test_default_add_does_not_run_L4(monkeypatch):
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE", raising=False)
    m = _mem(score=5)
    # ground defaults False: the fast L1 path runs, L4 (entailment) does not
    r = m.add("Some benign fact.", topic="x",
              source="An unrelated sentence.")
    assert r["grounding_score"] is None      # L4 was not invoked
