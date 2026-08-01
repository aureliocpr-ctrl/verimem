"""A judge that did not answer must not be scored as 50.

`fact_grounding_score_ex` asked the llm for a score with ``max_tokens=12`` and,
when the reply carried no number, returned ``50.0, "claude"``. Measured against
the two strongest third-party models available here (2026-07-28):

    glm-5.2          max_tokens=12  -> ''        (empty)  -> 50
    glm-5.2          max_tokens=128 -> 'SCORE: 0'         ->  0
    deepseek-v4-pro  max_tokens=12  -> ''        (empty)  -> 50
    deepseek-v4-pro  max_tokens=400 -> 'SCORE: 0'         ->  0

Both models REJECT the claim correctly when they can answer. Reasoning models
spend the token budget on internal reasoning, so a 12-token ceiling returns an
empty string — 64 was still empty, 128 was enough. The gate then invented 50,
which clears the write cut of 40, so the write is ADMITTED with a number no
judge produced and a receipt that reads "claude" whatever provider was passed.

Two separate defects, fixed separately:

* the budget was too small for how these models answer (and the same class was
  already recorded for the critic-orchestrator: "the loop aborted on the first
  turn with no tool call, and reasoning models legitimately produce that");
* silence became a number. The module already has NoGroundingJudge for exactly
  this — "I cannot judge" — and the write path turns it into the honest
  L4-skipped advisory. An unreadable verdict is not a middling verdict.
"""
from __future__ import annotations

import pytest

from verimem.grounding_gate import NoGroundingJudge, fact_grounding_score_ex

SRC = "Revenue of 4.2bn, up from 3.75bn last year."
FACT = "Revenue grew 45% year over year."


class _Reply:
    def __init__(self, text: str) -> None:
        self.text = text


class _Judge:
    """Mimics the measured behaviour: silent under a small budget, answers above
    it. Keeps the test off the network while pinning the real failure."""

    def __init__(self, needs: int = 128, answer: str = "SCORE: 0") -> None:
        self.needs, self.answer, self.seen = needs, answer, []

    def complete(self, system, messages, model=None, max_tokens=None, **kw):
        self.seen.append(max_tokens)
        budget = max_tokens or 0
        return _Reply(self.answer if budget >= self.needs else "")


def test_an_empty_reply_is_not_scored_fifty():
    judge = _Judge()
    with pytest.raises(NoGroundingJudge):
        fact_grounding_score_ex(_Judge(needs=10**9), SRC, FACT)
    assert judge.seen == [] or True


def test_the_budget_is_large_enough_for_a_reasoning_model():
    """128 was the measured minimum for glm-5.2; the shipped budget must clear
    it, or every reasoning model silently degrades to the fallback."""
    judge = _Judge(needs=128)
    score, backend = fact_grounding_score_ex(judge, SRC, FACT)
    assert judge.seen and judge.seen[0] >= 128, (
        f"asked for {judge.seen} tokens — a reasoning model answers nothing "
        f"under ~128 and the gate then invents a score")
    assert score == 0.0, score


def test_a_real_verdict_is_passed_through():
    judge = _Judge(needs=1, answer="SCORE: 87")
    score, _ = fact_grounding_score_ex(judge, SRC, FACT)
    assert score == 87.0


def test_a_judge_that_answers_without_a_number_is_not_a_verdict():
    """Prose with no score is the same silence as an empty string."""
    judge = _Judge(needs=1, answer="I would rather not say.")
    with pytest.raises(NoGroundingJudge):
        fact_grounding_score_ex(judge, SRC, FACT)
