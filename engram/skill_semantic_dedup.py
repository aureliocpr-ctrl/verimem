"""Semantic skill duplicate detection.

Complements `skill_signature.find_duplicate_skills` (which does SHA1 of
normalized trigger||body — catches *literal* duplicates only).

The audit on 2026-05-12 of the live corpus found two ``Provide Final
Answer`` skills with identical name and near-identical purpose but
slightly different trigger text — the SHA1 detector missed them.
This module catches that class via cosine similarity on trigger
embeddings.

**Honest scope (what this is and isn't):**

What it IS:
  - A *sensor*: it surfaces near-identical skills the SHA1 detector
    misses. Read-only. Never writes to the DB.
  - A *classifier*: each returned pair is tagged ``noise_clone`` (one
    side has 0 episode references — safe to retire) /
    ``degenerate`` (both 0-ref — pure noise) / ``hot_clone`` (both
    actively used — needs human review).
  - The first non-trivial cleanup signal the project had: 318-skill
    live corpus surfaced 50 pairs (42 degenerate, 4 noise, 4 hot)
    with 27 safe-to-retire skills.

What it is NOT:
  - A *health score boost*. The corpus health formula doesn't
    penalise zero-reference candidate skills, so removing the
    27 noise clones leaves the score nominally unchanged. The
    benefit is downstream: future consolidation passes have less
    noise to reason over, and ``hippo_recall`` becomes marginally
    more precise on the affected topics.
  - A *merger*. Hot-clones (eg. the 3 ``Provide Final Answer``
    variants with 86/87/134 episodes each) cannot be deduped here —
    that needs careful merging of the ``skills_used`` JSON lists in
    every episode, plus fitness recomputation, plus rollback. Out of
    scope; a separate merge tool with dry-run is the right place.

API:
    load_skills_with_embeddings(library)
        Join SkillLibrary.all() with persisted trigger_embedding
        BLOBs (the dataclass does NOT carry the vector in memory).

    load_episode_reference_counts(data_dir)
        Read every episodes.skills_used and count references per
        skill_id. Cached implicitly by the OS page cache.

    find_semantic_duplicate_skills(skills_with_emb, ref_counts=None, *, ...)
        Vectorised O(S^2) cosine over D=384 vectors. When ref_counts
        is provided, each pair is classified noise/hot/degenerate.
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path

import numpy as np

from . import embedding
from .skill import Skill, SkillLibrary


def load_skills_with_embeddings(
    library: SkillLibrary | None = None,
) -> list[tuple[Skill, np.ndarray]]:
    """Join ``SkillLibrary.all()`` with the persisted ``trigger_embedding``.

    The default ``Skill`` dataclass doesn't expose ``trigger_embedding``
    as an attribute — it's stored only in the SQLite row. This helper
    issues one read-only query and pairs every Skill with its vector.

    Returns ``[(skill, ndarray), ...]``. Skills without a stored vector
    are silently dropped from the result so downstream callers can
    skip the size check.
    """
    library = library or SkillLibrary()
    skills = library.all()
    db_path = Path(library.db_path) if hasattr(library, "db_path") else None
    if db_path is None:
        # Inspect first connection-yielding method to grab path
        db_path = Path(library._db_path)  # type: ignore[attr-defined]

    emb_by_id: dict[str, np.ndarray] = {}
    with sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True) as c:
        c.row_factory = sqlite3.Row
        for row in c.execute("SELECT id, trigger_embedding FROM skills"):
            blob = row["trigger_embedding"]
            if blob is None or len(blob) == 0:
                continue
            emb_by_id[row["id"]] = embedding.deserialize(blob)

    return [(s, emb_by_id[s.id]) for s in skills if s.id in emb_by_id]


def load_episode_reference_counts(
    data_dir: Path | str | None = None,
) -> Counter[str]:
    """Count how many episodes reference each skill_id via skills_used JSON.

    Returns a Counter; missing keys count as 0. Read-only, ~50 ms on
    a 547-episode corpus.
    """
    if data_dir is None:
        from .config import CONFIG
        data_dir = CONFIG.data_dir
    ep_db = Path(data_dir) / "episodes" / "episodes.db"
    counts: Counter[str] = Counter()
    if not ep_db.exists():
        return counts
    with sqlite3.connect(f"file:{ep_db.as_posix()}?mode=ro", uri=True) as c:
        for row in c.execute(
            "SELECT skills_used FROM episodes WHERE skills_used IS NOT NULL"
        ):
            try:
                for sid in json.loads(row[0]):
                    counts[sid] += 1
            except (json.JSONDecodeError, TypeError):
                continue
    return counts


def _classify_pair(ra: int, rb: int) -> str:
    """Tag a duplicate pair by reference imbalance.

    - degenerate: both sides 0-ref. Pure dust. Safe to retire both,
      or merge to one for tidiness; no functional impact either way.
    - noise_clone: exactly one side 0-ref. Loser is safe to retire.
    - hot_clone: both sides >=1 ref. Real semantic duplicate that
      gets independently invoked. Needs a careful merge (episode
      reference rewrite + fitness recomputation).
    """
    if ra == 0 and rb == 0:
        return "degenerate"
    if ra == 0 or rb == 0:
        return "noise_clone"
    return "hot_clone"


def find_semantic_duplicate_skills(
    skills_with_emb: list[tuple[Skill, np.ndarray]],
    ref_counts: Counter[str] | None = None,
    *,
    threshold: float = 0.95,
    top_k: int = 50,
    exclude_retired: bool = True,
) -> dict[str, object]:
    """Find pairs of skills whose trigger embeddings are nearly identical.

    Args:
        skills_with_emb: list of ``(skill, embedding_vector)`` tuples.
            Use :func:`load_skills_with_embeddings` to build it.
        ref_counts: optional Counter mapping skill_id -> episode-reference
            count (see :func:`load_episode_reference_counts`). When
            provided, every returned pair is tagged ``classification``
            in ``{degenerate, noise_clone, hot_clone}`` and the
            ``safe_to_retire`` field names the 0-reference loser (or
            None for hot_clones, which need manual merge).
        threshold: cosine ≥ this counts as a duplicate (default 0.95).
            Calibrated on the live corpus: ReAct-format skills share
            0.88-0.92 similarity but are intentionally distinct.
        top_k: cap on returned pairs (sorted by cosine desc).
        exclude_retired: skip pairs where either side is retired.

    Returns:
        ``{n_total_skills, n_scanned, threshold, pairs,
        summary?}`` where each pair is ``{skill_a, skill_b, name_a,
        name_b, status_a, status_b, fitness_a, fitness_b, trials_a,
        trials_b, cosine, merge_recommendation, classification?,
        ref_count_a?, ref_count_b?, safe_to_retire?}``. When
        ``ref_counts`` is provided, ``summary`` aggregates pair
        classification counts and the set of safe-to-retire IDs.

    Complexity: O(S²) cosine on D=384 embeddings — ~150 ms on 320
    skills, well under the MCP call budget.
    """
    pool: list[tuple[Skill, np.ndarray]] = []
    n_total = len(skills_with_emb)
    for s, emb in skills_with_emb:
        if exclude_retired and getattr(s, "status", None) == "retired":
            continue
        v = np.asarray(emb, dtype=np.float32)
        if v.size == 0:
            continue
        pool.append((s, v))

    if len(pool) < 2:
        return {
            "n_total_skills": n_total,
            "n_scanned": len(pool),
            "threshold": threshold,
            "pairs": [],
        }

    # Vectorised: stack into matrix and compute upper triangle of
    # cosine similarity in one shot.
    mat = np.stack([e for _, e in pool])         # (N, D)
    # Vectors are L2-normalised on encode, so dot product = cosine.
    sim = mat @ mat.T                            # (N, N)

    pairs: list[dict[str, object]] = []
    n = len(pool)
    class_counts: Counter[str] = Counter()
    safe_to_retire: set[str] = set()
    for i in range(n):
        for j in range(i + 1, n):
            c = float(sim[i, j])
            if c < threshold:
                continue
            a, b = pool[i][0], pool[j][0]
            keep = a if _fitness(a) >= _fitness(b) else b
            entry: dict[str, object] = {
                "skill_a": a.id, "skill_b": b.id,
                "name_a": a.name, "name_b": b.name,
                "status_a": a.status, "status_b": b.status,
                "fitness_a": round(_fitness(a), 3),
                "fitness_b": round(_fitness(b), 3),
                "trials_a": getattr(a, "trials", 0),
                "trials_b": getattr(b, "trials", 0),
                "cosine": round(c, 4),
                "merge_recommendation": keep.id,
            }
            if ref_counts is not None:
                ra = ref_counts.get(a.id, 0)
                rb = ref_counts.get(b.id, 0)
                cls = _classify_pair(ra, rb)
                entry["classification"] = cls
                entry["ref_count_a"] = ra
                entry["ref_count_b"] = rb
                if cls == "noise_clone":
                    loser = a.id if ra == 0 else b.id
                    entry["safe_to_retire"] = loser
                    safe_to_retire.add(loser)
                elif cls == "degenerate":
                    # Both 0; pick the lower-fitness one for retirement
                    loser = a.id if _fitness(a) <= _fitness(b) else b.id
                    entry["safe_to_retire"] = loser
                    safe_to_retire.add(loser)
                else:  # hot_clone
                    entry["safe_to_retire"] = None
                class_counts[cls] += 1
            pairs.append(entry)

    pairs.sort(key=lambda p: -float(p["cosine"]))
    out: dict[str, object] = {
        "n_total_skills": n_total,
        "n_scanned": len(pool),
        "threshold": threshold,
        "pairs": pairs[:top_k],
    }
    if ref_counts is not None:
        out["summary"] = {
            "by_classification": dict(class_counts),
            "n_safe_to_retire": len(safe_to_retire),
            "safe_to_retire_ids": sorted(safe_to_retire),
        }
    return out


def _fitness(s: Skill) -> float:
    trials = getattr(s, "trials", 0) or 0
    successes = getattr(s, "successes", 0) or 0
    return successes / trials if trials else 0.0


__all__ = [
    "find_semantic_duplicate_skills",
    "load_skills_with_embeddings",
    "load_episode_reference_counts",
]
