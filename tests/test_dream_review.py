"""CYCLE #37 — Hippo Dreams review tools (read-only, zero side-effect).

3 funzioni helper in dream.py:
  - dream_status(shadow_root) → metadata + counts
  - dream_list_pending(shadow_root) → lista task ancora pending (per Claude/host)
  - dream_diff(shadow_root, live_dirs) → new_skills nel shadow non nel live

3 MCP tool corrispondenti. Tutti zero LLM call, tutti zero modifica.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from engram.memory import Episode, EpisodicMemory
from engram.semantic import Fact, SemanticMemory
from engram.skill import Skill, SkillLibrary


def _h(p: Path) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()[:12]


VALID_SKILL_JSON = {
    "name": "Mental math shortcut",
    "trigger": "when asked X+X",
    "body": "Recognize 2X pattern, compute mentally.",
    "rationale": "Generalises across X+X tasks.",
}


@pytest.fixture
def shadow_with_one_submitted(tmp_path):
    """Setup: propose + submit di 1 task → shadow ha 1 new skill, N-1 pending."""
    from engram.dream import propose_dream_tasks, submit_dream_result
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
    shadow_root = tmp_path / "shadow_r"
    proposed = propose_dream_tasks(
        live_dirs, shadow_root=shadow_root, max_clusters=10, min_cluster_size=2,
    )
    first = proposed["pending_tasks"][0]
    submit_dream_result(
        shadow_root=shadow_root, task_id=first["task_id"],
        skill_json=VALID_SKILL_JSON, tokens_used=2000,
        model_name="opus-4-7",
    )
    return {
        "live_dirs": live_dirs,
        "shadow_root": shadow_root,
        "dream_id": proposed["dream_id"],
        "first_task_id": first["task_id"],
        "pending_count_initial": len(proposed["pending_tasks"]),
    }


# === dream_status() ===

def test_status_returns_required_fields(shadow_with_one_submitted):
    from engram.dream import dream_status
    s = shadow_with_one_submitted
    status = dream_status(shadow_root=s["shadow_root"])
    required = {"dream_id", "n_total", "n_done", "n_pending", "total_tokens_used"}
    assert required.issubset(status.keys())
    assert status["dream_id"] == s["dream_id"]
    assert status["n_total"] == s["pending_count_initial"]
    assert status["n_done"] == 1
    assert status["n_pending"] == s["pending_count_initial"] - 1
    assert status["total_tokens_used"] == 2000


def test_status_includes_models_used(shadow_with_one_submitted):
    from engram.dream import dream_status
    s = shadow_with_one_submitted
    status = dream_status(shadow_root=s["shadow_root"])
    assert "models_used" in status
    assert "opus-4-7" in status["models_used"]


def test_status_unknown_shadow_raises(tmp_path):
    from engram.dream import dream_status
    with pytest.raises((FileNotFoundError, ValueError), match="dream|shadow|not"):
        dream_status(shadow_root=tmp_path / "bogus")


# === dream_list_pending() ===

def test_list_pending_returns_only_pending(shadow_with_one_submitted):
    from engram.dream import dream_list_pending
    s = shadow_with_one_submitted
    pending = dream_list_pending(shadow_root=s["shadow_root"])
    assert isinstance(pending, list)
    # Tutti i task ritornati devono essere pending
    for task in pending:
        # done task non incluso
        assert "skill_id" not in task or task.get("status") == "pending"
    # First task era done, non incluso
    task_ids = {t["task_id"] for t in pending}
    assert s["first_task_id"] not in task_ids


def test_list_pending_preserves_prompts(shadow_with_one_submitted):
    """Ogni pending task deve avere ancora system_prompt + user_prompt per Claude/host."""
    from engram.dream import dream_list_pending
    s = shadow_with_one_submitted
    pending = dream_list_pending(shadow_root=s["shadow_root"])
    if not pending:
        pytest.skip("nessun pending task nel test fixture")
    task = pending[0]
    assert task.get("system_prompt"), "system_prompt missing"
    assert task.get("user_prompt"), "user_prompt missing"
    assert task.get("context_episode_ids")


def test_list_pending_unknown_shadow_raises(tmp_path):
    from engram.dream import dream_list_pending
    with pytest.raises((FileNotFoundError, ValueError), match="dream|shadow|not"):
        dream_list_pending(shadow_root=tmp_path / "bogus")


# === dream_diff() ===

def test_diff_shows_new_skills(shadow_with_one_submitted):
    """Shadow ha 1 skill nuova (dal submit), live no → diff.new_skills = [quella]."""
    from engram.dream import dream_diff
    s = shadow_with_one_submitted
    diff = dream_diff(shadow_root=s["shadow_root"], live_dirs=s["live_dirs"])
    assert "new_skills" in diff
    assert "n_new_skills" in diff
    assert diff["n_new_skills"] >= 1
    # La skill creata da submit deve esserci
    names = {sk["name"] for sk in diff["new_skills"]}
    assert VALID_SKILL_JSON["name"] in names


def test_diff_excludes_live_seed_skill(shadow_with_one_submitted):
    """live ha 'Live Seed' che esiste anche nello shadow (snapshot lo include) →
    NON deve apparire in new_skills."""
    from engram.dream import dream_diff
    s = shadow_with_one_submitted
    diff = dream_diff(shadow_root=s["shadow_root"], live_dirs=s["live_dirs"])
    names = {sk["name"] for sk in diff["new_skills"]}
    assert "Live Seed" not in names


def test_diff_unknown_shadow_raises(tmp_path):
    from engram.dream import dream_diff
    bogus_live = {
        "skills_db": tmp_path / "fake.db",
        "skills_dir_path": tmp_path / "fake",
        "episodes_db": tmp_path / "ep.db",
        "semantic_db": tmp_path / "sem.db",
    }
    with pytest.raises((FileNotFoundError, ValueError), match="dream|shadow|not"):
        dream_diff(shadow_root=tmp_path / "bogus", live_dirs=bogus_live)


# === SAFETY: zero side-effect ===

def test_review_tools_do_not_modify_live(shadow_with_one_submitted):
    """status + list_pending + diff: nessuno modifica live DB."""
    from engram.dream import dream_diff, dream_list_pending, dream_status
    s = shadow_with_one_submitted
    before = {
        k: _h(s["live_dirs"][k])
        for k in ("skills_db", "episodes_db", "semantic_db")
    }
    dream_status(shadow_root=s["shadow_root"])
    dream_list_pending(shadow_root=s["shadow_root"])
    dream_diff(shadow_root=s["shadow_root"], live_dirs=s["live_dirs"])
    after = {
        k: _h(s["live_dirs"][k])
        for k in ("skills_db", "episodes_db", "semantic_db")
    }
    for k in before:
        assert before[k] == after[k], f"live {k} modified by review tool!"


def test_review_tools_zero_llm_calls(shadow_with_one_submitted, monkeypatch):
    from engram import llm as llm_module
    calls = {"n": 0}
    orig = llm_module.get_llm
    def boom(*a, **kw):
        calls["n"] += 1
        return orig(*a, **kw)
    monkeypatch.setattr(llm_module, "get_llm", boom)
    from engram.dream import dream_diff, dream_list_pending, dream_status
    s = shadow_with_one_submitted
    dream_status(shadow_root=s["shadow_root"])
    dream_list_pending(shadow_root=s["shadow_root"])
    dream_diff(shadow_root=s["shadow_root"], live_dirs=s["live_dirs"])
    assert calls["n"] == 0


# === MCP TOOLS REGISTRATION ===

def test_mcp_tools_in_expected_set():
    from tests.test_mcp_server import _EXPECTED_TOOLS
    for tname in ("hippo_dream_status", "hippo_dream_list_pending", "hippo_dream_diff"):
        assert tname in _EXPECTED_TOOLS, f"missing tool: {tname}"
