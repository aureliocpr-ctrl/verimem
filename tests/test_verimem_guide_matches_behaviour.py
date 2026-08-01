"""The onboarding guide must promise exactly what the write path delivers.

`agent_guide.VERIMEM_AGENT_GUIDE` is returned in the MCP `initialize` response,
so it is the FIRST thing every connecting agent reads and the basis on which it
decides how to call the tools. Two of its sentences were wider than the measured
behaviour (banco 6, 2026-07-28):

* "facts pass a grounding gate (the moat) before they count as truth, so you
  never recall a confabulation" — the entailment moat needs the source TEXT to
  check against. Without one it does not run, and the fact is stored as an
  unverified model_claim. Measured: a blatant confabulation written with no
  source is admitted, grounding_score None.
* "pass a `source` (or `verified_by`)" — reads as if the two were alternatives
  for the moat. They are not: `verified_by` records WHO vouches, the moat needs
  WHAT the source says. Measured: verified_by alone leaves grounding_score None.

The gate is strong where it runs — the same store separates an entailed fact at
97.8 from a contradicted one at 0.25 — which is why the promise should describe
its actual perimeter instead of a wider one.

These tests bind the prose to the behaviour: each asserts what the write path
DOES and then that the guide says so. If the write path ever changes, the guide
cannot silently stay behind.
"""
from __future__ import annotations

import pytest

from verimem.agent_guide import VERIMEM_AGENT_GUIDE

CONFAB = ("The Anthropic Q3 2027 revenue was exactly 4.7 billion dollars "
          "according to the audited filing.")


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "0")
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "0")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    from verimem.client import Memory
    return Memory(tmp_path / "g.db")


def test_a_write_without_a_source_is_not_entailment_checked(mem):
    """The behaviour the guide has to describe."""
    res = mem.add(CONFAB, topic="w")
    assert res["grounding_score"] is None, (
        "the moat has nothing to check a fact against without a source")
    assert res["status"] != "quarantined", "and the fact is admitted"


def test_verified_by_alone_does_not_run_the_moat(mem):
    """`verified_by` names WHO vouches; the moat needs WHAT the source says."""
    res = mem.add(CONFAB, topic="w", verified_by=["source-doc:auditor:t1"])
    assert res["grounding_score"] is None


def test_a_source_that_contradicts_is_quarantined(mem):
    """Where it runs, it runs hard — the promise is worth stating precisely."""
    res = mem.add(CONFAB, topic="w",
                  source="The company published a blog post about hiring "
                         "engineers in Dublin.")
    assert res["status"] == "quarantined"
    assert res["grounding_score"] is not None and res["grounding_score"] < 40


def test_the_guide_states_that_a_source_is_what_runs_the_moat():
    guide = VERIMEM_AGENT_GUIDE.lower()
    assert "without a source" in guide, (
        "the guide must say what happens with no source — it is the common case")
    assert "verified_by" in guide and "does not run" in guide, (
        "the guide must not present verified_by as an alternative that grounds")


def test_the_guide_does_not_claim_confabulations_can_never_be_recalled():
    """A promise no write path can keep for unsourced writes."""
    guide = VERIMEM_AGENT_GUIDE.lower()
    assert "never recall a confabulation" not in guide
