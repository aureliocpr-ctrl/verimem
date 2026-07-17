"""dedup_skills_by_name must not silently swallow store() failures (scan #29).

The apply branch wrapped get/store in ``except Exception: pass`` — a
store() that failed (disk, lock, validation) was discarded silently, so
``applied_retired`` quietly under-counted and the operator believed N
skills were retired when fewer were. Silent failure on a write path.

Contract: a store() that raises is COUNTED (applied_failed) and logged,
not swallowed; the success count still reflects only real retirements.
"""
from __future__ import annotations

import logging
from types import SimpleNamespace

from verimem import skill_name_dedup as mod


class _FakeStore:
    """N skills sharing a name; store() raises for one loser id."""

    def __init__(self, skills):
        self._skills = {s.id: s for s in skills}
        self.fail_id = None

    def all(self):
        return list(self._skills.values())

    def get(self, sid):
        return self._skills.get(sid)

    def store(self, s):
        if s.id == self.fail_id:
            raise RuntimeError("simulated disk/lock failure on store()")
        self._skills[s.id] = s


def _skill(sid, name, trials):
    # status="candidate": dedup_skills_by_name's default only_status filter.
    return SimpleNamespace(id=sid, name=name, status="candidate",
                           trials=trials, successes=trials, created_at=0.0)


def test_store_failure_is_counted_and_logged(caplog):
    skills = [
        _skill("win", "dup name", 10),
        _skill("lose1", "dup name", 1),
        _skill("lose2", "dup name", 1),
    ]
    store = _FakeStore(skills)
    store.fail_id = "lose1"  # one retirement will raise

    with caplog.at_level(logging.WARNING, logger="verimem.skill_name_dedup"):
        out = mod.dedup_skills_by_name(store, apply=True, max_retire=10)

    assert out["applied_failed"] == 1, (
        "a store() that raised must be counted, not swallowed"
    )
    assert out["applied_retired"] == 1, (
        "only the genuinely-retired loser counts as applied"
    )
    assert any("dedup retire failed" in r.getMessage() for r in caplog.records), (
        "the swallowed failure must now be logged"
    )
