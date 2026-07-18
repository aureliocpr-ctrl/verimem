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


def test_ce_gate_off_when_abstention_not_requested():
    # default explain (no min_relevance) must NOT abstain via the CE gate — the
    # gate is opt-in with abstention, preserving backward-compatible permissive
    # recall.
    _reranker_or_skip()
    m = _mem()
    m.add("The office coffee machine was serviced on Tuesday.", verified_by=["ops:log"])
    rep = m.explain("what database does analytics run on?")  # no floor requested
    assert rep.get("facts"), "default explain should stay permissive (no CE gate)"
