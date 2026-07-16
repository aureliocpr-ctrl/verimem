"""CASE-B wire — trust-conditioned answering in Memory.answer().

Measured first (benchmark/wellgrounded_distractor_bench, sonnet-5, 2026-07-16):
on 12 well-grounded-distractor cases (both facts score 76-100 at the gate, so
grounding can NOT separate them) plain answer() was C=0.17 / H=0.33 / O=0.50,
while tagging each fact with the metadata the store ALREADY has
([when | source | status]) + a resolution rule lifted it to C=0.92 / H=0.08,
and it abstained 2/2 on unresolvable same-metadata conflicts. This wires that
measured lever into the product:

* ``search()`` now exposes ``asserted_at``/``created_at``/``source``/
  ``verified_by`` per hit (it already exposed status/grounding_score).
* ``answer(trust_conditioning=True)`` (default) builds tagged fact lines and
  uses the measured resolution system prompt; ``False`` restores the bare v1
  prompt byte-identically. The local-CE post-verify stays on both paths.

These pin the wiring with an LLM stub (no CE, no network).
"""
from __future__ import annotations

from engram.client import _ANSWER_SYSTEM, _ANSWER_TRUST_SYSTEM, Memory


class _StubLLM:
    """Captures the prompt; replies with a fixed text."""

    def __init__(self, reply: str = "NO ANSWER"):
        self.reply = reply
        self.calls: list[tuple[str, str]] = []

    def complete(self, system, messages, max_tokens=64):
        self.calls.append((system, messages[0]["content"]))

        class R:  # noqa: D401 — minimal response shape
            text = self.reply

        return R()


VERIFIED_REF = None  # set per-test: a real file: ref the verified_by gate accepts


def _mem(tmp_path) -> Memory:
    from engram.semantic import Fact
    global VERIFIED_REF
    m = Memory(path=tmp_path / "m.db")
    # verified is not self-declared: store()'s verified_by hard-gate demotes a
    # "verified" write whose refs don't check out (anti-laundering). Give it a
    # REAL checkable ref — a file that exists — like the trusted pipeline does.
    src = tmp_path / "minutes.txt"
    src.write_text("all-hands 2026-07-10: office moved to Turin\n", encoding="utf-8")
    VERIFIED_REF = f"file:{src}:1"
    m.semantic.store(Fact(proposition="The main office is in Turin.",
                          topic="office", status="verified",
                          verified_by=[VERIFIED_REF],
                          asserted_at=1783980000.0),     # 2026-07-14
                     embed="sync")
    m.add("The main office is in Milan.", asserted_at=1741000000.0)  # 2025-03
    return m


def test_search_exposes_provenance_fields(tmp_path):
    m = _mem(tmp_path)
    hits = m.search("main office", k=4)
    assert hits, "expected hits"
    for h in hits:
        assert "asserted_at" in h and "created_at" in h
        assert "source" in h and "verified_by" in h
    tur = next(h for h in hits if "Turin" in h["text"])
    assert tur["status"] == "verified"
    assert tur["verified_by"] == [VERIFIED_REF]
    assert tur["asserted_at"] == 1783980000.0


def test_answer_trust_conditioning_tags_facts_and_uses_trust_system(tmp_path):
    m = _mem(tmp_path)
    llm = _StubLLM()
    m.answer("Where is the main office?", llm=llm)      # default: ON
    system, user = llm.calls[0]
    assert system == _ANSWER_TRUST_SYSTEM
    # tagged lines: [when | source | status] text — both facts, each with its
    # own metadata (the verified one shows its verifier and its event date)
    assert "| verified]" in user and "| model_claim]" in user
    assert "2026-07-13" in user                          # asserted_at (UTC), ISO date
    assert VERIFIED_REF in user                          # source column (the ref)
    assert "The main office is in Turin." in user


def test_answer_trust_conditioning_off_is_v1_bare_prompt(tmp_path):
    m = _mem(tmp_path)
    llm = _StubLLM()
    m.answer("Where is the main office?", llm=llm, trust_conditioning=False)
    system, user = llm.calls[0]
    assert system == _ANSWER_SYSTEM
    assert "[" not in user.split("Question:")[0]         # no metadata tags
    assert "- The main office is in Turin." in user


def test_answer_stub_abstention_still_honored(tmp_path):
    # the model_abstained path must be unchanged by the new prompt
    m = _mem(tmp_path)
    out = m.answer("Where is the main office?", llm=_StubLLM("NO ANSWER"))
    assert out["answer"] == "NO ANSWER"
    assert out["reason"] == "model_abstained"


def test_undated_unrecorded_facts_tag_honestly(tmp_path):
    m = Memory(path=tmp_path / "m2.db")
    m.add("The retro is in room Alpha.")                 # no metadata at all
    llm = _StubLLM()
    m.answer("Which room?", llm=llm)
    _, user = llm.calls[0]
    # created_at always exists → the when column is a real date, never a lie;
    # source falls back to an explicit "unrecorded", not an invented one.
    assert "| unrecorded | model_claim]" in user
