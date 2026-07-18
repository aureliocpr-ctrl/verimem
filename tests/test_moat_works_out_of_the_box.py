"""The README quickstart's central claim, verified for a user WITHOUT an llm.

README "THE MOAT, live — the reason Verimem exists":
    m.add("Analytics runs on Postgres.", source=src)   # entailed  -> admitted
    r = m.add("Analytics runs on MongoDB.", source=src)  # confab   -> QUARANTINED
    assert r["status"] == "quarantined"

A brand-new user has no llm to pass. The moat MUST still work off the free local
cross-encoder (a core dependency, AUROC ~1.0 on this judgement) — otherwise the
documented quickstart raises AssertionError on first run.

Two bugs this pins (2026-07-18):
  1. default judge backend was "claude" (needs an injected llm) -> with none the
     gate fail-opened and admitted the confab.
  2. the direct-write CE path used the model's shipped gate_config threshold
     (99.641 — absurdly high) instead of a sane entailment cut, so it quarantined
     the TRUE fact too (Postgres, score 99.57).
"""
import tempfile
from pathlib import Path

from verimem.client import Memory


def _mem():
    return Memory(str(Path(tempfile.mkdtemp()) / "memory.db"))  # NO llm — like a new user


def test_readme_moat_quickstart_without_llm():
    m = _mem()
    src = "We migrated the analytics store to Postgres last quarter."
    a = m.add("Analytics runs on Postgres.", source=src)   # entailed
    r = m.add("Analytics runs on MongoDB.", source=src)    # confab
    # the confab must be quarantined — the exact README assertion
    assert r["status"] == "quarantined", f"moat did not fire: MongoDB status={r['status']!r}"
    # and the TRUE fact must NOT be quarantined by an over-tight threshold
    assert a["status"] != "quarantined", f"moat over-quarantined the true fact: {a['status']!r}"


def test_moat_admits_a_second_entailed_fact_without_llm():
    # guard against "just lower the threshold to 0" — a genuinely entailed but
    # differently-worded fact should still be admitted, a real confab rejected.
    m = _mem()
    src = "The Q3 revenue was 4.2 million euros, up from 3.1 million in Q2."
    ok = m.add("Q3 revenue reached 4.2 million euros.", source=src)   # entailed
    bad = m.add("Q3 revenue collapsed to zero.", source=src)          # confab
    assert ok["status"] != "quarantined", f"entailed fact quarantined: {ok['status']!r}"
    assert bad["status"] == "quarantined", f"confab admitted: {bad['status']!r}"
