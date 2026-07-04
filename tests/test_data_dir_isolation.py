"""FORGIA pezzo #48 — every SQLite-backed module respects HIPPO_DATA_DIR.

Regression guard: a future refactor that hard-codes a path inside one
of the storage modules would bypass `HIPPO_DATA_DIR` and break test
isolation / multi-tenant deploys.

We don't reload the config module (that pollutes other tests — see
FORGIA #29). Instead we instantiate each storage class with the
expected derived path passed explicitly, then verify the resolved
path lives under the requested data dir.
"""
from __future__ import annotations

from pathlib import Path

import pytest


def test_episodic_memory_respects_data_dir(tmp_path: Path):
    """EpisodicMemory(db_path=...) must put its DB exactly there."""
    from engram.memory import EpisodicMemory
    db = tmp_path / "ep" / "ep.db"
    mem = EpisodicMemory(db_path=db)
    assert mem.db_path == db
    assert db.parent.exists()  # constructor creates the parent


def test_skill_library_respects_dirs(tmp_path: Path):
    from engram.skill import SkillLibrary
    skills_dir = tmp_path / "skills"
    db = skills_dir / "idx.db"
    lib = SkillLibrary(dir_path=skills_dir, db_path=db)
    assert lib.dir == skills_dir
    assert lib.db_path == db
    assert skills_dir.exists()
    assert db.parent.exists()


def test_semantic_memory_respects_db_path(tmp_path: Path):
    from engram.semantic import SemanticMemory
    db = tmp_path / "sem" / "sem.db"
    sem = SemanticMemory(db_path=db)
    # SemanticMemory may name the field differently; tolerate both.
    assert getattr(sem, "db_path", None) == db or db.exists()


def test_data_dir_is_resolved_from_env_in_subprocess(tmp_path):
    """Subprocess sets HIPPO_DATA_DIR before import → CONFIG.data_dir matches."""
    import json
    import os
    import subprocess
    import sys

    env = os.environ.copy()
    env["HIPPO_DATA_DIR"] = str(tmp_path)
    env.setdefault("HIPPO_OFFLINE", "1")

    proc = subprocess.run(
        [sys.executable, "-c",
         "import json, sys; "
         "from engram.config import CONFIG; "
         "print(json.dumps({"
         "'data_dir': str(CONFIG.data_dir),"
         "'episodes_db': str(CONFIG.episodes_db),"
         "'skills_dir': str(CONFIG.skills_dir),"
         "}))"],
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout.strip())
    assert payload["data_dir"] == str(tmp_path), payload
    assert payload["episodes_db"].startswith(str(tmp_path)), payload
    assert payload["skills_dir"].startswith(str(tmp_path)), payload
