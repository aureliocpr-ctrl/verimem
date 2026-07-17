"""Audit 3-round #21 (crash-safety): adopt_dream wrote the `adopted_at` marker
only AFTER mutating the live skills, with a plain write_text (no fsync, no atomic
rename). A hard crash in the mutate->mark gap left the live mutated but the dream
un-marked, so a retry re-ran the backup over the already-mutated live and
clobbered the clean baseline.

Fix: a durable (tmp+fsync+os.replace) `adoption_started_at` marker is written
BEFORE the live mutation. On retry, a set started-marker with no adopted_at means
a prior attempt was interrupted -> refuse (don't clobber). A clean rollback clears
the marker so a legitimate retry is allowed; success clears it too.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from verimem.dream import (
    adopt_dream,
    propose_dream_tasks,
    submit_dream_result,
)
from verimem.memory import Episode, EpisodicMemory
from verimem.semantic import Fact, SemanticMemory
from verimem.skill import Skill, SkillLibrary

VALID_SKILL_JSON = {
    "name": "Mental math shortcut adopted",
    "trigger": "when asked X+X",
    "body": "Compute 2X mentally, emit just the digit.",
    "rationale": "Generalises across X+X cluster.",
}


@pytest.fixture
def shadow(tmp_path):
    live = tmp_path / "live"
    live.mkdir()
    skills_dir = live / "skills"
    skills_dir.mkdir()
    skills = SkillLibrary(dir_path=skills_dir, db_path=skills_dir / "skills_index.db")
    skills.store(Skill(id="live_seed", name="Live Seed", trigger="t", body="b"))
    mem = EpisodicMemory(db_path=live / "episodes.db")
    for i in range(6):
        mem.store(Episode(
            id=f"ep{i}", task_text=f"Compute {i}+{i}",
            final_answer=str(2 * i), outcome="success",
        ))
    sem = SemanticMemory(db_path=live / "semantic.db")
    sem.store(Fact(proposition="seed", topic="t", confidence=0.8))
    live_dirs = {
        "skills_db": skills.db_path, "skills_dir_path": skills.dir,
        "episodes_db": mem.db_path, "semantic_db": sem.db_path,
    }
    shadow_root = tmp_path / "shadow_a"
    proposed = propose_dream_tasks(
        live_dirs, shadow_root=shadow_root, max_clusters=10, min_cluster_size=2,
    )
    submit_dream_result(
        shadow_root=shadow_root, task_id=proposed["pending_tasks"][0]["task_id"],
        skill_json=VALID_SKILL_JSON, tokens_used=2000, model_name="opus-4-7",
    )
    return {
        "live_dirs": live_dirs, "shadow_root": shadow_root,
        "backups_root": tmp_path / "backups",
        "artifact": shadow_root / "dream_tasks.json",
    }


def test_interrupted_marker_blocks_retry(shadow):
    """A started-but-not-completed marker (a prior crash) must refuse a blind
    retry instead of re-backing-up the possibly-mutated live."""
    art = json.loads(shadow["artifact"].read_text())
    art["adoption_started_at"] = 12345.0   # crashed mid-adopt earlier
    art["adopted_at"] = None
    shadow["artifact"].write_text(json.dumps(art))

    with pytest.raises(ValueError, match="interrupt|in_progress|partial|started"):
        adopt_dream(
            shadow_root=shadow["shadow_root"], live_dirs=shadow["live_dirs"],
            backups_root=shadow["backups_root"],
        )


def test_marker_is_durable_before_mutation(shadow, monkeypatch):
    """When the backup runs (just before mutating live), the on-disk artifact
    must ALREADY carry adoption_started_at — i.e. the marker is fsync'd first."""
    from verimem import dream
    seen = {}
    real_backup = dream._backup_live_skills

    def spy_backup(db, d, bdir):
        on_disk = json.loads(Path(shadow["artifact"]).read_text())
        seen["started"] = on_disk.get("adoption_started_at")
        return real_backup(db, d, bdir)

    monkeypatch.setattr(dream, "_backup_live_skills", spy_backup)
    adopt_dream(
        shadow_root=shadow["shadow_root"], live_dirs=shadow["live_dirs"],
        backups_root=shadow["backups_root"],
    )
    assert seen.get("started") is not None, \
        "il marker adoption_started_at deve essere durabile su disco PRIMA del backup/mutazione"


def test_clean_rollback_clears_marker(shadow, monkeypatch):
    """A rollback restores the baseline, so the in-progress marker must be
    cleared — otherwise a legitimate retry would be blocked forever."""
    from verimem import skill as skill_module
    real_store = skill_module.SkillLibrary.store
    failed = {"once": False}

    def flaky_store(self, sk):
        if sk.name == VALID_SKILL_JSON["name"] and not failed["once"]:
            failed["once"] = True
            raise RuntimeError("simulated failure mid-adopt")
        return real_store(self, sk)

    monkeypatch.setattr(skill_module.SkillLibrary, "store", flaky_store)
    with pytest.raises(RuntimeError, match="simulated|adopt"):
        adopt_dream(
            shadow_root=shadow["shadow_root"], live_dirs=shadow["live_dirs"],
            backups_root=shadow["backups_root"],
        )
    art = json.loads(shadow["artifact"].read_text())
    assert art.get("adoption_started_at") is None, \
        "dopo un rollback pulito il marker deve essere azzerato (retry permesso)"
    assert art.get("adopted_at") is None, "un adopt fallito non risulta completato"
