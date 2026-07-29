"""Abstention is the product's headline claim, and it shipped off by default.

`env_floor()` calls ENGRAM_MIN_RELEVANCE "the single switch that turns 'knows
when it doesn't know' ON across every surface (SDK explain(), console,
gateway)", and returns 0.0 when it is unset — permissive. Nothing in the tree
sets it. So `Memory.explain()` answered every question, including the ones its
store cannot support, by handing back the nearest facts.

Measured on the live store 2026-07-29, ten questions, five supported and five
plausible inventions:

    gate OFF   0/5 abstentions   4/5 expected fact served   1.47s avg
    gate ON    4/5 abstentions   3/5 expected fact served   5.82s avg

Zero false abstentions in either column: the gate never withheld an answer the
store could support. That is what makes the default safe to flip — the cost is
latency on a deliberate custody check, not a wrong "I don't know".

The MCP surface was switched on first (a1f5e778), which left the two channels
disagreeing and made the docstring above false — the same split that let the
write moat run from the CLI and not from MCP. One switch, one behaviour.
"""
from __future__ import annotations

import pytest


def test_the_switch_defaults_to_the_calibrated_floor(monkeypatch) -> None:
    monkeypatch.delenv("ENGRAM_MIN_RELEVANCE", raising=False)
    from verimem.relevance_floor import env_floor
    assert env_floor() == "auto", (
        "unset means the product's headline behaviour is off for every SDK "
        "caller, while the MCP surface abstains — one store, two answers"
    )


@pytest.mark.parametrize("raw,expected", [
    ("off", 0.0),
    ("0", 0.0),
    ("0.35", 0.35),
    ("auto", "auto"),
])
def test_an_explicit_value_still_wins(monkeypatch, raw, expected) -> None:
    """Turning a default ON must not take away the switch. Whoever set a float
    (or off) keeps exactly what they asked for."""
    monkeypatch.setenv("ENGRAM_MIN_RELEVANCE", raw)
    from verimem.relevance_floor import env_floor
    assert env_floor() == expected


def test_a_hostile_value_does_not_abstain_on_everything(monkeypatch) -> None:
    """An infinite floor would refuse every query ever asked; nan would compare
    False forever. Both were live bugs in this family (env_num, 2026-07-28)."""
    from verimem.relevance_floor import env_floor
    for raw in ("inf", "nan", "-inf", "abc"):
        monkeypatch.setenv("ENGRAM_MIN_RELEVANCE", raw)
        v = env_floor()
        assert v == "auto" or (isinstance(v, float) and 0.0 <= v < 1e6), (
            f"{raw!r} resolved to {v!r}"
        )
