"""Product conversation ingestion (iter 34) — the competitors' core feature,
built with our winning granularity AND our trust gate.

Gap found 2026-07-05 (Aurelio challenge "real development, not tests"): the
+6-9pp atomic-extraction win lived ONLY in the benchmark harness; the product
path (transcript_promote) promotes single turns VERBATIM by hand. mem0/Zep sell
"add(messages) -> memories" as their core. This module ships it properly:

  conversation -> ATOMIC facts (shared prompt, single source of truth with the
  bench) -> each stored through SemanticMemory.store (anti-confab gate) with
  conversation provenance and a dedicated writer_role.

Hermetic: the LLM is injected (stub here) — no network, no claude -p.
"""
from __future__ import annotations

from engram.conversation_ingest import (
    ATOMIC_EXTRACT_SYSTEM,
    ingest_conversation,
    parse_extracted_lines,
)
from engram.semantic import SemanticMemory


class _StubLLM:
    """Returns a fixed extraction; records the prompt it was called with."""

    def __init__(self, text):
        self._text = text
        self.calls = []

    def complete(self, system, messages, **kw):
        self.calls.append({"system": system, "messages": messages})

        class R:
            text = self._text
        return R()


_CONV = [
    {"role": "user", "content": "Hi! I'm Martin Mark, I work as a nurse in Berlin "
                                "and I just adopted a puppy called Rex."},
    {"role": "assistant", "content": "Congrats on Rex!"},
]


def test_parse_extracted_lines_strips_bullets_and_numbering() -> None:
    raw = "- Martin Mark works as a nurse\n2. Martin Mark lives in Berlin\n\n* ok"
    lines = parse_extracted_lines(raw)
    assert lines[:2] == ["Martin Mark works as a nurse",
                         "Martin Mark lives in Berlin"]


def test_ingest_stores_atomic_facts_with_provenance(tmp_path) -> None:
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    llm = _StubLLM("Martin Mark works as a nurse in Berlin\n"
                   "Martin Mark adopted a puppy called Rex")
    res = ingest_conversation(sm, _CONV, llm=llm,
                              conversation_id="conv-42", embed="sync")
    assert res["stored"] == 2 and res["rejected"] == 0
    assert llm.calls[0]["system"] == ATOMIC_EXTRACT_SYSTEM  # the WINNING prompt
    facts = [sm.get(fid) for fid in res["fact_ids"]]
    for f in facts:
        assert f.status == "model_claim"          # claims, not laundered truth
        assert f.writer_role == "conversational_ingest"
        assert any("conversation:conv-42" in (s or "")
                   for s in (f.source_episodes or [])), "provenance required"
    props = {f.proposition for f in facts}
    assert "Martin Mark adopted a puppy called Rex" in props


def test_ingest_empty_extraction_stores_nothing(tmp_path) -> None:
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    res = ingest_conversation(sm, _CONV, llm=_StubLLM(""),
                              conversation_id="c0")
    assert res["stored"] == 0 and res["fact_ids"] == []


def test_ingest_llm_error_is_failsafe(tmp_path) -> None:
    class _Boom:
        def complete(self, *a, **k):
            raise RuntimeError("llm down")

    sm = SemanticMemory(db_path=tmp_path / "s.db")
    res = ingest_conversation(sm, _CONV, llm=_Boom(), conversation_id="c1")
    assert res["stored"] == 0 and res["error"], "must not raise, must report"


def test_ingest_redacts_secrets_before_store(tmp_path) -> None:
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    llm = _StubLLM("Martin's API key is sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAA")
    res = ingest_conversation(sm, _CONV, llm=llm, conversation_id="c2",
                              embed="sync")
    if res["stored"]:
        f = sm.get(res["fact_ids"][0])
        assert "sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAA" not in f.proposition


def test_bench_prompt_is_the_product_prompt() -> None:
    """Single source of truth: the benchmark imports the PRODUCT prompt, so a
    bench win IS a product win from now on."""
    from benchmark.halumem_extraction_f1 import _PROMPTS
    assert _PROMPTS["atomic"] is ATOMIC_EXTRACT_SYSTEM


def test_consolidate_merges_and_drops(monkeypatch) -> None:
    from engram.conversation_ingest import consolidate_facts
    cleaned = "Martin Mark works as a nurse in Berlin\nMartin Mark adopted a puppy"
    llm = _StubLLM(cleaned)
    out = consolidate_facts(
        ["Martin Mark is a nurse", "Martin Mark works as a nurse in Berlin",
         "Hello there", "Martin Mark adopted a puppy"], llm=llm)
    assert out == ["Martin Mark works as a nurse in Berlin",
                   "Martin Mark adopted a puppy"]


def test_consolidate_failsafe_returns_original_on_error() -> None:
    from engram.conversation_ingest import consolidate_facts

    class _Boom:
        def complete(self, *a, **k):
            raise RuntimeError("down")

    orig = ["Martin Mark is a nurse", "Martin Mark likes tea"]
    assert consolidate_facts(orig, llm=_Boom()) == orig


def test_consolidate_empty_pass_keeps_original() -> None:
    from engram.conversation_ingest import consolidate_facts
    orig = ["Martin Mark is a nurse"]
    assert consolidate_facts(orig, llm=_StubLLM("")) == orig
