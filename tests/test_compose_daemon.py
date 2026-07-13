"""TDD — the nightly composition daemon (the ORGANISM scheduler shell).

nightly_compose = P85 pre-flight -> compose_once(budget) -> P85 post-report.
The daemon REFUSES to compose when the self-write ratio already alarms: an
engine whose own output dominates the stream must not keep feeding on itself
(drift-invisibility, the exact P85 phase transition). Scheduling stays with
the OS (cron/Task Scheduler) — the module ships a one-shot CLI, local-first.
"""
from __future__ import annotations

import pytest

from engram.compose_daemon import nightly_compose


class _Judge:
    def complete(self, system, messages, **kw):
        class _R:  # noqa: N801
            text = "Score: 90"
        return _R()


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "claude")
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "0")
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "0")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    from engram.client import Memory
    return Memory(tmp_path / "daemon.db", grounding_llm=_Judge())


def test_normal_run_composes_and_reports_self_ratio(mem):
    mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    mem.add("A labrador is a dog.", topic="pets", verified_by=["source-doc:kb:t1"])
    rep = nightly_compose(mem, budget_candidates=10)
    assert rep["skipped_self_ratio"] is False
    assert rep["compose"]["admitted"] == 1
    assert 0.0 <= rep["self_ratio_pre"] < 0.5
    assert rep["self_ratio_post"] >= rep["self_ratio_pre"]   # we just self-wrote


def test_preflight_refuses_when_self_ratio_alarms(mem):
    """An engine already dominating its own stream must not keep composing."""
    mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    mem.add("A labrador is a dog.", topic="pets", verified_by=["source-doc:kb:t1"])
    for i in range(6):                       # engine floods: 6/8 = 0.75 > 0.5
        mem.add(f"Derived note {i} is a synthetic remark.", topic="derived",
                verified_by=[f"actor:composer:old{i}"])
    before = len(mem.semantic.all())
    rep = nightly_compose(mem, budget_candidates=10)
    assert rep["skipped_self_ratio"] is True
    assert rep["compose"] is None
    assert len(mem.semantic.all()) == before          # nothing was written


def test_budget_is_passed_down(mem):
    mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    mem.add("A labrador is a dog.", topic="pets", verified_by=["source-doc:kb:t1"])
    rep = nightly_compose(mem, budget_candidates=0)
    assert rep["compose"]["candidates"] == 0
    assert rep["compose"].get("truncated") is True    # bound declared, not silent


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
