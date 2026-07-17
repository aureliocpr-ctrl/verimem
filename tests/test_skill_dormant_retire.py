"""Ritiro dormancy-based delle candidate-zombie (qualità skill #5, gamba B).

Gap misurato: ``promote_or_retire`` salta le skill con ``trials <
min_trials`` — una candidate MAI provata non viene mai né promossa né
ritirata e resta attiva per sempre (corpus vivo: 162/324 candidate, molte a
trials=0 da settimane), pagando retrieve/dedup/cluster a ogni ciclo. Il
decadimento d'uso esisteva solo come report manuale (skill_usage_decay).

Fix: ``retire_dormant_candidates`` — candidate sotto ``min_trials`` la cui
ultima attività (last_used_at, fallback created_at) è più vecchia di
``max_age_days`` vanno ``retired`` (REVERSIBILE: status recuperabile, come
ogni retire), con cap conservativo per ciclo. Cablata in ``_stage_pruning``.
"""
from __future__ import annotations

import time

from verimem.skill import Skill, SkillLibrary

DAY = 86400.0


def _mk(lib: SkillLibrary, name: str, *, age_days: float, trials: int = 0,
        used_days_ago: float | None = None, status: str = "candidate") -> Skill:
    now = time.time()
    s = Skill(name=name, trigger=f"trigger {name}", body="b", rationale="r",
              stage="rem")
    s.status = status
    s.trials = trials
    lib.store(s)
    # Backdate in tabella: l'ultima attività persistita è updated_at (ogni
    # uso passa da update_fitness->store); last_used_at NON è una colonna.
    import sqlite3
    conn = sqlite3.connect(lib.db_path)
    used_at = now - (used_days_ago * DAY if used_days_ago is not None
                     else age_days * DAY)
    conn.execute("UPDATE skills SET created_at = ?, updated_at = ? WHERE id = ?",
                 (now - age_days * DAY, used_at, s.id))
    conn.commit()
    conn.close()
    return s


def test_dormant_untried_candidate_is_retired(tmp_path):
    lib = SkillLibrary(db_path=tmp_path / "skills.db")
    zombie = _mk(lib, "zombie", age_days=60, trials=0)
    fresh = _mk(lib, "fresh", age_days=3, trials=0)
    retired = lib.retire_dormant_candidates(max_age_days=30)
    assert zombie.id in retired
    assert lib.get(zombie.id).status == "retired"
    assert fresh.id not in retired, "una candidate fresca resta in prova"
    assert lib.get(fresh.id).status == "candidate"


def test_recently_used_candidate_survives(tmp_path):
    lib = SkillLibrary(db_path=tmp_path / "skills.db")
    active = _mk(lib, "old-but-active", age_days=90, trials=1,
                 used_days_ago=2)
    retired = lib.retire_dormant_candidates(max_age_days=30)
    assert active.id not in retired, (
        "l'uso recente azzera la dormienza anche se la skill è vecchia"
    )


def test_promoted_skills_are_never_touched(tmp_path):
    lib = SkillLibrary(db_path=tmp_path / "skills.db")
    star = _mk(lib, "star", age_days=120, trials=8, status="promoted")
    retired = lib.retire_dormant_candidates(max_age_days=30)
    assert star.id not in retired
    assert lib.get(star.id).status == "promoted"


def test_cap_limits_retirements_per_cycle(tmp_path):
    lib = SkillLibrary(db_path=tmp_path / "skills.db")
    for i in range(7):
        _mk(lib, f"z{i}", age_days=60, trials=0)
    retired = lib.retire_dormant_candidates(max_age_days=30, cap=3)
    assert len(retired) == 3, "gradualità: mai più di cap ritiri per ciclo"
    still = [s for s in lib.all() if s.status == "candidate"]
    assert len(still) == 4
