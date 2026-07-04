"""Tests for lateral inhibition (anti-Hebbian) in SkillLibrary.

The point of these tests is to measure that the *direction* and the
*magnitude* of the embedding change happen as the model dictates — not
just that the code runs without errors. Lateral inhibition is a
*cumulative* effect; one event nudges, many events differentiate. So
each test exercises one well-defined property and we leave the
"does it improve retrieval over hundreds of episodes" question to a
benchmark, not a unit test.
"""
from __future__ import annotations

import numpy as np
import pytest

from engram import embedding
from engram.config import CONFIG
from engram.skill import Skill, SkillLibrary


def _cosine(u: np.ndarray, v: np.ndarray) -> float:
    nu = float(np.linalg.norm(u))
    nv = float(np.linalg.norm(v))
    if nu == 0 or nv == 0:
        return 0.0
    return float(np.dot(u, v) / (nu * nv))


@pytest.fixture
def lib(tmp_data_dir):
    """Fresh SkillLibrary on a temp dir per test."""
    return SkillLibrary(
        dir_path=tmp_data_dir / "skills",
        db_path=tmp_data_dir / "skills_index.db",
    )


@pytest.fixture
def lateral_on(monkeypatch):
    """CONFIG is a frozen dataclass; swap the whole singleton for a copy
    with the lateral-inhibition knobs flipped on. We monkeypatch the
    binding `engram.skill.CONFIG` (which is what the implementation
    reads), not the source module — replacing the source module's
    attribute would leak into other tests in the same process."""
    from dataclasses import replace

    from engram import skill as skill_mod
    new = replace(
        CONFIG,
        lateral_inhibition_enabled=True,
        lateral_inhibition_min_similarity=0.80,
        lateral_inhibition_alpha=0.10,
        lateral_inhibition_top_k=5,
    )
    monkeypatch.setattr(skill_mod, "CONFIG", new)


# ---------------------------------------------------------------------------
# Happy path: a winner and a near-clone rival. After the winner consolidates
# on a task, the rival's embedding cosine to that task must DECREASE.
# ---------------------------------------------------------------------------


def test_rival_embedding_moves_away_from_winning_task(lib, lateral_on):
    task = "fix calculator add function returns wrong sign"
    task_vec = embedding.encode(task)

    # Winner: a skill with a learned_embedding seeded by an earlier success
    # close to the task. We seed it deliberately so the post-Hebbian winner
    # vector is highly cosine-similar to the rival.
    winner = Skill(name="bugfix_arith", trigger="fix arithmetic bug",
                   body="patch return statement",
                   learned_embedding=embedding.encode(
                       "fix arithmetic bug in calculator add").tolist())
    rival = Skill(name="rewrite_module", trigger="rewrite arithmetic module",
                  body="overwrite the file",
                  learned_embedding=embedding.encode(
                      "fix arithmetic bug in calculator add").tolist())
    lib.store(winner)
    lib.store(rival)

    rival_before = np.asarray(rival.learned_embedding, dtype=np.float32)
    cos_before = _cosine(rival_before, task_vec)

    # Trigger one fitness update on the winner with the task. Hebbian moves
    # winner toward task; lateral inhibition then nudges the rival away.
    lib.update_fitness(winner.id, success=True, tokens=10, task_text=task)

    rival_reloaded = lib.get(rival.id)
    rival_after = np.asarray(rival_reloaded.learned_embedding, dtype=np.float32)
    cos_after = _cosine(rival_after, task_vec)

    # Direction: cosine of rival to task must DECREASE.
    assert cos_after < cos_before, (
        f"expected rival to move away from task; "
        f"cos before={cos_before:.4f}, after={cos_after:.4f}"
    )


# ---------------------------------------------------------------------------
# Below threshold: a "rival" whose embedding cosine to the winner falls
# below `lateral_inhibition_min_similarity` is NOT inhibited at all.
# ---------------------------------------------------------------------------


def test_below_threshold_skills_are_not_inhibited(lib, lateral_on):
    task = "fix calculator add function"

    winner = Skill(name="bugfix_arith", trigger="fix arithmetic bug",
                   body="patch return statement",
                   learned_embedding=embedding.encode(
                       "fix arithmetic bug").tolist())
    distant = Skill(name="parse_json", trigger="parse json from web",
                    body="json.loads with try except",
                    learned_embedding=embedding.encode(
                        "parse json from web response").tolist())
    lib.store(winner)
    lib.store(distant)

    distant_before = list(distant.learned_embedding)

    lib.update_fitness(winner.id, success=True, tokens=10, task_text=task)

    distant_reloaded = lib.get(distant.id)
    # Either the rival was untouched (most likely) OR the change is below
    # numerical noise. Strict equality is too strict (float32 round-trip
    # via SQLite blob); allclose is the right test.
    assert np.allclose(
        np.asarray(distant_reloaded.learned_embedding, dtype=np.float32),
        np.asarray(distant_before, dtype=np.float32),
        atol=1e-6,
    )


