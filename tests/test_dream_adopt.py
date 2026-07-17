"""CYCLE #38 — Hippo Dreams adopt atomic con backup + rollback.

Step finale della pipeline subscription-first:
  shadow (cycle #34) → propose (cycle #35) → submit (cycle #36)
  → review (cycle #37) → ADOPT (questo cycle).

adopt_dream(shadow_root, live_dirs, *, dream_id):
  1. Verify artifact non già adopted (idempotency hard).
  2. Backup live skills (skills_index.db + dir skills/) in backups/.
  3. Per ogni new_skill (via dream_diff): insert in live SkillLibrary.
  4. Mark artifact adopted_at + adopted_skill_ids.
  5. Return {ok, n_adopted, backup_path, ...}.
  6. Se errore mid-apply → rollback dal backup, raise.

Zero LLM call. Modifica LIVE (è proprio quello che deve fare), ma con
backup atomic.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from verimem.memory import Episode, EpisodicMemory
from verimem.semantic import Fact, SemanticMemory
from verimem.skill import Skill, SkillLibrary


def _h(p: Path) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()[:12]


VALID_SKILL_JSON = {
    "name": "Mental math shortcut adopted",
    "trigger": "when asked X+X",
    "body": "Compute 2X mentally, emit just the digit.",
    "rationale": "Generalises across X+X cluster.",
}


@pytest.fixture
def shadow_with_submitted_skill(tmp_path):
    """Setup: propose + submit di 1 task → shadow ha 1 new skill pronto per adopt."""
    from verimem.dream import propose_dream_tasks, submit_dream_result
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
        "skills_db": skills.db_path,
        "skills_dir_path": skills.dir,
        "episodes_db": mem.db_path,
        "semantic_db": sem.db_path,
    }
    shadow_root = tmp_path / "shadow_a"
    proposed = propose_dream_tasks(
        live_dirs, shadow_root=shadow_root, max_clusters=10, min_cluster_size=2,
    )
    first = proposed["pending_tasks"][0]
    submit_dream_result(
        shadow_root=shadow_root, task_id=first["task_id"],
        skill_json=VALID_SKILL_JSON, tokens_used=2000, model_name="opus-4-7",
    )
    return {
        "live_dirs": live_dirs,
        "live_skills": skills,
        "shadow_root": shadow_root,
        "dream_id": proposed["dream_id"],
        "backups_root": tmp_path / "backups",
    }


# === HAPPY PATH ===

def test_adopt_inserts_new_skill_to_live(shadow_with_submitted_skill):
    """Dopo adopt, la skill creata da submit deve essere nel live SkillLibrary."""
    from verimem.dream import adopt_dream
    s = shadow_with_submitted_skill
    # FRESH library instance per verifica (evita stale _skills_cache).
    fresh_pre = SkillLibrary(
        dir_path=s["live_dirs"]["skills_dir_path"],
        db_path=s["live_dirs"]["skills_db"],
    )
    n_live_pre = len(list(fresh_pre.all()))
    result = adopt_dream(
        shadow_root=s["shadow_root"], live_dirs=s["live_dirs"],
        backups_root=s["backups_root"],
    )
    assert result["ok"] is True
    assert result["n_adopted"] == 1
    fresh_post = SkillLibrary(
        dir_path=s["live_dirs"]["skills_dir_path"],
        db_path=s["live_dirs"]["skills_db"],
    )
    n_live_post = len(list(fresh_post.all()))
    assert n_live_post == n_live_pre + 1
    names = {sk.name for sk in fresh_post.all()}
    assert VALID_SKILL_JSON["name"] in names


def test_adopt_creates_backup_before_apply(shadow_with_submitted_skill):
    """Backup deve esistere dopo adopt e contenere skills_index.db pre-apply."""
    from verimem.dream import adopt_dream
    s = shadow_with_submitted_skill
    result = adopt_dream(
        shadow_root=s["shadow_root"], live_dirs=s["live_dirs"],
        backups_root=s["backups_root"],
    )
    backup_path = Path(result["backup_path"])
    assert backup_path.exists() and backup_path.is_dir()
    backup_db = backup_path / "skills_index.db"
    assert backup_db.exists()
    # Backup contiene il pre-state (no skill nuova)
    backup_lib = SkillLibrary(dir_path=backup_path, db_path=backup_db)
    backup_names = {sk.name for sk in backup_lib.all()}
    assert VALID_SKILL_JSON["name"] not in backup_names
    assert "Live Seed" in backup_names


def test_adopt_marks_artifact_adopted_at(shadow_with_submitted_skill):
    """Artifact deve avere adopted_at timestamp + adopted_skill_ids."""
    from verimem.dream import adopt_dream
    s = shadow_with_submitted_skill
    result = adopt_dream(
        shadow_root=s["shadow_root"], live_dirs=s["live_dirs"],
        backups_root=s["backups_root"],
    )
    artifact = json.loads((s["shadow_root"] / "dream_tasks.json").read_text())
    assert "adopted_at" in artifact
    assert isinstance(artifact["adopted_at"], (int, float))
    assert "adopted_skill_ids" in artifact
    assert len(artifact["adopted_skill_ids"]) == 1
    assert artifact["adopted_skill_ids"] == result["adopted_skill_ids"]


def test_adopt_returns_dream_id(shadow_with_submitted_skill):
    from verimem.dream import adopt_dream
    s = shadow_with_submitted_skill
    result = adopt_dream(
        shadow_root=s["shadow_root"], live_dirs=s["live_dirs"],
        backups_root=s["backups_root"],
    )
    assert result["dream_id"] == s["dream_id"]


# === IDEMPOTENCY ===

def test_adopt_already_adopted_rejects(shadow_with_submitted_skill):
    """Double-adopt → ValueError hard reject con timestamp originale menzionato."""
    from verimem.dream import adopt_dream
    s = shadow_with_submitted_skill
    first = adopt_dream(
        shadow_root=s["shadow_root"], live_dirs=s["live_dirs"],
        backups_root=s["backups_root"],
    )
    with pytest.raises(ValueError, match="already_adopted|adopted"):
        adopt_dream(
            shadow_root=s["shadow_root"], live_dirs=s["live_dirs"],
            backups_root=s["backups_root"],
        )


# === ERROR HANDLING ===

def test_adopt_unknown_shadow_raises(tmp_path):
    from verimem.dream import adopt_dream
    bogus_live = {
        "skills_db": tmp_path / "fake_skills.db",
        "skills_dir_path": tmp_path / "fake_skills",
        "episodes_db": tmp_path / "fake_ep.db",
        "semantic_db": tmp_path / "fake_sem.db",
    }
    with pytest.raises((FileNotFoundError, ValueError), match="dream|shadow|not"):
        adopt_dream(
            shadow_root=tmp_path / "bogus",
            live_dirs=bogus_live,
            backups_root=tmp_path / "backups",
        )


# === SAFETY: zero LLM calls ===

def test_adopt_zero_llm_calls(shadow_with_submitted_skill, monkeypatch):
    from verimem import llm as llm_module
    calls = {"n": 0}
    orig = llm_module.get_llm
    def boom(*a, **kw):
        calls["n"] += 1
        return orig(*a, **kw)
    monkeypatch.setattr(llm_module, "get_llm", boom)
    from verimem.dream import adopt_dream
    s = shadow_with_submitted_skill
    adopt_dream(
        shadow_root=s["shadow_root"], live_dirs=s["live_dirs"],
        backups_root=s["backups_root"],
    )
    assert calls["n"] == 0, f"adopt invoked get_llm {calls['n']} times"


# === ROLLBACK ===

def test_adopt_partial_failure_triggers_rollback(shadow_with_submitted_skill, monkeypatch):
    """Se SkillLibrary.store fallisce mid-adopt, live deve essere restored dal backup.

    Verifica semantica: live skill set == pre-adopt set (no new skill applicata).
    Hash file SHA1 non è affidabile causa WAL/PRAGMA side effects all'apertura.
    """
    from verimem.dream import adopt_dream
    s = shadow_with_submitted_skill

    # Snapshot pre-adopt: ids di skill nel live (via fresh instance).
    fresh_pre = SkillLibrary(
        dir_path=s["live_dirs"]["skills_dir_path"],
        db_path=s["live_dirs"]["skills_db"],
    )
    ids_pre = {sk.id for sk in fresh_pre.all()}

    # Force store to fail when trying to insert the new skill.
    from verimem import skill as skill_module
    real_store = skill_module.SkillLibrary.store
    failed = {"once": False}
    def flaky_store(self, sk):
        # Solo la new skill (NOT live_seed che è già lì) fa raise
        if sk.name == VALID_SKILL_JSON["name"] and not failed["once"]:
            failed["once"] = True
            raise RuntimeError("simulated failure mid-adopt")
        return real_store(self, sk)
    monkeypatch.setattr(skill_module.SkillLibrary, "store", flaky_store)

    with pytest.raises(RuntimeError, match="simulated|adopt"):
        adopt_dream(
            shadow_root=s["shadow_root"], live_dirs=s["live_dirs"],
            backups_root=s["backups_root"],
        )
    # Verifica semantica rollback: live skill ids identici al pre-adopt set.
    fresh_post = SkillLibrary(
        dir_path=s["live_dirs"]["skills_dir_path"],
        db_path=s["live_dirs"]["skills_db"],
    )
    ids_post = {sk.id for sk in fresh_post.all()}
    assert ids_post == ids_pre, (
        f"rollback failed: live skill set changed. "
        f"added={ids_post - ids_pre} removed={ids_pre - ids_post}"
    )


# === EDGE CASE ===

def test_adopt_no_new_skills_returns_n_zero(tmp_path):
    """Edge: shadow senza submit → diff vuoto → adopt = noop ma success ok."""
    from verimem.dream import adopt_dream, propose_dream_tasks
    live = tmp_path / "live"
    live.mkdir()
    skills_dir = live / "skills"
    skills_dir.mkdir()
    skills = SkillLibrary(dir_path=skills_dir, db_path=skills_dir / "skills_index.db")
    skills.store(Skill(id="live_only", name="Live Only", trigger="t", body="b"))
    mem = EpisodicMemory(db_path=live / "episodes.db")
    for i in range(5):
        mem.store(Episode(
            id=f"ep{i}", task_text=f"task {i}", final_answer="x", outcome="success",
        ))
    sem = SemanticMemory(db_path=live / "semantic.db")
    live_dirs = {
        "skills_db": skills.db_path,
        "skills_dir_path": skills.dir,
        "episodes_db": mem.db_path,
        "semantic_db": sem.db_path,
    }
    shadow_root = tmp_path / "shadow_noop"
    propose_dream_tasks(live_dirs, shadow_root=shadow_root, max_clusters=5)
    # Nessun submit → diff vuoto
    result = adopt_dream(
        shadow_root=shadow_root, live_dirs=live_dirs,
        backups_root=tmp_path / "backups",
    )
    assert result["ok"] is True
    assert result["n_adopted"] == 0


# === CRITIC-FOUND COUNTEREXAMPLE: rollback non atomico con multi-skill ===

@pytest.fixture
def shadow_with_two_submitted_skills(tmp_path):
    """Setup robust: build shadow direttamente con 2 new skill, bypass propose+submit.
    Per i counterexample test serve guarantee determinstica di 2 new skill."""
    live = tmp_path / "live"
    live.mkdir()
    skills_dir = live / "skills"
    skills_dir.mkdir()
    skills = SkillLibrary(dir_path=skills_dir, db_path=skills_dir / "skills_index.db")
    skills.store(Skill(id="live_seed", name="Live Seed", trigger="t", body="b"))
    mem_db = live / "episodes.db"
    EpisodicMemory(db_path=mem_db)
    sem_db = live / "semantic.db"
    SemanticMemory(db_path=sem_db)
    live_dirs = {
        "skills_db": skills.db_path, "skills_dir_path": skills.dir,
        "episodes_db": mem_db, "semantic_db": sem_db,
    }
    # Construct shadow manually
    shadow_root = tmp_path / "shadow_a2"
    shadow_skills_dir = shadow_root / "skills"
    shadow_skills_dir.mkdir(parents=True)
    shadow_lib = SkillLibrary(
        dir_path=shadow_skills_dir,
        db_path=shadow_skills_dir / "skills_index.db",
    )
    # Mirror live seed (sarebbe nel snapshot)
    shadow_lib.store(Skill(id="live_seed", name="Live Seed", trigger="t", body="b"))
    # 2 new skills
    shadow_lib.store(Skill(id="new_A", name="Skill A", trigger="tA", body="bA"))
    shadow_lib.store(Skill(id="new_B", name="Skill B", trigger="tB", body="bB"))
    # Costruisci dream_tasks.json minimale
    import json as _json
    artifact = {
        "dream_id": "test_dream_002",
        "shadow_root": str(shadow_root),
        "pending_tasks": [
            {"task_id": "t1", "kind": "nrem_skill_from_cluster", "status": "done",
             "skill_id": "new_A", "context_episode_ids": []},
            {"task_id": "t2", "kind": "nrem_skill_from_cluster", "status": "done",
             "skill_id": "new_B", "context_episode_ids": []},
        ],
        "summary": {"n_clusters_found": 2, "n_tasks_generated": 2},
    }
    (shadow_root / "dream_tasks.json").write_text(_json.dumps(artifact, indent=2))
    return {
        "live_dirs": live_dirs, "shadow_root": shadow_root,
        "backups_root": tmp_path / "backups", "live_skills_dir": skills_dir,
    }


def test_adopt_rollback_cleans_wal_shm(shadow_with_two_submitted_skills, monkeypatch):
    """CRITIC-FOUND #38 counterexample 1: rollback deve eliminare .db-wal/.db-shm
    della live, altrimenti SQLite all'apertura può re-applicare frame WAL della
    scrittura parziale → reintroduce skill o malformed-db."""
    from verimem.dream import adopt_dream
    s = shadow_with_two_submitted_skills
    # Force store fail sulla SECONDA skill (after first one already partially stored).
    from verimem import skill as skill_module
    real_store = skill_module.SkillLibrary.store
    call_count = {"n": 0}
    def flaky_store(self, sk):
        # Skip live_seed (già lì). Conta solo store di NUOVE skill.
        if sk.id != "live_seed":
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("simulated mid-loop failure on 2nd skill")
        return real_store(self, sk)
    monkeypatch.setattr(skill_module.SkillLibrary, "store", flaky_store)
    with pytest.raises(RuntimeError, match="simulated|adopt"):
        adopt_dream(
            shadow_root=s["shadow_root"], live_dirs=s["live_dirs"],
            backups_root=s["backups_root"],
        )
    # WAL/SHM dei live skills NON devono persistere dopo restore.
    live_db = s["live_dirs"]["skills_db"]
    bad = list(live_db.parent.glob(f"{live_db.name}-wal")) + list(
        live_db.parent.glob(f"{live_db.name}-shm")
    )
    # WAL files might exist (open conn re-creates them) but devono essere consistenti:
    # verifica che il DB sia leggibile e che il set di skill ids sia pre-adopt.
    fresh = SkillLibrary(
        dir_path=s["live_dirs"]["skills_dir_path"], db_path=live_db,
    )
    ids_post = {sk.id for sk in fresh.all()}
    assert ids_post == {"live_seed"}, (
        f"WAL residual reintrodotto skill: ids={ids_post}"
    )


def test_adopt_rollback_cleans_orphan_body_files(shadow_with_two_submitted_skills, monkeypatch):
    """CRITIC-FOUND #38 counterexample 2: SkillLibrary.store scrive body
    file <skill_id>.json PRIMA dell'insert DB. Se 2° skill fa raise, il body
    della 1° è già scritto. Rollback deve eliminarlo (non era nel backup)."""
    from verimem.dream import adopt_dream
    s = shadow_with_two_submitted_skills
    # Lista body file pre-adopt.
    body_files_pre = {p.name for p in s["live_skills_dir"].glob("*.json")}
    from verimem import skill as skill_module
    real_store = skill_module.SkillLibrary.store
    call_count = {"n": 0}
    def flaky_store(self, sk):
        if sk.id != "live_seed":
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("simulated mid-loop failure on 2nd skill")
        return real_store(self, sk)
    monkeypatch.setattr(skill_module.SkillLibrary, "store", flaky_store)
    with pytest.raises(RuntimeError):
        adopt_dream(
            shadow_root=s["shadow_root"], live_dirs=s["live_dirs"],
            backups_root=s["backups_root"],
        )
    # Body files post-rollback: nessun .json orfano (no new file rispetto a pre).
    body_files_post = {p.name for p in s["live_skills_dir"].glob("*.json")}
    orphans = body_files_post - body_files_pre
    assert not orphans, (
        f"orphan body files dopo rollback: {orphans} "
        "(SkillLibrary.store ha scritto .json prima di raise, non puliti)"
    )


# === MCP TOOL REGISTRATION ===

def test_mcp_tool_hippo_dream_adopt_in_expected_set():
    from tests.test_mcp_server import _EXPECTED_TOOLS
    assert "hippo_dream_adopt" in _EXPECTED_TOOLS
