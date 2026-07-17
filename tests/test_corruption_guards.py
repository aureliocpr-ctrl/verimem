"""FORGIA pezzo #37 — Corruption guards on file-backed JSON readers.

Multiple call-sites used to assume `json.loads(file)` returns a dict.
A hand-edited / cross-version / truncated file containing a JSON
scalar or list would crash with `TypeError: argument of type 'X' is
not iterable` or `AttributeError: 'list' has no attribute 'get'`.

This test pins three guards forged in pezzo #37:

  1. `repomap._load_cache` returns {} on a non-object payload.
  2. `skill.SkillLibrary.get` returns None on a corrupt skill JSON.
  3. `settings.load` returns the default UserSettings on garbage.
"""
from __future__ import annotations

from pathlib import Path


def test_repomap_load_cache_handles_scalar(tmp_path: Path):
    from verimem.repomap import _load_cache
    p = tmp_path / "cache.json"
    p.write_text("4", encoding="utf-8")
    assert _load_cache(p) == {}

    p.write_text("[1, 2, 3]", encoding="utf-8")
    assert _load_cache(p) == {}

    p.write_text("null", encoding="utf-8")
    assert _load_cache(p) == {}

    p.write_text('"string"', encoding="utf-8")
    assert _load_cache(p) == {}

    # Real dict still works.
    p.write_text('{"a": 1}', encoding="utf-8")
    assert _load_cache(p) == {"a": 1}


def test_skill_get_returns_none_on_corruption(tmp_path: Path):
    from verimem.skill import SkillLibrary
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    db = skills_dir / "idx.db"
    lib = SkillLibrary(dir_path=skills_dir, db_path=db)

    # Drop a hand-corrupt JSON at the path the lib would load.
    bad = skills_dir / "BADXX.json"
    bad.write_text("[1, 2, 3]", encoding="utf-8")
    lib.invalidate_cache()
    # Without crashing, the library returns None for a corrupt skill.
    assert lib.get("BADXX") is None

    # Also: a scalar JSON.
    bad.write_text("4", encoding="utf-8")
    lib.invalidate_cache()
    assert lib.get("BADXX") is None

    # And a malformed JSON.
    bad.write_text("{not json}", encoding="utf-8")
    lib.invalidate_cache()
    assert lib.get("BADXX") is None


def test_settings_load_returns_default_on_garbage(tmp_path: Path, monkeypatch):
    from verimem import settings as settings_mod
    bad = tmp_path / "settings.json"
    monkeypatch.setattr(settings_mod, "SETTINGS_FILE", bad)
    bad.write_text("[1, 2, 3]", encoding="utf-8")
    s = settings_mod.load()
    # Default UserSettings has provider=""; a scalar/list payload returns
    # the default rather than crashing on `.items()`.
    assert s.provider == ""
