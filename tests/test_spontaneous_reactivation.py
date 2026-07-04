"""Tests for the spontaneous reactivation stage in SleepEngine.

Property under test: stale skills (last_used_at older than the configured
min_age) get their last_used_at pushed forward by the rescue half-life,
which keeps them out of the decay/retirement reach for one more cycle.
"""
from __future__ import annotations

import time
from dataclasses import replace

import pytest

from engram import sleep as sleep_mod
from engram.config import CONFIG
from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory
from engram.semantic import SemanticMemory
from engram.skill import Skill, SkillLibrary
from engram.sleep import SleepEngine


@pytest.fixture
def stores(tmp_data_dir):
    skills = SkillLibrary(
        dir_path=tmp_data_dir / "skills",
        db_path=tmp_data_dir / "skills_index.db",
    )
    memory = EpisodicMemory(db_path=tmp_data_dir / "episodes.db")
    semantic = SemanticMemory(db_path=tmp_data_dir / "semantic.db")
    return skills, memory, semantic


@pytest.fixture
def reactivation_on(monkeypatch):
    new = replace(
        CONFIG,
        spontaneous_reactivation_enabled=True,
        spontaneous_reactivation_n=2,
        spontaneous_reactivation_min_age_s=24 * 3600.0,  # 1 day
        # Disable other stages so the test only exercises reactivation.
        sleep_min_episodes=0,
    )
    monkeypatch.setattr(sleep_mod, "CONFIG", new)


def _stale_skill(name: str, age_s: float) -> Skill:
    return Skill(
        name=name,
        trigger=f"trigger for {name}",
        body=f"body of {name}",
        status="promoted",
        trials=10, successes=8,
        last_used_at=time.time() - age_s,
    )


def test_stale_skills_get_last_used_at_advanced(stores, reactivation_on):
    skills, memory, semantic = stores
    old_a = _stale_skill("old_a", 30 * 24 * 3600.0)   # 30 days
    old_b = _stale_skill("old_b", 14 * 24 * 3600.0)   # 14 days
    young = _stale_skill("young", 1 * 3600.0)         # 1 hour
    for s in (old_a, old_b, young):
        skills.store(s)

    before = {s.id: s.last_used_at for s in skills.all()}

    engine = SleepEngine(memory=memory, skills=skills, semantic=semantic,
                         llm=None)
    engine._stage_spontaneous_reactivation(sleep_mod.SleepReport())

    after = {s.id: s.last_used_at for s in skills.all()}

    # The young skill must NOT have been touched (under the min_age threshold).
    assert after[young.id] == before[young.id]

    # Of the two stale skills, *at least one* (n=2 in fixture, both are
    # candidates so both will be picked) should have last_used_at moved
    # forward, but never to a value newer than `now`.
    now = time.time()
    moved = [
        sid for sid in (old_a.id, old_b.id)
        if after[sid] > before[sid]
    ]
    assert len(moved) >= 1
    for sid in moved:
        assert after[sid] < now, "rescued ts should still be 'in the past'"


def test_disabled_by_default_does_not_touch_skills(stores, monkeypatch):
    skills, memory, semantic = stores
    # Real CONFIG default: spontaneous_reactivation_enabled=False.
    # With min_episodes=0 so cycle() runs to completion instead of
    # bailing on "insufficient_episodes" before it reaches the dispatch.
    monkeypatch.setattr(
        sleep_mod, "CONFIG",
        replace(CONFIG, sleep_min_episodes=0),
    )
    # A skill old enough to be a reactivation candidate (default
    # min_age is 7 days; 30 days clears it). If the off-switch worked
    # only by accident this is exactly the skill that would get moved.
    old = _stale_skill("old", 30 * 24 * 3600.0)
    skills.store(old)
    before = skills.get(old.id).last_used_at

    engine = SleepEngine(memory=memory, skills=skills, semantic=semantic,
                         llm=None)
    # Drive the REAL off-switch: the stage is gated by the
    # `spontaneous_reactivation_enabled` flag at the cycle() dispatch
    # site, NOT inside the stage method. We must therefore exercise the
    # full cycle (calling the stage directly would bypass the guard and
    # always move the candidate, telling us nothing about the flag).
    engine.cycle()

    after = skills.get(old.id).last_used_at
    # Disabled-by-default contract: the candidate's last_used_at is left
    # EXACTLY as it was. This is falsifiable — if the dispatch guard at
    # sleep.py were dropped (or the flag default flipped to True), cycle()
    # would rescue this 30-day skill and `after` would jump forward to
    # ~now - decay_cutoff/2, breaking the equality. (Cross-checked
    # empirically: with the flag forced True, cycle() does move it.)
    assert after == before, (
        "disabled-by-default off-switch failed: cycle() moved a stale "
        f"skill ({after - before:+.0f}s) with reactivation disabled"
    )


