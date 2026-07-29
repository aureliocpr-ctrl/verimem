"""Counting the assertions in a rejected claim, on claims that were really rejected.

The three cases below are verbatim from 2026-07-29: three consecutive attempts
to save one checkpoint, each rejected with the same unactionable "the source
does not support this proposition". The facts were true — I had verified them —
but each was proven SOMEWHERE ELSE than in the source attached, and the verdict
named no part. Three tries to find it by hand, and what worked every time was
SPLITTING the sentence.

Naming the guilty clause was tried first and does not work: see the module
docstring for the two measurements (per-clause scoring answers backwards;
ablation scored 0 of 2). So these tests cover the only thing that can be said
without a model — that the sentence makes more than one assertion — and the one
way that claim could still be wrong: cutting a LIST into fake assertions.
"""
from __future__ import annotations

import pytest

from verimem.unsupported_span import split_claim_clauses

# Case 1 — the source was a commit message about the MCP channel; the claim also
# asserted what the SDK preset does, which that message never mentions.
CASO_1 = ("Il moat non girava sul canale MCP: hippo_remember non passava "
          "ground_write e ricadeva sull ambiente, mentre il preset balanced "
          "dell SDK passa ground=True e faceva giudicare la CLI.")

# Case 2 — same checkpoint, causal link added; the source reports the two facts
# separately and never joins them.
CASO_2 = ("Sul canale MCP la stessa scrittura con e senza source finiva con "
          "grounding NULL, perche il gate risolveva il moat dall ambiente.")

# Case 3 — the source was the abstention bench numbers; the claim opened with a
# diagnosis about which surfaces were off, which the numbers do not state.
CASO_3 = ("L astensione era spenta di default per SDK console e gateway "
          "mentre il canale MCP si asteneva, e su venti domande il gate "
          "acceso non toglie alcuna risposta che lo store poteva dare.")


def test_a_list_is_not_three_claims():
    """"SDK, console e gateway" is one enumeration. Cutting on a bare `e` would
    turn every list into separate assertions and point at a fragment."""
    clauses = split_claim_clauses("Il gate copre SDK, console e gateway.")
    assert len(clauses) == 1, clauses


@pytest.mark.parametrize("text,attesa", [
    (CASO_1, "mentre il preset balanced"),
    (CASO_2, "perche il gate risolveva"),
    (CASO_3, "e su venti domande"),
])
def test_a_new_assertion_starts_a_new_clause(text, attesa):
    clauses = split_claim_clauses(text)
    assert len(clauses) >= 2, clauses
    assert any(attesa in c for c in clauses), clauses


def test_the_gate_says_how_many_assertions_it_judged_as_one(monkeypatch):
    """The advice a writer actually reads, wired end to end.

    The rejection used to end at "likely a confabulated inference", which is a
    verdict, not a next step. It now states the one fact that makes the next
    step obvious and that no model has to guess.
    """
    import types

    from verimem.anti_confab_gate import run_validation_gate

    class _Judge:
        def complete(self, system, messages, *, model=None, max_tokens=None):  # noqa: ANN001
            return types.SimpleNamespace(text="SCORE: 5")

    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    monkeypatch.delenv("ENGRAM_GRADED_ADMISSION", raising=False)
    r = run_validation_gate(
        proposition=CASO_3, verified_by=None, topic=None, agent=None,
        source="commit b7771f7a: 0 wrong abstentions, 8/8 caught",
        grounding_llm=_Judge(),
    )
    l4 = [w for w in (r.warnings or []) if w.get("layer") == "L4-grounding"]
    assert l4, f"no L4 warning on a rejected write: {r.warnings}"
    advice = l4[0].get("advice", "")
    assert "3 separate assertions" in advice, advice
    assert "split" in advice.lower(), advice


def test_a_single_assertion_gets_no_split_advice(monkeypatch):
    """Telling someone to split a sentence that says one thing is noise, and
    noise is how the useful half of a message stops being read."""
    import types

    from verimem.anti_confab_gate import run_validation_gate

    class _Judge:
        def complete(self, system, messages, *, model=None, max_tokens=None):  # noqa: ANN001
            return types.SimpleNamespace(text="SCORE: 5")

    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    monkeypatch.delenv("ENGRAM_GRADED_ADMISSION", raising=False)
    r = run_validation_gate(
        proposition="Il totale della fattura e 1240 euro.",
        verified_by=None, topic=None, agent=None,
        source="Fattura 88: imponibile 1000, IVA 240.",
        grounding_llm=_Judge(),
    )
    l4 = [w for w in (r.warnings or []) if w.get("layer") == "L4-grounding"]
    if l4:
        assert "separate assertions" not in l4[0].get("advice", "")
