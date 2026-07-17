"""Giro 2 — the ingest tagging that PRODUCES ``user_belief`` (2026-07-16).

The foundation (``af22b04``) added the status, ranked it below ``model_claim``,
and hid it from default recall via five SQL filters (``test_user_belief.py``).
But nothing WROTE it — ``user_belief`` was a ghost status. This closes that:
``ingest_conversation(..., tag_beliefs=True)`` teaches the extraction LLM to
prefix an unverified factual assertion with ``BELIEF:``; the store loop maps
that one line to ``status="user_belief"`` instead of ``model_claim``, so the
memory stops laundering a user's unproven claim into default recall.

Opt-in and conservative by design:
  * ``tag_beliefs`` defaults **False** — the extraction prompt stays
    byte-identical to today (the benchmark's ``ATOMIC_EXTRACT_SYSTEM`` constant
    is never mutated) and every fact stays ``model_claim``. No regression, no
    silent default flip (Giro 1b lesson: no default flip without a MemSyco delta).
  * the marker is only interpreted when we ASKED for it — flag off never strips.
  * "when unsure, do NOT tag" — biased toward KEEPING personalization in recall.
"""
from __future__ import annotations

from verimem.conversation_ingest import (
    ATOMIC_EXTRACT_SYSTEM,
    ingest_conversation,
    strip_belief_marker,
)
from verimem.semantic import SemanticMemory


class _StubLLM:
    """Echoes a fixed extraction; records every prompt it was called with."""

    def __init__(self, text):
        self._text = text
        self.calls = []

    def complete(self, system, messages, **kw):
        self.calls.append({"system": system, "messages": messages})

        class R:
            text = self._text
        return R()


_CONV = [
    {"role": "user", "content": "Our vendor's API is the fastest on the market. "
                                "Also I'm Martin Mark and I work as a nurse."},
    {"role": "assistant", "content": "Noted."},
]


def test_strip_belief_marker_unit() -> None:
    assert strip_belief_marker("BELIEF: X is faster than Y") == ("X is faster than Y", True)
    assert strip_belief_marker("belief: lower-case tag") == ("lower-case tag", True)
    assert strip_belief_marker("  BELIEF:no space") == ("no space", True)
    # a normal fact is untouched
    assert strip_belief_marker("Martin Mark works as a nurse") == (
        "Martin Mark works as a nurse", False)
    # the marker only counts as a prefix, never mid-line
    assert strip_belief_marker("Martin holds a BELIEF: about X") == (
        "Martin holds a BELIEF: about X", False)


def test_belief_marker_maps_line_to_user_belief_status(tmp_path) -> None:
    """A ``BELIEF:``-tagged line -> status user_belief (marker stripped); an
    untagged line on the same extraction -> model_claim as always."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    llm = _StubLLM("BELIEF: The vendor's API is the fastest on the market\n"
                   "Martin Mark works as a nurse")
    res = ingest_conversation(sm, _CONV, llm=llm, conversation_id="cb1",
                              tag_beliefs=True, consolidate=False, embed="sync")
    facts = [sm.get(fid) for fid in res["fact_ids"]]
    by_status = {f.status: f for f in facts}
    assert "user_belief" in by_status, f"no belief tagged; got {[f.status for f in facts]}"
    assert "model_claim" in by_status, "the plain fact must stay a model_claim"
    belief = by_status["user_belief"]
    assert belief.proposition == "The vendor's API is the fastest on the market", \
        "marker must be stripped from the stored proposition"
    assert belief.writer_role == "conversational_ingest", "no gate bypass"


def test_tag_beliefs_default_off_is_byte_identical_and_no_belief(tmp_path) -> None:
    """Default (flag off): prompt byte-identical to the bench constant AND the
    marker is NOT interpreted — nothing becomes user_belief."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    llm = _StubLLM("BELIEF: The vendor's API is the fastest on the market\n"
                   "Martin Mark works as a nurse")
    res = ingest_conversation(sm, _CONV, llm=llm, conversation_id="cb2",
                              consolidate=False, embed="sync")
    assert llm.calls[0]["system"] == ATOMIC_EXTRACT_SYSTEM, \
        "flag off must not touch the winning extraction prompt"
    statuses = {sm.get(fid).status for fid in res["fact_ids"]}
    assert "user_belief" not in statuses, "flag off must never produce a belief"


def test_tag_beliefs_on_extends_prompt_without_mutating_base(tmp_path) -> None:
    """flag on: the belief instruction is APPENDED (base prompt unchanged), and
    the consolidate pass is told to preserve the marker."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    llm = _StubLLM("Martin Mark works as a nurse")
    ingest_conversation(sm, _CONV, llm=llm, conversation_id="cb3",
                        tag_beliefs=True, consolidate=True, embed="sync")
    extract_sys = llm.calls[0]["system"]
    assert extract_sys.startswith(ATOMIC_EXTRACT_SYSTEM), "base prompt must be intact"
    assert "BELIEF:" in extract_sys, "extraction must ask for the marker"
    # calls[1] is the consolidation pass (consolidate=True) — it must preserve markers
    consolidate_sys = llm.calls[1]["system"]
    assert "BELIEF:" in consolidate_sys, "consolidate must be told to keep the marker"
