"""Tests for Hebbian skill embedding (cells that fire together wire together).

The skill's trigger embedding drifts toward the task embedding on each success.
This makes the skill more retrievable for similar future tasks.
"""
from __future__ import annotations

import numpy as np

from engram.skill import Skill, SkillLibrary


def _embedding_for(lib: SkillLibrary, skill_id: str) -> np.ndarray:
    """Pull the persisted (BLOB) embedding for a skill, as numpy."""
    from engram import embedding as emb_mod

    with lib._connect() as conn:
        row = conn.execute(
            "SELECT trigger_embedding FROM skills WHERE id = ?", (skill_id,)
        ).fetchone()
    return emb_mod.deserialize(row["trigger_embedding"])


def test_success_drifts_embedding_toward_task(tmp_data_dir):
    """After success on a specific task, the skill's embedding moves toward
    the task embedding — by approximately CONFIG.hebbian_alpha."""
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    s = Skill(name="generic helper", trigger="when helping", body="x")
    lib.store(s)
    before = _embedding_for(lib, s.id).copy()

    # Apply with a very specific task — embedding should drift toward it
    lib.update_fitness(s.id, success=True, tokens=100,
                        task_text="solve quadratic equations using the discriminant formula")
    after = _embedding_for(lib, s.id)

    # Embedding should have changed
    assert not np.allclose(before, after), "embedding did not change after Hebbian update"

    # And the change magnitude should be roughly proportional to alpha (small)
    delta = float(np.linalg.norm(after - before))
    assert 0.0 < delta < 0.5, f"hebbian drift too large/small: {delta}"

    # And remain L2-normalised (cosine math relies on this)
    assert abs(float(np.linalg.norm(after)) - 1.0) < 1e-3


def test_failure_does_not_drift(tmp_data_dir):
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    s = Skill(name="x", trigger="x", body="x")
    lib.store(s)
    before = _embedding_for(lib, s.id).copy()
    lib.update_fitness(s.id, success=False, tokens=10, task_text="anything")
    after = _embedding_for(lib, s.id)
    assert np.allclose(before, after), "embedding should not drift on failure"


def test_empty_task_does_not_drift(tmp_data_dir):
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    s = Skill(name="x", trigger="x", body="x")
    lib.store(s)
    before = _embedding_for(lib, s.id).copy()
    lib.update_fitness(s.id, success=True, tokens=10, task_text="")
    after = _embedding_for(lib, s.id)
    assert np.allclose(before, after), "embedding should not drift with empty task"


def test_repeated_drift_compounds_in_same_direction(tmp_data_dir):
    """Multiple successes on the same task should drift the embedding monotonically."""
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    s = Skill(name="generic", trigger="generic", body="x")
    lib.store(s)
    task = "compute fibonacci numbers efficiently with memoization"

    from engram import embedding as emb_mod
    task_emb = emb_mod.encode(task)
    sims = []
    for _ in range(5):
        lib.update_fitness(s.id, success=True, tokens=10, task_text=task)
        cur = _embedding_for(lib, s.id)
        sims.append(float(np.dot(cur, task_emb)))

    # Cosine similarity to the task should increase monotonically (with rounding tolerance)
    for a, b in zip(sims, sims[1:], strict=False):
        assert b >= a - 1e-4, f"similarity should not decrease: {sims}"
    assert sims[-1] > sims[0], "similarity to task did not grow over 5 successes"


def test_hebbian_makes_skill_more_retrievable(tmp_data_dir):
    """Two semantically-distant skills compete for retrieval. After one of
    them is repeatedly applied with success on a specific task, it should
    overtake the other for that task in retrieve()."""
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    a = Skill(name="alpha", trigger="alpha helper unrelated to numbers", body="x")
    b = Skill(name="beta",  trigger="beta helper unrelated to numbers",  body="x")
    lib.store(a)
    lib.store(b)

    task = "compute prime numbers efficiently using the sieve of Eratosthenes"
    # Drift skill A toward the task many times
    for _ in range(8):
        lib.update_fitness(a.id, success=True, tokens=10, task_text=task)

    top = lib.retrieve(task, k=1)
    assert len(top) == 1
    assert top[0].id == a.id, "Hebbian drift did not pull A above B"