def test_no_candidates_emits_skip(stores, reactivation_on):
    skills, memory, semantic = stores
    fresh = _stale_skill("fresh", 1.0)
    skills.store(fresh)

    engine = SleepEngine(memory=memory, skills=skills, semantic=semantic,
                         llm=None)
    n = engine._stage_spontaneous_reactivation(sleep_mod.SleepReport())
    assert n == 0


def test_retired_skills_are_excluded(stores, reactivation_on):
    skills, memory, semantic = stores
    retired_old = _stale_skill("retired_old", 30 * 24 * 3600.0)
    retired_old.status = "retired"
    skills.store(retired_old)

    engine = SleepEngine(memory=memory, skills=skills, semantic=semantic,
                         llm=None)
    n = engine._stage_spontaneous_reactivation(sleep_mod.SleepReport())
    assert n == 0
    assert (skills.get(retired_old.id).last_used_at
            == retired_old.last_used_at)


def test_high_fitness_skills_preferred_over_low(stores, reactivation_on):
    """Across many independent cycles, the high-fitness candidate should
    be chosen MORE OFTEN than the low-fitness one — fitness-weighted
    sampling, not uniform.

    We can't pin a deterministic order (the rng is involved), so we run
    1000 sample-once trials and check the empirical frequency.
    """
    skills, memory, semantic = stores
    high = _stale_skill("high_fit", 30 * 24 * 3600.0)
    high.successes = 19  # fitness ~0.95 (Beta(20, 2) mean = 0.91)
    high.trials = 20
    low = _stale_skill("low_fit", 30 * 24 * 3600.0)
    low.successes = 1     # fitness ~0.10 (Beta(2, 11) mean = 0.15)
    low.trials = 10
    skills.store(high)
    skills.store(low)

    # Force n=1 so each trial picks exactly one of the two.
    from dataclasses import replace as _dc_replace
    high_count = 0
    for seed in range(1000):
        # Reset last_used_at so both stay eligible across trials.
        h = skills.get(high.id)
        lo = skills.get(low.id)
        assert h is not None and lo is not None
        h.last_used_at = high.last_used_at
        lo.last_used_at = low.last_used_at
        skills.store(h)
        skills.store(lo)
        engine = SleepEngine(memory=memory, skills=skills, semantic=semantic,
                             llm=None, seed=seed)
        # Pick exactly one per trial via direct method call (bypass cycle).
        # We monkeypatch via temp CONFIG override on the module:
        original = sleep_mod.CONFIG
        sleep_mod.CONFIG = _dc_replace(
            sleep_mod.CONFIG,
            spontaneous_reactivation_n=1,
        )
        try:
            engine._stage_spontaneous_reactivation(sleep_mod.SleepReport())
        finally:
            sleep_mod.CONFIG = original

        # Whoever got rescued has a fresher last_used_at.
        h2 = skills.get(high.id)
        if h2.last_used_at != high.last_used_at:
            high_count += 1

    # With weights ~0.95 vs 0.15, P(high) ≈ 0.86 — the trial frequency
    # should land well above 0.6 (loose floor; binomial variance is ~0.01).
    assert high_count > 600, (
        f"high-fitness skill was picked only {high_count}/1000 times"
    )


def test_n_zero_bails_out_immediately(stores, monkeypatch):
    skills, memory, semantic = stores
    monkeypatch.setattr(
        sleep_mod, "CONFIG",
        replace(
            CONFIG,
            spontaneous_reactivation_enabled=True,
            spontaneous_reactivation_n=0,
            sleep_min_episodes=0,
        ),
    )
    old = _stale_skill("old", 30 * 24 * 3600.0)
    skills.store(old)
    before = skills.get(old.id).last_used_at

    engine = SleepEngine(memory=memory, skills=skills, semantic=semantic,
                         llm=None)
    n = engine._stage_spontaneous_reactivation(sleep_mod.SleepReport())
    assert n == 0
    assert skills.get(old.id).last_used_at == before
