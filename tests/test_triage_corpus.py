"""triage_corpus + quarantine_fact: the consolidation-time Tier-2 pass. On a DECLASS
verdict a specific-unsourced fact is quarantined (reversible); sourced / non-specific /
already-quarantined facts are skipped; KEEP/dry-run leave the corpus untouched. Hermetic —
tmp SemanticMemory + FixedJudge (no LLM)."""
from __future__ import annotations

import tempfile
from pathlib import Path

from engram.semantic import Fact, SemanticMemory
from engram.tier2_judge import FixedJudge, JudgeAction, JudgeVerdict, triage_corpus


def _mem():
    tmp = Path(tempfile.mkdtemp(prefix="triage_"))
    return SemanticMemory(db_path=tmp / "semantic" / "semantic.db")


def _seed(sm):
    # specific + unsourced -> the judge bucket
    sm.store(Fact(proposition="The cache holds 1024 entries.", topic="infra",
                  confidence=0.8), embed="sync")
    # non-specific -> skipped (no quantity)
    sm.store(Fact(proposition="The user likes tea.", topic="prefs", confidence=0.8),
             embed="sync")
    # specific but SOURCED -> skipped (evidence beats opinion)
    sm.store(Fact(proposition="The build uses Python 3.13.", topic="infra",
                  confidence=0.9, verified_by=["file:pyproject.toml:1"]), embed="sync")


def test_quarantine_fact_roundtrip():
    sm = _mem()
    r = sm.store(Fact(proposition="The TTL is 300 seconds.", topic="t"), embed="sync")
    fid = r if isinstance(r, str) else r.id if hasattr(r, "id") else None
    # find the stored fact id
    fid = sm.all()[0].id
    assert sm.quarantine_fact(fid) is True
    assert sm.get(fid).status == "quarantined"
    assert sm.quarantine_fact(fid) is False  # idempotent no-op
    assert sm.quarantine_fact("nonexistent") is False


def test_cap_is_surfaced_not_silent():
    """max_judged / corpus limit must be SURFACED (candidates_pending, corpus_truncated) so a
    partial pass is never read as 'whole corpus reviewed' (adversarial-review hole #7)."""
    sm = _mem()
    for i in range(5):
        sm.store(Fact(proposition=f"The widget count is {i + 10}.", topic="t"), embed="sync")
    from engram.tier2_judge import FixedJudge, JudgeAction, JudgeVerdict, triage_corpus
    keep = FixedJudge(JudgeVerdict(JudgeAction.KEEP, "x"))  # judge keeps; check accounting
    res = triage_corpus(sm, keep, apply=False, max_judged=2, min_corroborations=99)
    assert res["reviewed"] == 2  # only 2 judged this pass
    assert res["candidates"] >= 5  # all eligible specific-unsourced facts counted
    assert res["candidates_pending"] == res["candidates"] - 2  # backlog surfaced, not dropped


def test_quarantine_then_restore_roundtrip():
    sm = _mem()
    sm.store(Fact(proposition="The pool size is 32.", topic="t"), embed="sync")
    fid = sm.all()[0].id
    assert sm.quarantine_fact(fid) is True
    assert sm.get(fid).status == "quarantined"
    # reversible: restore brings it back to the live view
    assert sm.restore_fact(fid) is True
    assert sm.get(fid).status == "model_claim"
    # only quarantined rows restore (idempotent / guarded)
    assert sm.restore_fact(fid) is False
    assert sm.restore_fact("nonexistent") is False


def test_declass_quarantines_only_the_ambiguous_bucket():
    sm = _mem()
    _seed(sm)
    judge = FixedJudge(JudgeVerdict(JudgeAction.DECLASS, "noise", 0.7))
    res = triage_corpus(sm, judge, apply=True)
    assert res["reviewed"] == 1  # only the specific-unsourced fact reaches the judge
    assert res["declassed"] == 1
    statuses = {f.proposition: f.status for f in sm.all()}
    assert statuses["The cache holds 1024 entries."] == "quarantined"
    assert statuses["The user likes tea."] != "quarantined"   # non-specific skipped
    assert statuses["The build uses Python 3.13."] != "quarantined"  # sourced skipped


def test_keep_leaves_corpus_untouched():
    sm = _mem()
    _seed(sm)
    judge = FixedJudge(JudgeVerdict(JudgeAction.KEEP, "keep", 0.5))
    res = triage_corpus(sm, judge, apply=True)
    assert res["reviewed"] == 1 and res["declassed"] == 0
    assert all(f.status != "quarantined" for f in sm.all())


def test_dry_run_counts_but_does_not_mutate():
    sm = _mem()
    _seed(sm)
    judge = FixedJudge(JudgeVerdict(JudgeAction.DECLASS, "noise", 0.7))
    res = triage_corpus(sm, judge, apply=False)
    assert res["declassed"] == 1 and res["applied"] is False
    assert all(f.status != "quarantined" for f in sm.all())  # no mutation
