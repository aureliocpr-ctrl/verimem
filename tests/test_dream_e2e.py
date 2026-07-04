"""CYCLE #39 — Hippo Dreams end-to-end integration test (full pipeline mock).

Sweep through tutti i 7 MCP tool della pipeline subscription-first in 1 test:
  shadow ← propose ← list_pending ← submit_result ←
  status ← diff ← adopt

Mock LLM = il caller fornisce skill JSON direttamente, simulando l'output
LLM. Test segnale che la pipeline E2E è funzionale + idempotente + safe.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from engram.memory import Episode, EpisodicMemory
from engram.semantic import Fact, SemanticMemory
from engram.skill import Skill, SkillLibrary


@pytest.fixture
def live_corpus(tmp_path):
    """Corpus live con 2 cluster ben separati (math + reverse) per garantire propose ≥ 2 tasks."""
    live = tmp_path / "live"
    live.mkdir()
    skills_dir = live / "skills"
    skills_dir.mkdir()
    skills = SkillLibrary(dir_path=skills_dir, db_path=skills_dir / "skills_index.db")
    skills.store(Skill(id="live_seed", name="Live Seed", trigger="t", body="b"))
    mem = EpisodicMemory(db_path=live / "episodes.db")
    # Cluster math forte: 6 episodi molto simili
    for i in range(6):
        mem.store(Episode(
            id=f"m{i}", task_text=f"Compute {i}+{i}",
            final_answer=str(2 * i), outcome="success",
        ))
    # Cluster reverse forte: 6 episodi simili
    for i in range(6):
        mem.store(Episode(
            id=f"r{i}", task_text=f"Reverse string 'abc{i}'",
            final_answer=f"{i}cba", outcome="success",
        ))
    sem = SemanticMemory(db_path=live / "semantic.db")
    sem.store(Fact(proposition="seed fact", topic="t", confidence=0.8))
    return {
        "live_dirs": {
            "skills_db": skills.db_path,
            "skills_dir_path": skills.dir,
            "episodes_db": mem.db_path,
            "semantic_db": sem.db_path,
        },
        "skills_dir": skills_dir,
    }


def test_e2e_full_pipeline_mock_llm(live_corpus, tmp_path):
    """Full sweep: propose → list_pending → submit (mock LLM output) → status →
    diff → adopt. Verifica che live abbia le skill nuove a fine pipeline."""
    from engram.dream import (
        adopt_dream,
        dream_diff,
        dream_list_pending,
        dream_status,
        propose_dream_tasks,
        submit_dream_result,
    )
    shadow_root = tmp_path / "shadow_e2e"
    backups_root = tmp_path / "backups"

    # STEP 1: propose
    proposed = propose_dream_tasks(
        live_corpus["live_dirs"],
        shadow_root=shadow_root,
        max_clusters=5,
        min_cluster_size=3,
    )
    assert proposed["summary"]["n_tasks_generated"] >= 1
    n_initial = proposed["summary"]["n_tasks_generated"]

    # STEP 2: list_pending (review pre-LLM)
    pending = dream_list_pending(shadow_root=shadow_root)
    assert len(pending) == n_initial
    # Ogni pending task ha system_prompt + user_prompt
    for task in pending:
        assert task.get("system_prompt")
        assert task.get("user_prompt")
        assert task.get("context_episode_ids")

    # STEP 3: per ogni task, simula LLM output e submit
    for i, task in enumerate(pending):
        fake_llm_output = {
            "name": f"E2E skill {i}",
            "trigger": f"when context matches cluster {i}",
            "body": f"Heuristic body for task {task['task_id'][:6]}.",
            "rationale": "End-to-end test synthesis.",
        }
        result = submit_dream_result(
            shadow_root=shadow_root, task_id=task["task_id"],
            skill_json=fake_llm_output, tokens_used=1500 + i,
            model_name="opus-4-7-test",
        )
        assert result["ok"] is True
        assert result["skill_id"]

    # STEP 4: status finale
    status = dream_status(shadow_root=shadow_root)
    assert status["n_total"] == n_initial
    assert status["n_done"] == n_initial
    assert status["n_pending"] == 0
    assert status["total_tokens_used"] >= 1500 * n_initial

    # STEP 5: diff
    diff = dream_diff(shadow_root=shadow_root, live_dirs=live_corpus["live_dirs"])
    assert diff["n_new_skills"] == n_initial

    # STEP 6: adopt atomic
    adopted = adopt_dream(
        shadow_root=shadow_root, live_dirs=live_corpus["live_dirs"],
        backups_root=backups_root,
    )
    assert adopted["ok"] is True
    assert adopted["n_adopted"] == n_initial

    # STEP 7: verifica live ha le nuove skill
    fresh_live = SkillLibrary(
        dir_path=live_corpus["skills_dir"],
        db_path=live_corpus["live_dirs"]["skills_db"],
    )
    all_names = {sk.name for sk in fresh_live.all()}
    for i in range(n_initial):
        assert f"E2E skill {i}" in all_names

    # STEP 8: idempotency double-adopt
    with pytest.raises(ValueError, match="already_adopted"):
        adopt_dream(
            shadow_root=shadow_root, live_dirs=live_corpus["live_dirs"],
            backups_root=backups_root,
        )


def test_e2e_pipeline_does_not_leak_anthropic_key(live_corpus, tmp_path, monkeypatch):
    """Crucial invariant: l'intera pipeline E2E NON deve mai invocare get_llm
    (zero ANTHROPIC_API_KEY usage, subscription-first guarantee)."""
    from engram import llm as llm_module
    calls = {"n": 0}
    orig = llm_module.get_llm
    def boom(*a, **kw):
        calls["n"] += 1
        return orig(*a, **kw)
    monkeypatch.setattr(llm_module, "get_llm", boom)

    from engram.dream import (
        adopt_dream,
        dream_diff,
        dream_list_pending,
        dream_status,
        propose_dream_tasks,
        submit_dream_result,
    )
    shadow_root = tmp_path / "shadow_nokey"
    backups_root = tmp_path / "backups_nokey"

    proposed = propose_dream_tasks(
        live_corpus["live_dirs"], shadow_root=shadow_root,
        max_clusters=5, min_cluster_size=3,
    )
    for i, task in enumerate(dream_list_pending(shadow_root=shadow_root)):
        submit_dream_result(
            shadow_root=shadow_root, task_id=task["task_id"],
            skill_json={"name": f"x{i}", "trigger": "t", "body": "b"},
            tokens_used=100,
        )
    dream_status(shadow_root=shadow_root)
    dream_diff(shadow_root=shadow_root, live_dirs=live_corpus["live_dirs"])
    adopt_dream(
        shadow_root=shadow_root, live_dirs=live_corpus["live_dirs"],
        backups_root=backups_root,
    )

    assert calls["n"] == 0, (
        f"E2E pipeline invoked get_llm {calls['n']} times — "
        "subscription-first guarantee VIOLATED"
    )


def test_e2e_pipeline_preserves_live_until_adopt(live_corpus, tmp_path):
    """Invariant: solo adopt modifica live. Tutti gli altri 6 step lasciano
    live invariato (hash check su skills_index.db PRE-adopt vs INITIAL)."""
    import hashlib

    from engram.dream import (
        dream_diff,
        dream_list_pending,
        dream_status,
        propose_dream_tasks,
        submit_dream_result,
    )

    def h(p): return hashlib.sha1(p.read_bytes()).hexdigest()
    pre_hash = h(live_corpus["live_dirs"]["skills_db"])

    shadow_root = tmp_path / "shadow_invariant"
    proposed = propose_dream_tasks(
        live_corpus["live_dirs"], shadow_root=shadow_root,
        max_clusters=3, min_cluster_size=3,
    )
    for i, task in enumerate(dream_list_pending(shadow_root=shadow_root)):
        submit_dream_result(
            shadow_root=shadow_root, task_id=task["task_id"],
            skill_json={"name": f"inv{i}", "trigger": "t", "body": "b"},
        )
    dream_status(shadow_root=shadow_root)
    dream_diff(shadow_root=shadow_root, live_dirs=live_corpus["live_dirs"])

    post_hash_pre_adopt = h(live_corpus["live_dirs"]["skills_db"])
    assert post_hash_pre_adopt == pre_hash, (
        "live skills_db modificato PRIMA di adopt — violazione invariante"
    )
