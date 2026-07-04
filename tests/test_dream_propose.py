"""CYCLE #35 redesign — Hippo Dreams subscription-first.

propose_dream_tasks(live_dirs, shadow_root, *, max_clusters, ...) -> dict

Tool MCP che prepara cluster di episodi + prompt structured per skill synthesis
SENZA mai chiamare LLM internamente. Claude Code (host) consuma i prompt e fa
le LLM call con la subscription dell'utente, poi passa result via cycle #36
hippo_dream_submit_result.

Direttiva fondamentale (fact preferences/aurelio d4dd857b1eea):
subscription = base sempre. API key separata = opt-in per public users.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engram.memory import Episode, EpisodicMemory
from engram.semantic import Fact, SemanticMemory
from engram.skill import Skill, SkillLibrary


@pytest.fixture
def live_dirs_with_corpus(tmp_path):
    """Live state con N episodi clusterabili (testi simili a gruppi)."""
    live = tmp_path / "live"
    live.mkdir()
    skills_dir = live / "skills"
    skills_dir.mkdir()
    skills = SkillLibrary(dir_path=skills_dir, db_path=skills_dir / "skills_index.db")
    skills.store(Skill(id="seed", name="Seed Skill", trigger="t", body="b"))
    episodes_db = live / "episodes.db"
    mem = EpisodicMemory(db_path=episodes_db)
    # Cluster A: task ripetitivi su matematica (5 episodi simili)
    for i in range(5):
        mem.store(Episode(
            id=f"math_{i}", task_text=f"Compute {i}+{i}",
            final_answer=str(2 * i), outcome="success",
        ))
    # Cluster B: task ripetitivi su stringhe (5 episodi simili)
    for i in range(5):
        mem.store(Episode(
            id=f"str_{i}", task_text=f"Reverse the string 'hello{i}'",
            final_answer=f"'{i}olleh'"[::-1], outcome="success",
        ))
    semantic_db = live / "semantic.db"
    sem = SemanticMemory(db_path=semantic_db)
    sem.store(Fact(proposition="seed fact", topic="t", confidence=0.8))
    return {
        "skills_db": skills_dir / "skills_index.db",
        "skills_dir_path": skills_dir,
        "episodes_db": episodes_db,
        "semantic_db": semantic_db,
        "skills": skills,
    }


# === propose_dream_tasks() core function ===

def test_propose_returns_dream_id_and_shadow_root(live_dirs_with_corpus, tmp_path):
    from engram.dream import propose_dream_tasks
    result = propose_dream_tasks(
        live_dirs_with_corpus, shadow_root=tmp_path / "shadow_p1",
    )
    assert "dream_id" in result
    assert "shadow_root" in result
    assert result["dream_id"]  # non-empty


def test_propose_zero_llm_calls(live_dirs_with_corpus, tmp_path, monkeypatch):
    """CRUCIAL: zero LLM call interne. Subscription-first guarantee."""
    # Sentinel: monkeypatcho get_llm per esplodere se chiamato
    from engram import llm as llm_module
    from engram.dream import propose_dream_tasks
    calls = {"n": 0}
    orig = llm_module.get_llm
    def boom(*a, **kw):
        calls["n"] += 1
        return orig(*a, **kw)
    monkeypatch.setattr(llm_module, "get_llm", boom)
    propose_dream_tasks(
        live_dirs_with_corpus, shadow_root=tmp_path / "shadow_p2",
    )
    # propose_dream_tasks NON deve invocare get_llm (LLM-free path).
    assert calls["n"] == 0, (
        f"propose_dream_tasks invoked get_llm {calls['n']} times — "
        "must be LLM-free (subscription-first directive)"
    )


def test_propose_returns_pending_tasks_for_each_cluster(live_dirs_with_corpus, tmp_path):
    """10 episodi (2 cluster simili) → almeno 1 pending task. Conferma clustering reale."""
    from engram.dream import propose_dream_tasks
    result = propose_dream_tasks(
        live_dirs_with_corpus, shadow_root=tmp_path / "shadow_p3",
        max_clusters=10,
    )
    assert "pending_tasks" in result
    assert isinstance(result["pending_tasks"], list)
    # Almeno 1 cluster trovato (test pollution se < 1)
    assert len(result["pending_tasks"]) >= 1


def test_propose_task_has_required_schema(live_dirs_with_corpus, tmp_path):
    """Ogni dream task deve avere: task_id, kind, system_prompt, user_prompt, context_episode_ids."""
    from engram.dream import propose_dream_tasks
    result = propose_dream_tasks(
        live_dirs_with_corpus, shadow_root=tmp_path / "shadow_p4",
        max_clusters=10,
    )
    if not result["pending_tasks"]:
        pytest.skip("no clusters formed in test corpus")
    task = result["pending_tasks"][0]
    required = {"task_id", "kind", "system_prompt", "user_prompt", "context_episode_ids"}
    assert required.issubset(task.keys()), (
        f"missing keys: {required - task.keys()}"
    )
    assert task["kind"] in ("nrem_skill_from_cluster",)  # cycle #35 only kind
    assert "DREAMER" in task["system_prompt"] or "skill" in task["system_prompt"].lower()
    assert isinstance(task["context_episode_ids"], list)
    assert len(task["context_episode_ids"]) >= 2  # min cluster size


def test_propose_persists_tasks_artifact_file(live_dirs_with_corpus, tmp_path):
    """File artifact JSON persistito su shadow_root/dream_tasks.json per audit/replay."""
    from engram.dream import propose_dream_tasks
    shadow_root = tmp_path / "shadow_p5"
    result = propose_dream_tasks(
        live_dirs_with_corpus, shadow_root=shadow_root,
    )
    artifact = shadow_root / "dream_tasks.json"
    assert artifact.exists(), "dream_tasks.json artifact non creato"
    data = json.loads(artifact.read_text())
    assert "dream_id" in data
    assert "pending_tasks" in data
    assert data["dream_id"] == result["dream_id"]


def test_propose_does_not_modify_live(live_dirs_with_corpus, tmp_path):
    """Crucial: hash test live DB pre/post — NESSUNA modifica."""
    import hashlib

    from engram.dream import propose_dream_tasks
    def h(p): return hashlib.sha1(p.read_bytes()).hexdigest()
    before = {
        k: h(live_dirs_with_corpus[k])
        for k in ("skills_db", "episodes_db", "semantic_db")
    }
    propose_dream_tasks(
        live_dirs_with_corpus, shadow_root=tmp_path / "shadow_p6",
    )
    after = {
        k: h(live_dirs_with_corpus[k])
        for k in ("skills_db", "episodes_db", "semantic_db")
    }
    for k in before:
        assert before[k] == after[k], f"live {k} modified by propose!"


def test_propose_respects_max_clusters(live_dirs_with_corpus, tmp_path):
    """max_clusters cap: anche se ci sono N>cap cluster, pending_tasks ≤ cap."""
    from engram.dream import propose_dream_tasks
    result = propose_dream_tasks(
        live_dirs_with_corpus, shadow_root=tmp_path / "shadow_p7",
        max_clusters=1,
    )
    assert len(result["pending_tasks"]) <= 1


def test_propose_includes_summary_counts(live_dirs_with_corpus, tmp_path):
    """Report deve includere counts diagnostici: total clusters trovati, post-cap."""
    from engram.dream import propose_dream_tasks
    result = propose_dream_tasks(
        live_dirs_with_corpus, shadow_root=tmp_path / "shadow_p8",
    )
    assert "summary" in result
    s = result["summary"]
    assert "n_episodes_snapshot" in s
    assert "n_clusters_found" in s
    assert "n_tasks_generated" in s


def test_propose_invalid_shadow_root_overlap_raises(live_dirs_with_corpus):
    """Riusa la validation cycle #34: shadow=live deve raise non distruggere."""
    from engram.dream import propose_dream_tasks
    live_root = live_dirs_with_corpus["skills_db"].parent.parent
    with pytest.raises(ValueError, match="overlap|live"):
        propose_dream_tasks(
            live_dirs_with_corpus, shadow_root=live_root,
        )
    # Live deve sopravvivere
    assert live_dirs_with_corpus["skills_db"].exists()


# === MCP tool registration ===

def test_mcp_tool_hippo_dream_propose_in_expected_set():
    from tests.test_mcp_server import _EXPECTED_TOOLS
    assert "hippo_dream_propose" in _EXPECTED_TOOLS
