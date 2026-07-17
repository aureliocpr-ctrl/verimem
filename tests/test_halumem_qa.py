"""HaluMem QA — the reconstruction / faithful-QA slice (iter 37).

Aurelio mandate 2026-07-05 ("distaccarli totalmente, non perdere niente"): the
extraction-F1 game is string-overlap and matcher-capped. HaluMem ships per-session
`questions` whose CORRECT answer, for 39/164, is to ABSTAIN ("Unknown; not
provided") — the Memory-Boundary category — and another 39 are Memory-Conflict
(the reconciled/current fact). 48% of the benchmark rewards exactly what only we
have: the anti-confab gate + reconcile-on-write. This runner ingests the dialogue
through OUR gated pipeline (verimem.conversation_ingest) and answers from the
STORED facts alone — measuring lossless usefulness, not overlap.

Hermetic: LLM injected (stub), no network, no claude -p.
"""
from __future__ import annotations

import tempfile
from pathlib import Path


class _StubLLM:
    """Returns a fixed extraction; records prompts. Two-pass safe (extract +
    consolidate get the same text back)."""

    def __init__(self, text):
        self._text = text
        self.calls = []

    def complete(self, system, messages, **kw):
        self.calls.append({"system": system, "messages": messages})

        class R:
            text = self._text
        return R()


def test_is_abstention_gold_recognises_boundary_answers() -> None:
    from benchmark.halumem_qa import _is_abstention_gold
    assert _is_abstention_gold("Unknown; not provided by the user.")
    assert _is_abstention_gold("This was not mentioned in the conversation.")
    assert _is_abstention_gold("There is no information about that.")
    # a concrete fact is NOT an abstention
    assert not _is_abstention_gold("Martin Mark lives in Berlin.")
    assert not _is_abstention_gold("He is a nurse.")


def _mini_dataset():
    return [{
        "sessions": [{
            "dialogue": [
                {"role": "user", "content": "I'm Martin Mark, a nurse in Berlin."},
                {"role": "assistant", "content": "Nice to meet you!"},
            ],
            "questions": [
                {"question": "Where does Martin Mark live?", "answer": "Berlin",
                 "question_type": "Basic Fact Recall"},
                {"question": "What is Martin Mark's middle name?",
                 "answer": "Unknown; not provided by the user.",
                 "question_type": "Memory Boundary"},
            ],
        }],
    }]


def test_build_records_ingests_via_our_pipeline_and_flags_abstention() -> None:
    from benchmark.halumem_qa import build_records_halumem
    llm = _StubLLM("Martin Mark works as a nurse in Berlin")
    workdir = Path(tempfile.mkdtemp(prefix="hm_qa_test_"))
    try:
        recs = build_records_halumem(_mini_dataset(), k=5, workdir=workdir,
                                     ingest_llm=llm)
    finally:
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)
    assert len(recs) == 2, "one record per question"
    # the ingest went through OUR pipeline: the atomic extraction prompt ran
    from verimem.conversation_ingest import ATOMIC_EXTRACT_SYSTEM
    assert any(c["system"] == ATOMIC_EXTRACT_SYSTEM for c in llm.calls)
    by_cat = {r["category"]: r for r in recs}
    # Basic Fact Recall: a real answer, NOT adversarial, context recalled from store
    fact_rec = by_cat["Basic Fact Recall"]
    assert fact_rec["adversarial"] is False
    assert isinstance(fact_rec["context"], list)
    # Memory Boundary: correct behaviour is to ABSTAIN -> adversarial, gold blanked
    bnd = by_cat["Memory Boundary"]
    assert bnd["adversarial"] is True
    assert bnd["gold"] == ""


def test_parse_halumem_ts() -> None:
    from benchmark.halumem_qa import _parse_halumem_ts
    a = _parse_halumem_ts("Sep 04, 2025, 18:42:18")
    b = _parse_halumem_ts("Dec 15, 2025, 09:00:00")
    assert a and b and b > a, "later date -> larger epoch (real age gap)"
    assert _parse_halumem_ts("") is None
    assert _parse_halumem_ts("not a date") is None


def test_raw_turns_arm_skips_the_gate() -> None:
    """The baseline arm (what mem0/raw ingestion does) stores turns verbatim and
    never calls the extraction LLM — so a comparison isolates OUR pipeline's
    contribution."""
    from benchmark.halumem_qa import build_records_halumem
    llm = _StubLLM("should not be called")
    workdir = Path(tempfile.mkdtemp(prefix="hm_qa_raw_"))
    try:
        recs = build_records_halumem(_mini_dataset(), k=5, workdir=workdir,
                                     ingest_llm=llm, raw_turns=True)
    finally:
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)
    assert len(recs) == 2
    assert llm.calls == [], "raw-turns baseline must not invoke the extraction LLM"


def test_raw_turns_baseline_visible_with_event_time_stamp() -> None:
    """Review 5-lenti C1 (CRITICAL): the baseline arm used to write the HaluMem
    event-time into created_at — the anti-spoof + half-life guards then hid the
    baseline store from default recall (dataset scale: 1379/1387 sessions out of
    the visible window), inflating every pipeline-vs-raw delta. The stamp must go
    to asserted_at (v13), exactly like the pipeline arm does."""
    from benchmark.halumem_qa import _ingest_raw_turns, _parse_halumem_ts
    from verimem.semantic import SemanticMemory
    workdir = Path(tempfile.mkdtemp(prefix="hm_raw_stamp_"))
    try:
        sm = SemanticMemory(db_path=workdir / "raw.db")
        ts = _parse_halumem_ts("Sep 04, 2025, 18:42:18")  # real dataset event-time
        _ingest_raw_turns(sm, [{"role": "user",
                                "content": "I am Martin Mark, a nurse in Berlin."}],
                          topic="t", asserted_at=ts)
        hits = sm.recall("Where does Martin Mark live?", k=5)
        assert len(hits) == 1, "baseline turn must be visible to default recall"
        fact = hits[0][0]
        assert fact.asserted_at == ts, "event-time belongs in asserted_at (v13)"
        assert fact.created_at > ts, "created_at is transaction time, never backdated"
    finally:
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)
