"""answer_question_grounded: the validated provenance-conditioning mechanism wired into
the reusable answer path. Hermetic (capturing stub LLM) — asserts the grounding tags +
floor reach the prompt; the behavioral win is proven in benchmark/grounding_conditioned_qa.py.
"""
from __future__ import annotations

import types

from benchmark.qa_eval import answer_question_grounded


class _CapLLM:
    def __init__(self):
        self.system = None
        self.user = None

    def complete(self, system, messages, *, model=None, max_tokens=None):
        self.system = system
        self.user = messages[-1]["content"]
        return types.SimpleNamespace(text="ok")


def test_scored_facts_are_tagged_unscored_are_plain():
    llm = _CapLLM()
    answer_question_grounded(llm, "q?", [("grounded fact", 90.0), ("plain fact", None),
                                         ("weak fact", 12.0)])
    assert "[grounding 90/100] grounded fact" in llm.user
    assert "[grounding 12/100] weak fact" in llm.user
    assert "plain fact" in llm.user and "[grounding" not in llm.user.split("plain fact")[0].rsplit("\n", 1)[-1]


def test_floor_is_injected_into_system_prompt():
    llm = _CapLLM()
    answer_question_grounded(llm, "q?", [("f", 90.0)], floor=55.0)
    assert "reliability floor of 55" in llm.system


def test_returns_model_text():
    llm = _CapLLM()
    out = answer_question_grounded(llm, "q?", [("f", 90.0)])
    assert out == "ok"
