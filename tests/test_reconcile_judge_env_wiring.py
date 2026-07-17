"""ENGRAM_RECONCILE_NLI=local wires the LOCAL NLI judge (no claude -p, O4-clean)
into reconcile-on-write — making the trust-maintenance moat usable at ~4x conflict-
recall WITHOUT a paid judge and without a programmatic set_reconcile_judge call.
=1/on/true/yes/llm still wires the subscription LLM judge; unset -> lexical default.

Hermetic: a stub semantic captures the judge; neither judge loads its model (both are
lazy), so this never touches transformers or claude -p."""
from __future__ import annotations

from verimem.agent import wire_reconcile_judge


class _Sem:
    def __init__(self):
        self.judge = "UNSET"

    def set_reconcile_judge(self, j):
        self.judge = j


def test_local_value_wires_local_nli_judge(monkeypatch) -> None:
    monkeypatch.setenv("ENGRAM_RECONCILE_NLI", "local")
    from verimem.local_relation import LocalRelationJudge
    s = _Sem()
    wire_reconcile_judge(s, llm=object())
    assert isinstance(s.judge, LocalRelationJudge)


def test_truthy_value_wires_llm_judge(monkeypatch) -> None:
    monkeypatch.setenv("ENGRAM_RECONCILE_NLI", "1")
    from verimem.semantic_conflict import LLMRelationJudge
    s = _Sem()
    wire_reconcile_judge(s, llm=object())
    assert isinstance(s.judge, LLMRelationJudge)


def test_unset_leaves_lexical_default(monkeypatch) -> None:
    monkeypatch.delenv("ENGRAM_RECONCILE_NLI", raising=False)
    s = _Sem()
    wire_reconcile_judge(s, llm=object())
    assert s.judge == "UNSET"  # no judge wired -> lexical (unchanged)


def test_wiring_never_raises_on_bad_semantic(monkeypatch) -> None:
    monkeypatch.setenv("ENGRAM_RECONCILE_NLI", "local")

    class _Boom:
        def set_reconcile_judge(self, j):
            raise RuntimeError("boom")

    wire_reconcile_judge(_Boom(), llm=object())  # must not raise
