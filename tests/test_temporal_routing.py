"""History routing (`wants_history` + `Memory.search(with_history="auto")`).

The measured trade (docs/TRUST_MAINTENANCE.md): always-on history context
lifts transition questions +16pp but costs abstention purity on trap
questions (1.000 -> 0.949). The cure is routing — the story only where the
query's wording is temporal. EN+IT (G10: the router must not be EN-only).
Hermetic, no LLM.
"""
from __future__ import annotations

import time

import pytest

from engram.temporal_context import wants_history

_TEMPORAL = [
    "What was the budget as of March 2026?",
    "When did Johnson move to Milan?",
    "Did his income change after the layoff?",
    "Is he still working at Albi B&B?",
    "What is his current job title?",
    "What did she prefer before the update?",
    "Where did he live in 2024?",
    "His preference used to be thrillers, right?",
    # italiano
    "Quando ha cambiato lavoro?",
    "Qual è il suo stipendio attuale?",
    "Dove viveva prima di trasferirsi?",
    "È ancora vegetariano?",
    "Cosa è successo a marzo?",
]

_PLAIN = [
    "What is Johnson's MBTI type?",
    "Where does Martin Mark live?",
    "What is the middle name of Johnson Joseph?",
    "Which pets does he own?",
    "What's the capital of the project budget line?",
    # italiano
    "Qual è il suo tipo MBTI?",
    "Dove abita Martin?",
    "Come si chiama il suo gatto?",
]


@pytest.mark.parametrize("q", _TEMPORAL)
def test_temporal_queries_route_to_history(q: str) -> None:
    assert wants_history(q) is True, q


@pytest.mark.parametrize("q", _PLAIN)
def test_plain_lookups_stay_lean(q: str) -> None:
    assert wants_history(q) is False, q


def test_empty_and_none_are_lean() -> None:
    assert wants_history("") is False
    assert wants_history(None) is False  # type: ignore[arg-type]


def test_sdk_auto_routes_per_query(tmp_path) -> None:
    """with_history='auto': a temporal question carries the transition story,
    a plain lookup does not — same store, same API call shape."""
    from engram.client import Memory
    from engram.semantic import Fact

    mem = Memory(tmp_path / "r.db")
    now = time.time()
    day = 86400.0
    mem.semantic.store(Fact(id="roma", topic="user/home",
                            proposition="User lives in Rome",
                            asserted_at=now - 400 * day), embed="sync")
    mem.semantic.store(Fact(id="milano", topic="user/home",
                            proposition="User lives in Milan",
                            asserted_at=now - 10 * day), embed="sync")
    mem.semantic.supersede("roma", "milano", reason="moved")

    temporal = mem.search("When did the user move to Milan?", k=3,
                          with_history="auto")
    assert temporal and any("history" in h and h["history"] for h in temporal), \
        "temporal wording must carry the transition story"

    plain = mem.search("Which city?", k=3, with_history="auto")
    assert plain and all("history" not in h for h in plain), \
        "plain lookup stays lean (no history key at all)"

    # explicit booleans keep their exact pre-'auto' behaviour
    forced = mem.search("Which city?", k=3, with_history=True)
    assert any("history" in h for h in forced)
    off = mem.search("When did he move?", k=3, with_history=False)
    assert all("history" not in h for h in off)
