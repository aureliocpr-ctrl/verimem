"""Stuck-candidate diagnostic — TDD coverage."""
from __future__ import annotations

import os
from dataclasses import dataclass

import pytest

os.environ.setdefault("HIPPO_OFFLINE", "1")
os.environ.setdefault("HIPPO_HOSTED", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


@dataclass
class _S:
    id: str
    name: str = ""
    status: str = "candidate"
    trials: int = 0
    created_at: float = 0.0


def test_summary_aggregates_status_counts():
    from engram.skill_stuck_diagnostic import stuck_candidates_report
    skills = [
        _S("p1", status="promoted", trials=10),
        _S("p2", status="promoted", trials=20),
        _S("c1", status="candidate", trials=0, created_at=0),
        _S("c2", status="candidate", trials=5),
        _S("r1", status="retired", trials=10),
    ]
    out = stuck_candidates_report(skills, now_ts=1_000_000.0, min_age_days=7.0)
    s = out["summary"]
    assert s["candidate_total"] == 2
    assert s["candidate_trials_0"] == 1
    assert s["promoted_total"] == 2
    assert s["retired_total"] == 1


def test_only_aged_candidates_are_flagged():
    """A candidate younger than min_age_days must NOT appear."""
    from engram.skill_stuck_diagnostic import stuck_candidates_report
    now = 2_000_000_000.0           # ~2033 — keeps subtraction positive
    old = now - 14 * 86400          # 14 days ago
    fresh = now - 2 * 86400         # 2 days ago
    skills = [
        _S("aged",  status="candidate", trials=0, created_at=old),
        _S("fresh", status="candidate", trials=0, created_at=fresh),
    ]
    out = stuck_candidates_report(skills, now_ts=now, min_age_days=7.0)
    assert out["summary"]["candidate_trials_0_aged"] == 1
    ids = [x["id"] for x in out["stuck_skills"]]
    assert ids == ["aged"]


def test_candidates_with_trials_not_flagged():
    from engram.skill_stuck_diagnostic import stuck_candidates_report
    now = 2_000_000_000.0
    old = now - 30 * 86400
    skills = [_S("trying", status="candidate", trials=4, created_at=old)]
    out = stuck_candidates_report(skills, now_ts=now, min_age_days=7.0)
    assert out["summary"]["candidate_trials_0_aged"] == 0
    assert out["stuck_skills"] == []


def test_catch_22_fraction_computation():
    from engram.skill_stuck_diagnostic import stuck_candidates_report
    now = 2_000_000_000.0
    old = now - 14 * 86400
    skills = [
        _S(f"aged_{i}", status="candidate", trials=0, created_at=old)
        for i in range(8)
    ] + [
        _S(f"trying_{i}", status="candidate", trials=5)
        for i in range(2)
    ]
    out = stuck_candidates_report(skills, now_ts=now, min_age_days=7.0)
    assert out["summary"]["candidate_total"] == 10
    assert out["summary"]["candidate_trials_0_aged"] == 8
    assert out["summary"]["catch_22_fraction"] == 0.8


def test_top_k_caps_listing():
    from engram.skill_stuck_diagnostic import stuck_candidates_report
    now = 2_000_000_000.0
    skills = [
        _S(f"s{i}", status="candidate", trials=0, created_at=now - (10 + i) * 86400)
        for i in range(20)
    ]
    out = stuck_candidates_report(skills, now_ts=now, min_age_days=7.0, top_k=5)
    assert len(out["stuck_skills"]) == 5
    ages = [x["age_days"] for x in out["stuck_skills"]]
    assert ages == sorted(ages, reverse=True)


def test_skilllibrary_corpus_reveals_catch_22():
    """End-to-end: a real SkillLibrary populated with a catch-22 corpus
    must surface a high (>0.5) catch_22_fraction via the diagnostic.

    Why not the *real* ~/.engram DB?  The autouse `_isolate_test_env`
    fixture (tests/conftest.py) pins HIPPO_DATA_DIR to an empty per-test
    tmp dir, so `SkillLibrary()` under pytest always reads an EMPTY skills
    DB.  The previous version of this test therefore hit
    `candidate_total == 0` and `pytest.skip(...)` on *every* isolated run
    — an always-true skip masquerading as conditional coverage: the
    assert never executed.

    Fix: build the catch-22 condition deterministically through the actual
    SkillLibrary.store()/all() path (against the isolated tmp DB), so the
    integration SkillLibrary -> stuck_candidates_report is genuinely
    exercised, with no dependency on external mutable state.
    """
    from engram.skill import Skill, SkillLibrary
    from engram.skill_stuck_diagnostic import stuck_candidates_report

    now = 2_000_000_000.0
    aged = now - 14 * 86400          # 14 days old → counts as aged at min_age_days=7
    lib = SkillLibrary()             # isolated tmp skills DB (conftest)
    # 8 aged candidates with zero trials = the catch-22 (never retrieved,
    # so never tried, so never promoted, so never retired).
    for i in range(8):
        lib.store(Skill(id=f"stuck_{i}", status="candidate", trials=0, created_at=aged))
    # 2 candidates that *did* get trials → not stuck. Plus terminal-state
    # noise that must be excluded from the candidate denominator.
    for i in range(2):
        lib.store(Skill(id=f"trying_{i}", status="candidate", trials=5, created_at=aged))
    lib.store(Skill(id="prom", status="promoted", trials=12, created_at=aged))
    lib.store(Skill(id="ret", status="retired", trials=9, created_at=aged))

    out = stuck_candidates_report(lib.all(), now_ts=now, min_age_days=7.0, top_k=10)
    s = out["summary"]
    assert s["candidate_total"] == 10           # promoted/retired excluded
    assert s["candidate_trials_0_aged"] == 8
    assert s["catch_22_fraction"] == 0.8        # 8/10
    assert s["catch_22_fraction"] > 0.5, (
        f"catch_22_fraction={s['catch_22_fraction']:.3f}; expected >0.5 — "
        f"the diagnostic failed to surface the seeded catch-22 corpus."
    )
