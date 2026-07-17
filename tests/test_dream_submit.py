"""CYCLE #36 — Hippo Dreams: submit_dream_result.

Pipeline subscription-first (cycle #35 propose → #36 submit_result → #37 diff → #38 adopt):

1. Claude Code (host) ha già chiamato hippo_dream_propose (cycle #35), ottenuto
   pending_tasks con system_prompt + user_prompt structured.
2. Per ogni task: Claude Code esegue LLM call con la sua subscription Pro/Max
   (default opus-4-7), ottiene skill JSON.
3. Ora chiama hippo_dream_submit_result(shadow_name, task_id, skill_json) per
   PERSISTERE lo skill sul SHADOW SkillLibrary (NON sul live — preserva
   safety invariants cycle #34).

Decisioni design (confermate con Aurelio 2026-05-13):
- Lenient validation: required = name+trigger+body (non-empty strings), optional
  = rationale; extra fields silently ignored (LLM output può variare).
- Reject hard se task già "done" (idempotency safety; caller deve usare
  list_pending prima — cycle #37).

Zero LLM call interno: la LLM call è stata fatta da Claude/host. Qui solo
schema validation + persistence + artifact update.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from verimem.memory import Episode, EpisodicMemory
from verimem.semantic import Fact, SemanticMemory
from verimem.skill import Skill, SkillLibrary


def _h(p: Path) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()[:12]


@pytest.fixture
def shadow_with_pending_task(tmp_path):
    """Setup: live corpus + dream propose già fatto + 1 pending task disponibile."""
    from verimem.dream import propose_dream_tasks
    live = tmp_path / "live"
    live.mkdir()
    skills_dir = live / "skills"
    skills_dir.mkdir()
    skills = SkillLibrary(dir_path=skills_dir, db_path=skills_dir / "skills_index.db")
    skills.store(Skill(id="seed", name="Seed", trigger="t", body="b"))
    mem = EpisodicMemory(db_path=live / "episodes.db")
    for i in range(5):
        mem.store(Episode(
            id=f"ep{i}", task_text=f"Compute {i}+{i}", final_answer=str(2 * i),
            outcome="success",
        ))
    sem = SemanticMemory(db_path=live / "semantic.db")
    sem.store(Fact(proposition="seed fact", topic="t", confidence=0.8))
    live_dirs = {
        "skills_db": skills.db_path,
        "skills_dir_path": skills.dir,
        "episodes_db": mem.db_path,
        "semantic_db": sem.db_path,
    }
    shadow_root = tmp_path / "shadow_propose"
    result = propose_dream_tasks(
        live_dirs, shadow_root=shadow_root, max_clusters=10, min_cluster_size=2,
    )
    # Garanzia: almeno 1 task pendente
    assert len(result["pending_tasks"]) >= 1, "fixture broken: no pending tasks"
    return {
        "live_dirs": live_dirs,
        "shadow_root": shadow_root,
        "dream_id": result["dream_id"],
        "first_task_id": result["pending_tasks"][0]["task_id"],
        "first_task_context": result["pending_tasks"][0]["context_episode_ids"],
        "pending_count_initial": len(result["pending_tasks"]),
    }


VALID_SKILL_JSON = {
    "name": "Reuse arithmetic shortcuts",
    "trigger": "when asked to compute simple sums",
    "body": "When the operands are small integers, compute mentally and emit just the digit. Avoid restating the problem.",
    "rationale": "Generalises across all 'compute X+Y' tasks of arity 2-3",
}


# === HAPPY PATH ===

def test_submit_persists_skill_on_shadow(shadow_with_pending_task):
    """Happy path: skill_json valido → skill nuova sul shadow SkillLibrary."""
    from verimem.dream import submit_dream_result
    s = shadow_with_pending_task
    result = submit_dream_result(
        shadow_root=s["shadow_root"], task_id=s["first_task_id"],
        skill_json=VALID_SKILL_JSON, tokens_used=2150, model_name="opus-4-7",
    )
    assert result["ok"] is True
    assert "skill_id" in result
    # Verify shadow library contiene la nuova skill
    shadow_skills = SkillLibrary(
        dir_path=s["shadow_root"] / "skills",
        db_path=s["shadow_root"] / "skills" / "skills_index.db",
    )
    new_skill = shadow_skills.get(result["skill_id"])
    assert new_skill is not None, f"skill {result['skill_id']} not persisted"
    assert new_skill.name == VALID_SKILL_JSON["name"]
    assert new_skill.trigger == VALID_SKILL_JSON["trigger"]
    assert new_skill.body == VALID_SKILL_JSON["body"]
    assert new_skill.stage == "nrem"
    assert new_skill.status == "candidate"
    # source episodes preservati nel skill record
    assert set(new_skill.provenance_episodes) == set(s["first_task_context"])


def test_submit_marks_task_done_in_artifact(shadow_with_pending_task):
    """Dopo submit, dream_tasks.json deve avere task.status = 'done' + skill_id."""
    from verimem.dream import submit_dream_result
    s = shadow_with_pending_task
    submit_dream_result(
        shadow_root=s["shadow_root"], task_id=s["first_task_id"],
        skill_json=VALID_SKILL_JSON, tokens_used=2150,
    )
    artifact = json.loads((s["shadow_root"] / "dream_tasks.json").read_text())
    task = next(t for t in artifact["pending_tasks"] if t["task_id"] == s["first_task_id"])
    assert task["status"] == "done"
    assert "skill_id" in task
    assert task["tokens_used_reported"] == 2150


def test_submit_decreases_remaining_pending_count(shadow_with_pending_task):
    """remaining_pending nel return deve essere coerente con dream_tasks.json."""
    from verimem.dream import submit_dream_result
    s = shadow_with_pending_task
    result = submit_dream_result(
        shadow_root=s["shadow_root"], task_id=s["first_task_id"],
        skill_json=VALID_SKILL_JSON,
    )
    assert result["remaining_pending"] == s["pending_count_initial"] - 1


# === SAFETY INVARIANTS ===

def test_submit_does_not_modify_live(shadow_with_pending_task):
    """CRUCIAL: live DB UNCHANGED (3 SHA1)."""
    from verimem.dream import submit_dream_result
    s = shadow_with_pending_task
    before = {
        k: _h(s["live_dirs"][k])
        for k in ("skills_db", "episodes_db", "semantic_db")
    }
    submit_dream_result(
        shadow_root=s["shadow_root"], task_id=s["first_task_id"],
        skill_json=VALID_SKILL_JSON,
    )
    after = {
        k: _h(s["live_dirs"][k])
        for k in ("skills_db", "episodes_db", "semantic_db")
    }
    for k in before:
        assert before[k] == after[k], f"live {k} modified by submit!"


def test_submit_zero_llm_calls(shadow_with_pending_task, monkeypatch):
    """SUBSCRIPTION-FIRST: zero LLM call interne. Monkeypatch sentinel."""
    from verimem import llm as llm_module
    calls = {"n": 0}
    orig = llm_module.get_llm
    def boom(*a, **kw):
        calls["n"] += 1
        return orig(*a, **kw)
    monkeypatch.setattr(llm_module, "get_llm", boom)
    from verimem.dream import submit_dream_result
    s = shadow_with_pending_task
    submit_dream_result(
        shadow_root=s["shadow_root"], task_id=s["first_task_id"],
        skill_json=VALID_SKILL_JSON,
    )
    assert calls["n"] == 0, (
        f"submit_dream_result invoked get_llm {calls['n']} times — "
        "must be LLM-free (subscription-first directive)"
    )


# === ERROR HANDLING ===

def test_submit_unknown_shadow_root_raises(tmp_path):
    """shadow_root non esiste → FileNotFoundError (o subclass)."""
    from verimem.dream import submit_dream_result
    bogus = tmp_path / "does_not_exist"
    with pytest.raises((FileNotFoundError, ValueError), match="dream|shadow|not found"):
        submit_dream_result(
            shadow_root=bogus, task_id="any", skill_json=VALID_SKILL_JSON,
        )


def test_submit_unknown_task_id_raises(shadow_with_pending_task):
    """task_id non in dream_tasks.json → ValueError."""
    from verimem.dream import submit_dream_result
    s = shadow_with_pending_task
    with pytest.raises(ValueError, match="task|unknown"):
        submit_dream_result(
            shadow_root=s["shadow_root"], task_id="bogus_task_xyz",
            skill_json=VALID_SKILL_JSON,
        )


def test_submit_already_done_task_rejects_hard(shadow_with_pending_task):
    """Idempotency hard: double-submit dello stesso task_id → ValueError con info."""
    from verimem.dream import submit_dream_result
    s = shadow_with_pending_task
    first = submit_dream_result(
        shadow_root=s["shadow_root"], task_id=s["first_task_id"],
        skill_json=VALID_SKILL_JSON,
    )
    # Seconda submit DEVE essere rifiutata
    with pytest.raises(ValueError, match="already_submitted|done|already") as exc_info:
        submit_dream_result(
            shadow_root=s["shadow_root"], task_id=s["first_task_id"],
            skill_json=VALID_SKILL_JSON,
        )
    # Errore deve menzionare lo skill_id già esistente per debug
    assert first["skill_id"] in str(exc_info.value)


# === VALIDATION ===

def test_submit_missing_required_name_rejects(shadow_with_pending_task):
    """skill_json senza `name` → ValueError validation."""
    from verimem.dream import submit_dream_result
    s = shadow_with_pending_task
    bad = {"trigger": "ok", "body": "ok"}
    with pytest.raises(ValueError, match="name|required|validation"):
        submit_dream_result(
            shadow_root=s["shadow_root"], task_id=s["first_task_id"], skill_json=bad,
        )


def test_submit_empty_name_rejects(shadow_with_pending_task):
    """skill_json con name='' → ValueError validation."""
    from verimem.dream import submit_dream_result
    s = shadow_with_pending_task
    bad = {"name": "  ", "trigger": "ok", "body": "ok"}
    with pytest.raises(ValueError, match="name|empty|validation"):
        submit_dream_result(
            shadow_root=s["shadow_root"], task_id=s["first_task_id"], skill_json=bad,
        )


def test_submit_wrong_type_body_rejects(shadow_with_pending_task):
    """skill_json con body=42 (int) → ValueError validation."""
    from verimem.dream import submit_dream_result
    s = shadow_with_pending_task
    bad = {"name": "ok", "trigger": "ok", "body": 42}
    with pytest.raises(ValueError, match="body|type|str|validation"):
        submit_dream_result(
            shadow_root=s["shadow_root"], task_id=s["first_task_id"], skill_json=bad,
        )


def test_submit_lenient_extra_fields_accepted(shadow_with_pending_task):
    """LENIENT: extra fields nell'output LLM silently ignored."""
    from verimem.dream import submit_dream_result
    s = shadow_with_pending_task
    permissive = {
        **VALID_SKILL_JSON,
        "extra_field_from_llm": "whatever",
        "confidence_score": 0.95,
        "metadata": {"foo": "bar"},
    }
    result = submit_dream_result(
        shadow_root=s["shadow_root"], task_id=s["first_task_id"],
        skill_json=permissive,
    )
    assert result["ok"] is True


# === MCP TOOL REGISTRATION ===

def test_mcp_tool_hippo_dream_submit_result_in_expected_set():
    from tests.test_mcp_server import _EXPECTED_TOOLS
    assert "hippo_dream_submit_result" in _EXPECTED_TOOLS
