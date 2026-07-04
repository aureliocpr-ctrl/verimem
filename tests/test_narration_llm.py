"""LLM-refined atomic extraction from narration (2026-06-14).

Higher-recall companion to the rule-based engram.narration.extract_atomic_candidates,
with the same anti-confab discipline as engram.openie: JSON-only, one retry on a
malformed parse, [] on a second failure — never a crash, never a fabricated parse.
Tested with a FAKE llm (no real model call).
"""
from __future__ import annotations

import sqlite3
import types

from engram.narration_llm import extract_atomic_facts


class _FakeLLM:
    """Returns the queued responses in order (last one repeats)."""

    def __init__(self, *texts):
        self._texts = list(texts)
        self._i = 0

    def complete(self, **_kw):
        t = self._texts[min(self._i, len(self._texts) - 1)]
        self._i += 1
        return types.SimpleNamespace(text=t)


def test_extracts_claims_from_valid_json():
    llm = _FakeLLM('{"claims": ["PR #217 merged (commit 8d848fa)", "recall bounded at 2s"]}')
    out = extract_atomic_facts("ENGRAM 2026-06-13 sera: shipped stuff", llm)
    assert out == ["PR #217 merged (commit 8d848fa)", "recall bounded at 2s"]


def test_retry_on_malformed_then_fixed():
    llm = _FakeLLM("not json at all", '{"claims": ["fixed.py:10 patched"]}')
    out = extract_atomic_facts("narrative prose", llm)
    assert out == ["fixed.py:10 patched"]


def test_two_failures_yield_empty_no_crash():
    llm = _FakeLLM("garbage", "still not json")
    assert extract_atomic_facts("narrative prose", llm) == []


def test_non_dict_or_missing_claims_is_empty():
    assert extract_atomic_facts("x", _FakeLLM('["a","b"]')) == []  # list, not {claims:[]}
    assert extract_atomic_facts("x", _FakeLLM('{"other": 1}')) == []


def test_empty_input_and_no_llm_are_safe():
    assert extract_atomic_facts("", _FakeLLM('{"claims":["a"]}')) == []
    assert extract_atomic_facts("x", None) == []


def test_dedup_casefold_and_cap():
    llm = _FakeLLM('{"claims": ["Alpha", "alpha", "Beta", "", "  "]}')
    assert extract_atomic_facts("n", llm) == ["Alpha", "Beta"]
    many = _FakeLLM('{"claims": ' + str([f"claim {i}" for i in range(20)]).replace("'", '"') + "}")
    assert len(extract_atomic_facts("n", many, max_claims=5)) == 5


def test_llm_call_exception_degrades_to_empty():
    class _Boom:
        def complete(self, **_kw):
            raise RuntimeError("model down")
    assert extract_atomic_facts("narrative", _Boom()) == []


# --- wiring: archive_and_extract_narration uses the LLM path when given an llm ---

def test_archive_uses_llm_extractor_when_provided(tmp_path):
    from engram.narration import archive_and_extract_narration
    db = tmp_path / "s.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE facts (id TEXT PRIMARY KEY, topic TEXT, proposition TEXT, "
                "created_at REAL, superseded_by TEXT)")
    # No verifiable anchor (no SHA / PR# / file:line / outcome verb / number+unit),
    # so the rule-based pass yields 0 atoms — past the 300-char dated-narration gate.
    narr = ("ENGRAM 2026-06-13 sera: we explored many directions and talked through the "
            "approach at length over the evening, weighing several options and revisiting "
            "earlier assumptions, going well beyond the three hundred character minimum so "
            "that the detector reliably treats this row as a dated first person session "
            "narration rather than an atomic piece of knowledge, with no commit hashes, no "
            "pull request numbers, no file references and no measured numbers anywhere here.")
    con.execute("INSERT INTO facts VALUES('n1','project/engram',?,1.0,NULL)", (narr,))
    con.commit(); con.close()
    assert archive_and_extract_narration(db, dry_run=True)["narration_found"] == 1
    # Two DIFFERENT fake LLMs over the SAME prose: the atomic count tracks the
    # LLM's output (2 vs 3), proving the llm path is taken — the rule-based pass
    # would give a single fixed number regardless of the llm.
    out2 = archive_and_extract_narration(
        db, dry_run=True, llm=_FakeLLM('{"claims": ["claim A", "claim B"]}'))
    out3 = archive_and_extract_narration(
        db, dry_run=True, llm=_FakeLLM('{"claims": ["claim A", "claim B", "claim C"]}'))
    assert out2["atomic_candidates"] == 2
    assert out3["atomic_candidates"] == 3, "the LLM extractor (not the rule pass) must be used"
