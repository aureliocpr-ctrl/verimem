"""Read-side "must not pass": on a query the store CANNOT support, abstain — do
NOT return the nearest-but-wrong fact. Measured 2026-07-18: with only an
off-topic fact, `explain(min_relevance="auto")` returned it (bi-encoder cosine
0.71; the "auto" floor collapses to 0.0 on a near-empty store). The CE relevance
gate (logit floor 0.0) fixes it store-size-independently — the CE scores the
off-topic fact ~-8 and the on-topic one ~+8. Skips if the reranker model isn't
installed (CE-dependent, like the moat tests).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


def _reranker_or_skip():
    from verimem import semantic
    try:
        if semantic._load_reranker() is None:
            pytest.skip("cross-encoder reranker model not installed")
    except Exception:  # noqa: BLE001
        pytest.skip("cross-encoder reranker unavailable")


def _mem():
    from verimem.client import Memory
    return Memory(str(Path(tempfile.mkdtemp()) / "m.db"))


def test_abstains_on_unsupported_query_even_on_a_tiny_store():
    _reranker_or_skip()
    m = _mem()
    m.add("The office coffee machine was serviced on Tuesday.",
          verified_by=["ops:log"])
    rep = m.explain("what database does the analytics service run on?",
                    min_relevance="auto")
    assert rep.get("abstained") is True, f"did not abstain: {rep.get('facts')}"
    blob = str(rep.get("facts") or []).lower()
    assert "coffee" not in blob, "off-topic fact leaked into the dossier"


def test_answers_when_supported_no_over_abstention():
    _reranker_or_skip()
    m = _mem()
    m.add("The office coffee machine was serviced on Tuesday.", verified_by=["ops:log"])
    m.add("The analytics service runs on Postgres.",
          source="We migrated analytics to Postgres.")
    rep = m.explain("what database does the analytics service run on?",
                    min_relevance="auto")
    assert rep.get("abstained") is not True, "over-abstained on a supported query"
    assert "postgres" in str(rep.get("facts") or []).lower()


def test_permissive_recall_is_still_available_on_request():
    """Renamed and inverted on 2026-07-29, deliberately.

    This used to assert that the DEFAULT stays permissive — that asking "what
    database does analytics run on?" of a store which only knows about the
    coffee machine returns the coffee machine. That is the very example this
    file's docstring calls a "must not pass", and the same one the CE gate was
    built for (measured 2026-07-18: bi-encoder 0.71, CE -8.7). The product knew
    the answer was wrong, had the gate to stop it, and defaulted to shipping it
    for backward compatibility.

    The default now abstains (env_floor unset -> "auto"). What still has to hold
    — and is what this test now guards — is that anyone depending on the old
    behaviour can ask for it and get it exactly.
    """
    import os

    _reranker_or_skip()
    m = _mem()
    m.add("The office coffee machine was serviced on Tuesday.", verified_by=["ops:log"])

    _prev = os.environ.get("ENGRAM_MIN_RELEVANCE")
    os.environ["ENGRAM_MIN_RELEVANCE"] = "off"
    try:
        rep = m.explain("what database does analytics run on?")
        assert rep.get("facts"), (
            "ENGRAM_MIN_RELEVANCE=off must restore permissive recall for "
            "callers who depend on it"
        )
    finally:
        if _prev is None:
            os.environ.pop("ENGRAM_MIN_RELEVANCE", None)
        else:
            os.environ["ENGRAM_MIN_RELEVANCE"] = _prev


def test_the_default_now_declines_the_nearest_but_wrong_fact():
    """The other half: the behaviour this file's docstring asks for is now what
    you get without configuring anything."""
    _reranker_or_skip()
    m = _mem()
    m.add("The office coffee machine was serviced on Tuesday.", verified_by=["ops:log"])
    rep = m.explain("what database does analytics run on?")
    assert not rep.get("facts"), (
        f"served the coffee machine for a database question: {rep.get('facts')}"
    )
    assert rep.get("abstained") is True
