"""Grounding-verified answering (the anti-hallucination read-path, asse madre).

BENCHMARKS.md: recall@30=0.96 (the memory FINDS the fact) but QA-Correct=0.433 /
Hallucination=0.167 — the answerer gets fooled by distractors. The write-time
grounding_score is 0% on the real corpus (opt-in, never on), so conditioning on a
STORED score is empty. This ships the answer-time defense instead: the LLM answers
from the retrieved facts, then a local cross-encoder (no LLM) verifies the answer
is entailed by a retrieved fact — if no fact supports it, abstain (NO ANSWER)
rather than serve a probable hallucination.

Empirically the local CE separates cleanly (probe 2026-07-16): a fact entailing the
answer scores ~91-94, a distractor/wrong answer ~1-3.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from verimem.client import Memory


def _local_ce_available() -> bool:
    # the answer()-verification tests exercise the REAL local cross-encoder;
    # skip where the distilled model is absent (CI) so a missing model is a skip,
    # not a red build. The CE's separation is independently proven by the probe
    # recorded in the answer() commit; here we test answer()'s logic ON it.
    try:
        from verimem.local_grounding import try_local_score
        return try_local_score("Rex is a poodle.", "Rex is a poodle.") is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _local_ce_available(),
    reason="local cross-encoder (local_gate_ce_v2) not available — real-CE test")


class _LLM:
    """Deterministic stub: returns a fixed answer regardless of the prompt."""
    def __init__(self, text):
        self._t = text
    def complete(self, system, messages, **kw):
        return type("R", (), {"text": self._t})()


@pytest.fixture()
def mem():
    m = Memory(path=Path(tempfile.mkdtemp()) / "a.db")
    m.add("Rex is a poodle.", topic="pets")
    m.add("Rex was adopted in March 2026.", topic="pets")
    m.add("Martin works as a nurse in Berlin.", topic="people")
    return m


def test_answer_serves_a_fact_supported_answer(mem):
    out = mem.answer("What breed is Rex?", llm=_LLM("Rex is a poodle."))
    assert out["grounded"] is True
    assert "poodle" in out["answer"]
    assert out["support_score"] >= 40.0


def test_answer_abstains_when_llm_hallucinates(mem):
    # the model asserts a breed NO retrieved fact supports -> the CE catches it
    out = mem.answer("What breed is Rex?", llm=_LLM("Rex is a labrador."))
    assert out["answer"] == "NO ANSWER", f"served a hallucination: {out}"
    assert out["grounded"] is False
    assert out["reason"] == "unsupported_by_facts"
    # the caught hallucination is REPORTED (not silently dropped) for audit
    assert out["raw_answer"] == "Rex is a labrador."


def test_answer_passes_through_model_abstention(mem):
    out = mem.answer("What is the capital of Mars?", llm=_LLM("NO ANSWER"))
    assert out["answer"] == "NO ANSWER"
    assert out["reason"] == "model_abstained"


def test_answer_no_facts_abstains(mem):
    empty = Memory(path=Path(tempfile.mkdtemp()) / "e.db")
    out = empty.answer("anything?", llm=_LLM("something confident"))
    assert out["answer"] == "NO ANSWER"
    assert out["reason"] == "no_facts"


def test_answer_KNOWN_LIMIT_distractor_in_memory_is_served(mem):
    """HONEST LIMIT (pinned, not a bug): answer() verifies against retrieved facts,
    so a WRONG fact stored IN memory supports the wrong answer and is served. The
    distractor-in-memory case (the dominant half of the 0.167 gap) needs per-fact
    grounding/reconcile, NOT this post-verifier. Documented so no one over-claims."""
    mem.add("Rex is a labrador.", topic="pets")  # a wrong fact now co-exists
    out = mem.answer("What breed is Rex?", llm=_LLM("Rex is a labrador."))
    assert out["grounded"] is True          # the CE finds the stored distractor
    assert out["answer"] == "Rex is a labrador."   # ...and serves the wrong answer
    assert out["support_score"] >= 40.0
