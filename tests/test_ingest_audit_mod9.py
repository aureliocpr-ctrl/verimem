"""Fase-C audit mod.9 — conversation_ingest.py line-by-line (2026-07-17).

Three real defects, pinned RED before the fix:

M9-1 (MED, silent data loss): ``render_conversation`` truncates at 12k chars
with NO signal — a long conversation (the gateway accepts 1MB bodies) loses
its tail and the ingest result says nothing. Silent caps read as
"covered everything" when they didn't (standing project rule). The result
dict must carry ``truncated``; the cap must be overridable end-to-end.

M9-2 (MED, parser corruption): ``parse_extracted_lines`` lstrips the char-set
``"-*•0123456789. "``, so a legitimate fact STARTING with digits is eaten:
"3M employs Rex." → "M employs Rex.", "1Password stores vaults." →
"Password stores vaults.". Only ONE leading bullet/number MARKER ("1. ", "2)",
"- ", "* ") may be stripped — never digits that belong to the fact.

M9-3 (LOW, lost origin tag): the gap-fill pass never receives the BELIEF
instruction, so an unverified user assertion recovered by ``completeness=True``
enters as plain ``model_claim`` — exactly the laundering the Giro-2 tag exists
to prevent.
"""
from __future__ import annotations

from engram.conversation_ingest import (
    ingest_conversation,
    parse_extracted_lines,
    render_conversation,
)


class _StubLLM:
    """Returns queued replies; records every (system, user) call."""

    def __init__(self, replies: list[str]):
        self.replies = list(replies)
        self.calls: list[tuple[str, str]] = []

    def complete(self, system, messages, max_tokens=1200):
        self.calls.append((system, messages[0]["content"]))

        class R:
            text = self.replies.pop(0) if self.replies else ""

        return R()


# ---- M9-2: parser must not eat leading digits of real facts ----------------

def test_parser_strips_bullet_markers_only():
    text = ("1. Alice likes tea\n"
            "2) Bob visited Rome\n"
            "- Carol plays chess\n"
            "* Dan owns a kayak\n"
            "• Eve speaks French")
    assert parse_extracted_lines(text) == [
        "Alice likes tea", "Bob visited Rome", "Carol plays chess",
        "Dan owns a kayak", "Eve speaks French"]


def test_parser_preserves_digit_leading_facts():
    text = ("3M employs Rex as a chemist.\n"
            "1Password stores the team vaults.\n"
            "23andMe processed the sample.")
    assert parse_extracted_lines(text) == [
        "3M employs Rex as a chemist.",
        "1Password stores the team vaults.",
        "23andMe processed the sample."]


def test_parser_numbered_bullet_before_digit_fact():
    # a numbered list whose FACT also starts with a digit: strip the marker,
    # keep the fact's own digits
    assert parse_extracted_lines("1. 3M employs Rex.") == ["3M employs Rex."]


# ---- M9-1: truncation must be visible and the cap overridable ---------------

def test_render_conversation_reports_truncation():
    msgs = [{"role": "user", "content": "x" * 20000}]
    text, truncated = render_conversation(msgs, cap_chars=12000,
                                          with_flag=True)
    assert truncated is True
    assert len(text) == 12000
    text2, tr2 = render_conversation(msgs, cap_chars=50000, with_flag=True)
    assert tr2 is False and len(text2) > 12000


def test_ingest_result_carries_truncated_flag(tmp_path):
    from engram.semantic import SemanticMemory
    sm = SemanticMemory(db_path=tmp_path / "m.db")
    llm = _StubLLM(["Alice likes tea"])
    res = ingest_conversation(
        sm, [{"role": "user", "content": "y" * 20000}], llm=llm,
        conversation_id="c1", consolidate=False, embed="sync")
    assert res["truncated"] is True
    # and the LLM saw exactly the capped dialogue, not the full text
    assert "y" * 12001 not in llm.calls[0][1]

    llm2 = _StubLLM(["Alice likes tea"])
    res2 = ingest_conversation(
        sm, [{"role": "user", "content": "short one"}], llm=llm2,
        conversation_id="c2", consolidate=False, embed="sync")
    assert res2["truncated"] is False


def test_ingest_cap_chars_overridable(tmp_path):
    from engram.semantic import SemanticMemory
    sm = SemanticMemory(db_path=tmp_path / "m2.db")
    llm = _StubLLM(["Alice likes tea"])
    res = ingest_conversation(
        sm, [{"role": "user", "content": "z" * 20000}], llm=llm,
        conversation_id="c3", consolidate=False, embed="sync",
        cap_chars=30000)
    assert res["truncated"] is False
    assert "z" * 15000 in llm.calls[0][1]      # the tail actually reached the LLM


# ---- M9-3: gap-fill must carry the BELIEF instruction when tagging ----------

def test_gapfill_receives_belief_instruction_when_tagging(tmp_path):
    from engram.semantic import SemanticMemory
    sm = SemanticMemory(db_path=tmp_path / "m3.db")
    llm = _StubLLM([
        "Alice likes tea",                       # extraction
        "BELIEF: their API is the fastest",      # gap-fill output (tagged)
    ])
    res = ingest_conversation(
        sm, [{"role": "user", "content": "long chat about tea and APIs"}],
        llm=llm, conversation_id="c4", consolidate=False, completeness=True,
        tag_beliefs=True, embed="sync")
    gap_system = llm.calls[1][0]
    assert "BELIEF" in gap_system, "gap-fill prompt lacks the origin-tag rule"
    assert res["gapfilled"] == 1
    # the recovered assertion is stored as user_belief, not laundered
    import sqlite3
    with sqlite3.connect(str(sm.db_path)) as con:
        rows = dict(con.execute(
            "SELECT proposition, status FROM facts").fetchall())
    assert rows.get("their API is the fastest") == "user_belief"
