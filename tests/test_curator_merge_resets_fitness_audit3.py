"""audit#3-r3 R12: SleepEngine._merge carried over the SUM of both parents'
trials + successes onto the merged skill. The merged BODY is a brand-new
LLM-generated artifact that has NEVER been executed, yet it inherited a passing
track record — so the promotion gate (success_rate + min_trials) could
auto-promote an untested skill. A merged skill must start untested and earn
promotion through its OWN trials (the same way _recombine already does).
"""
from __future__ import annotations

from engram.skill import Skill
from engram.sleep import SleepEngine


class _Resp:
    def __init__(self, text: str) -> None:
        self.text = text
        self.total_tokens = 7


class _StubLLM:
    def complete(self, *a, **k):
        return _Resp(
            '{"name": "merged skill", "trigger": "t", '
            '"body": "combined body", "rationale": "r"}'
        )


def test_curator_merge_resets_fitness_to_untested():
    a = Skill(name="A", trigger="xa", body="ba", trials=12, successes=11)
    b = Skill(name="B", trigger="yb", body="bb", trials=10, successes=9)

    # _merge only touches self.llm + module-level helpers, so bypass __init__.
    eng = object.__new__(SleepEngine)
    eng.llm = _StubLLM()
    merged, toks = eng._merge(a, b)

    assert merged is not None
    assert merged.trials == 0, f"merged inherited parent trials: {merged.trials}"
    assert merged.successes == 0, (
        f"merged inherited parent successes: {merged.successes}"
    )
    # Lineage is still recorded; only the fitness is reset.
    assert a.id in merged.parent_skills and b.id in merged.parent_skills
    assert toks == 7
