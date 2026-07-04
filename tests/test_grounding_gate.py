"""TDD for engram.grounding_gate — the externalized evidence-verification gate.

The gate turns R6/R7 into product: the model's introspective confidence is at chance
for flagging its own fabrications (R6, AUROC 0.494), but an EXTERNAL verifier separates
sound from fabricated answers far better (R7, 0.810 vs 0.705). The gate computes that
external grounding score and abstains below a threshold. All logic is unit-tested with a
stub LLM — deterministic, no claude -p, no network.
"""
from __future__ import annotations

import types

from engram.grounding_gate import (
    _BASIC_SYSTEM,
    _SPAN_SYSTEM,
    DEFAULT_THRESHOLD,
    GateResult,
    fact_grounding_score,
    fact_grounding_span,
    gate_answer,
    grounding_score,
    is_grounded,
    optimal_threshold,
    select_relevant_span,
    should_store_fact,
)


class StubLLM:
    """Records the system prompts it was called with; returns a fixed text."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.systems: list[str] = []

    def complete(self, system, messages, *, model=None, max_tokens=None):  # noqa: ANN001
        self.systems.append(system)
        return types.SimpleNamespace(text=self.text)


class RecLLM:
    """Records the user-message content (so tests can assert WHICH source the gate saw)."""

    def __init__(self, text: str = "SCORE: 90") -> None:
        self.text = text
        self.last_user: str | None = None

    def complete(self, system, messages, *, model=None, max_tokens=None):  # noqa: ANN001
        self.last_user = messages[0]["content"]
        return types.SimpleNamespace(text=self.text)


# ---- A1: relevant-span source selection (cuts gate over-rejection at fixed budget) -------

def test_select_relevant_span_keeps_overlapping_drops_filler() -> None:
    src = "\n".join([
        "user: the weather was cold today",
        "user: I really love quiet jazz cafes",   # the relevant line
        "user: we talked about taxes",
        "user: my commute is long",
    ])
    span = select_relevant_span(src, "prefers jazz cafes", budget=40)
    assert "jazz" in span
    assert "taxes" not in span and "commute" not in span
    assert len(span) <= 40


def test_select_relevant_span_short_source_unchanged() -> None:
    src = "user: I love jazz"
    assert select_relevant_span(src, "jazz", budget=1000) == src


def test_select_relevant_span_preserves_original_order() -> None:
    src = "a love jazz\nb hate techno\nc love jazz too"
    # both 'jazz' lines overlap; the result must keep them in original order (a before c)
    span = select_relevant_span(src, "jazz", budget=100)
    assert span.index("a love jazz") < span.index("c love jazz too")


def test_fact_grounding_score_focus_budget_trims_to_relevant_span() -> None:
    # a long source where the supporting evidence is NOT in the prefix; focus_budget must
    # span-select it so the gate sees the evidence (the A1 over-rejection fix).
    filler = "\n".join(f"user: unrelated chatter line {i}" for i in range(50))
    src = filler + "\nuser: I am allergic to peanuts"
    rec = RecLLM("SCORE: 95")
    fact_grounding_score(rec, src, "allergic to peanuts", focus_budget=40)
    assert "peanuts" in rec.last_user          # the evidence reached the judge
    assert "unrelated chatter line 0" not in rec.last_user  # filler dropped (budget full)


def test_fact_grounding_score_no_focus_budget_sends_full_source() -> None:
    rec = RecLLM("SCORE: 80")
    src = "user: alpha\nuser: beta peanuts"
    fact_grounding_score(rec, src, "peanuts", focus_budget=None)
    assert "alpha" in rec.last_user and "beta peanuts" in rec.last_user  # unchanged default


def test_grounding_score_parses() -> None:
    assert grounding_score(StubLLM("SCORE: 90"), "q", "ev", "a") == 90.0


def test_grounding_score_missing_defaults_50() -> None:
    assert grounding_score(StubLLM("no number here"), "q", "ev", "a") == 50.0


def test_grounding_score_clamps_high() -> None:
    assert grounding_score(StubLLM("SCORE: 250"), "q", "ev", "a") == 100.0


def test_is_grounded_threshold() -> None:
    assert is_grounded(90, threshold=85) is True
    assert is_grounded(80, threshold=85) is False


def test_default_threshold_is_sane() -> None:
    assert 50.0 <= DEFAULT_THRESHOLD <= 100.0


def test_gate_answer_passes_high_score() -> None:
    r = gate_answer(StubLLM("SCORE: 95"), "q", "ev", "Paris", threshold=85)
    assert isinstance(r, GateResult)
    assert r.grounded is True
    assert r.answer == "Paris"
    assert r.score == 95.0


def test_gate_answer_abstains_low_score() -> None:
    r = gate_answer(StubLLM("SCORE: 40"), "q", "ev", "Paris", threshold=85)
    assert r.grounded is False
    assert r.answer == "NO ANSWER"
    assert r.raw_answer == "Paris"


def test_gate_answer_passthrough_existing_abstention_spends_no_call() -> None:
    stub = StubLLM("SCORE: 10")  # must NOT be consulted for an already-abstaining answer
    r = gate_answer(stub, "q", "ev", "NO ANSWER", threshold=85)
    assert r.answer == "NO ANSWER"
    assert r.grounded is True
    assert stub.systems == []  # no judge call spent


def test_gate_answer_empty_is_abstention() -> None:
    stub = StubLLM("SCORE: 10")
    r = gate_answer(stub, "q", "ev", "", threshold=85)
    assert r.answer == "NO ANSWER"
    assert stub.systems == []


def test_optimal_threshold_separable() -> None:
    scores = [100, 95, 90, 80, 20, 10]
    labels = [1, 1, 1, 0, 0, 0]
    t = optimal_threshold(scores, labels)
    assert 80 < t <= 90


def test_span_judge_routes_span_prompt() -> None:
    stub = StubLLM("a quoted span\nSCORE: 100")
    grounding_score(stub, "q", "ev", "a", judge="span")
    assert stub.systems[-1] == _SPAN_SYSTEM


def test_basic_judge_default_prompt() -> None:
    stub = StubLLM("SCORE: 90")
    grounding_score(stub, "q", "ev", "a")
    assert stub.systems[-1] == _BASIC_SYSTEM


def test_env_threshold_override(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("ENGRAM_GROUNDING_THRESHOLD", "70")
    r = gate_answer(StubLLM("SCORE: 75"), "q", "ev", "Paris")  # no explicit threshold
    assert r.grounded is True  # 75 >= 70 from env


def test_env_judge_override(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("ENGRAM_GROUNDING_JUDGE", "span")
    stub = StubLLM("span\nSCORE: 88")
    grounding_score(stub, "q", "ev", "a")  # no explicit judge
    assert stub.systems[-1] == _SPAN_SYSTEM


def test_evidence_list_is_joined_not_crash() -> None:
    stub = StubLLM("SCORE: 90")
    s = grounding_score(stub, "q", ["e1", "e2"], "a")
    assert s == 90.0


class SeqLLM:
    """Returns a scripted sequence of texts across successive .complete calls."""

    def __init__(self, texts: list[str]) -> None:
        self.texts = list(texts)
        self.i = 0

    def complete(self, system, messages, *, model=None, max_tokens=None):  # noqa: ANN001
        t = self.texts[min(self.i, len(self.texts) - 1)]
        self.i += 1
        return types.SimpleNamespace(text=t)


def test_answer_question_gated_abstains_when_ungrounded(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("ENGRAM_GROUNDING_GATE", "1")
    from benchmark.qa_eval import answer_question
    llm = SeqLLM(["Paris", "SCORE: 10"])  # answer, then a low external grounding score
    assert answer_question(llm, "q", ["irrelevant context"]) == "NO ANSWER"


def test_answer_question_gated_passes_when_grounded(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("ENGRAM_GROUNDING_GATE", "1")
    from benchmark.qa_eval import answer_question
    llm = SeqLLM(["Paris", "SCORE: 99"])
    assert answer_question(llm, "q", ["Paris is the capital"]) == "Paris"


def test_answer_question_gate_off_is_unchanged(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.delenv("ENGRAM_GROUNDING_GATE", raising=False)
    from benchmark.qa_eval import answer_question
    llm = SeqLLM(["Paris", "SCORE: 10"])  # second text must never be consulted
    assert answer_question(llm, "q", ["ctx"]) == "Paris"
    assert llm.i == 1  # exactly one call: the answer, no verifier


# ---- write-path primitive (fact grounding) --------------------------------------
def test_fact_grounding_score_parses() -> None:
    assert fact_grounding_score(StubLLM("SCORE: 100"), "src", "fact") == 100.0


def test_fact_grounding_score_missing_defaults_50() -> None:
    assert fact_grounding_score(StubLLM("dunno"), "src", "fact") == 50.0


def test_should_store_fact_grounded() -> None:
    store, score = should_store_fact(StubLLM("SCORE: 95"), "src", "fact", threshold=85)
    assert store is True
    assert score == 95.0


def test_should_store_fact_confabulation_rejected() -> None:
    # a plausible inference the source does not state -> mid score -> reject
    store, score = should_store_fact(StubLLM("SCORE: 50"), "src", "fact", threshold=85)
    assert store is False
    assert score == 50.0


# ---- provenance-on-write (fact_grounding_span) ----------------------------------
def test_fact_grounding_span_extracts_span_and_score() -> None:
    out = fact_grounding_span(
        StubLLM("The Zorvex-9 reactor sustains 4200 kelvin.\nSCORE: 100"), "src", "fact")
    assert out["score"] == 100.0
    assert out["span"] == "The Zorvex-9 reactor sustains 4200 kelvin."


def test_fact_grounding_span_none_means_no_span() -> None:
    out = fact_grounding_span(StubLLM("NONE\nSCORE: 0"), "src", "fact")
    assert out["score"] == 0.0
    assert out["span"] is None


def test_fact_grounding_span_none_lowercase_dot() -> None:
    out = fact_grounding_span(StubLLM("none.\nSCORE: 0"), "src", "fact")
    assert out["span"] is None


def test_fact_grounding_span_unparseable_defaults() -> None:
    out = fact_grounding_span(StubLLM("garbled response no score"), "src", "fact")
    assert out["score"] == 50.0