# ---------------------------------------------------------------------------
# Failure path: when the winner LOSES (success=False), no inhibition
# fires. We do not punish rivals for someone else's failure.
# ---------------------------------------------------------------------------


def test_no_inhibition_on_failure(lib, lateral_on):
    task = "fix calculator add function"

    seed = embedding.encode("fix arithmetic bug").tolist()
    winner = Skill(name="bugfix_arith", trigger="fix arithmetic bug",
                   body="patch", learned_embedding=seed)
    rival = Skill(name="rewrite_module", trigger="rewrite arithmetic module",
                  body="overwrite", learned_embedding=seed)
    lib.store(winner)
    lib.store(rival)

    rival_before = list(rival.learned_embedding)

    lib.update_fitness(winner.id, success=False, tokens=10, task_text=task)

    rival_reloaded = lib.get(rival.id)
    assert np.allclose(
        np.asarray(rival_reloaded.learned_embedding, dtype=np.float32),
        np.asarray(rival_before, dtype=np.float32),
        atol=1e-6,
    )


# ---------------------------------------------------------------------------
# Disabled by default: even with a near-clone rival, when the feature is
# OFF (the default) nothing changes. This is the safety property — opt-in
# is real, not a label.
# ---------------------------------------------------------------------------


def test_disabled_by_default_does_not_inhibit(lib, monkeypatch):
    # The real CONFIG has lateral_inhibition_enabled=False by default,
    # so we don't even need to override it here — but we make the
    # property explicit by re-asserting the binding the implementation
    # reads.
    from dataclasses import replace

    from engram import skill as skill_mod
    monkeypatch.setattr(
        skill_mod, "CONFIG",
        replace(CONFIG, lateral_inhibition_enabled=False),
    )
    task = "fix calculator add function"

    seed = embedding.encode("fix arithmetic bug").tolist()
    winner = Skill(name="bugfix_arith", trigger="fix arithmetic bug",
                   body="patch", learned_embedding=seed)
    rival = Skill(name="rewrite_module", trigger="rewrite arithmetic module",
                  body="overwrite", learned_embedding=seed)
    lib.store(winner)
    lib.store(rival)

    rival_before = list(rival.learned_embedding)

    lib.update_fitness(winner.id, success=True, tokens=10, task_text=task)

    rival_reloaded = lib.get(rival.id)
    assert np.allclose(
        np.asarray(rival_reloaded.learned_embedding, dtype=np.float32),
        np.asarray(rival_before, dtype=np.float32),
        atol=1e-6,
    )


# ---------------------------------------------------------------------------
# Retired skills are excluded from inhibition. They're already out of the
# retrieval pool; touching them adds churn for no benefit.
# ---------------------------------------------------------------------------


def test_retired_rivals_are_not_inhibited(lib, lateral_on):
    task = "fix calculator add function"

    seed = embedding.encode("fix arithmetic bug").tolist()
    winner = Skill(name="bugfix_arith", trigger="fix arithmetic bug",
                   body="patch", learned_embedding=seed)
    rival = Skill(name="rewrite_module", trigger="rewrite arithmetic module",
                  body="overwrite", learned_embedding=seed,
                  status="retired")
    lib.store(winner)
    lib.store(rival)

    rival_before = list(rival.learned_embedding)

    lib.update_fitness(winner.id, success=True, tokens=10, task_text=task)

    rival_reloaded = lib.get(rival.id)
    assert rival_reloaded.status == "retired"
    assert np.allclose(
        np.asarray(rival_reloaded.learned_embedding, dtype=np.float32),
        np.asarray(rival_before, dtype=np.float32),
        atol=1e-6,
    )


# ---------------------------------------------------------------------------
# Embedding remains unit-length after inhibition. The cosine math the rest
# of the system depends on assumes unit-norm vectors.
# ---------------------------------------------------------------------------


def test_inhibited_embedding_is_unit_length(lib, lateral_on):
    task = "fix calculator add function"
    seed = embedding.encode("fix arithmetic bug").tolist()
    winner = Skill(name="w", trigger="fix arithmetic bug",
                   body="x", learned_embedding=seed)
    rival = Skill(name="r", trigger="rewrite arithmetic module",
                  body="x", learned_embedding=seed)
    lib.store(winner)
    lib.store(rival)

    lib.update_fitness(winner.id, success=True, tokens=10, task_text=task)

    rival_after = np.asarray(lib.get(rival.id).learned_embedding,
                             dtype=np.float32)
    norm = float(np.linalg.norm(rival_after))
    assert abs(norm - 1.0) < 1e-4, f"expected unit length, got {norm}"
