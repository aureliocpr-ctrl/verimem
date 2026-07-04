"""audit#3-r3 R13: dream_diff computed only new_ids = shadow - live (add-only by
id), and adopt_dream stored only those. Skills present in BOTH but RETIRED /
PROMOTED / REVISED in the shadow during the dream were invisible to the diff and
never written back — the dream's edits to existing skills were silently lost on
adopt. Fix: a full shadow->live delta (new + changed), applied on adopt.
"""
from __future__ import annotations

from pathlib import Path

from engram.dream import adopt_dream, dream_diff
from engram.skill import Skill, SkillLibrary


def _artifact(shadow_root: Path) -> None:
    (shadow_root / "dream_tasks.json").write_text(
        '{"dream_id": "t1", "pending_tasks": []}'
    )


def _setup(tmp_path: Path):
    shadow_root = tmp_path / "shadow"
    (shadow_root / "skills").mkdir(parents=True)
    _artifact(shadow_root)
    live_dir = tmp_path / "live_skills"
    live_dir.mkdir()
    live_db = live_dir / "skills_index.db"
    shadow_db = shadow_root / "skills" / "skills_index.db"

    live_lib = SkillLibrary(dir_path=live_dir, db_path=live_db)
    shared = Skill(name="shared", trigger="t", body="orig body",
                   status="active", stage="active")
    unchanged = Skill(name="stable", trigger="u", body="same",
                      status="active", stage="active")
    live_lib.store(shared)
    live_lib.store(unchanged)

    shadow_lib = SkillLibrary(dir_path=shadow_root / "skills", db_path=shadow_db)
    # CHANGED: same id, retired + body revised in the dream.
    shadow_lib.store(Skill(id=shared.id, name="shared", trigger="t",
                           body="REVISED body", status="retired", stage="active"))
    # UNCHANGED: byte-identical to live.
    shadow_lib.store(Skill(id=unchanged.id, name="stable", trigger="u",
                           body="same", status="active", stage="active"))
    # NEW: shadow only.
    new = Skill(name="brand new", trigger="n", body="nb",
                status="active", stage="active")
    shadow_lib.store(new)

    live_dirs = {"skills_db": str(live_db), "skills_dir_path": str(live_dir)}
    return shadow_root, live_dirs, live_dir, live_db, shared, unchanged, new


def test_dream_diff_detects_changed_skills(tmp_path):
    shadow_root, live_dirs, _ld, _db, shared, unchanged, new = _setup(tmp_path)
    diff = dream_diff(shadow_root=shadow_root, live_dirs=live_dirs)

    new_ids = {s["shadow_id"] for s in diff["new_skills"]}
    changed_ids = {s["shadow_id"] for s in diff.get("changed_skills", [])}

    assert new.id in new_ids
    assert shared.id in changed_ids, "retired+revised skill must be 'changed'"
    assert unchanged.id not in changed_ids, "identical skill must NOT be flagged"


def test_adopt_dream_applies_changed_skills(tmp_path):
    shadow_root, live_dirs, live_dir, live_db, shared, _unch, new = _setup(tmp_path)
    res = adopt_dream(
        shadow_root=shadow_root, live_dirs=live_dirs,
        backups_root=tmp_path / "backups",
    )
    assert res["ok"] is True

    live2 = SkillLibrary(dir_path=live_dir, db_path=live_db)
    got = live2.get(shared.id)
    assert got is not None
    assert got.status == "retired", "shadow retire was lost on adopt"
    assert got.body == "REVISED body", "shadow body revision was lost on adopt"
    assert live2.get(new.id) is not None, "new skill must still be adopted"
