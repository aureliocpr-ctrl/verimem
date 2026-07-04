"""Auto-derive STRIPS preconditions/postconditions from episode
sequences.

FORGIA pezzo #213 — Wave 12. The STRIPS schema (#209) defines
`Skill.preconditions` and `Skill.postconditions` but the live skill
library has them empty (a v1 schema). Manually filling 318 skills
is impractical. We can bootstrap from data.

Heuristic (zero LLM):
  - Postcondition `after_<skill_id>` is ALWAYS added — it's the
    trivial "I ran" marker, lets STRIPS chain skills together.
  - Precondition `after_<X>` is added IF X is the IMMEDIATE
    predecessor of the target skill in ≥ `threshold` fraction of
    episodes where the target appears.

This is auto-supervised structural learning: we re-use the SR
signal we already have (transition statistics) to seed the
symbolic STRIPS layer. Once 60-70% of skills have derived
predicates, the planner becomes useful on the real corpus.

Why immediate predecessor only? Multi-step ancestry would over-
trigger preconditions (e.g. A→B→C would make A a precondition of
C, but C only really needs B's effects to be true). The
immediate-predecessor rule keeps the predicate graph tight.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any


def _self_marker(skill_id: str) -> str:
    return f"after_{skill_id}"


def derive_predicates_from_episodes(
    skill_id: str,
    *,
    episodes: Iterable[Any],
    threshold: float = 0.5,
) -> tuple[list[str], list[str]]:
    """Auto-derive `(preconditions, postconditions)` for a skill from
    episode sequences.

    Args:
      - `skill_id`: target skill whose predicates we're deriving.
      - `episodes`: iterable of episode-like objects that expose
        `.skills_used` (list[str]).
      - `threshold`: minimum fraction of `target`'s appearances in
        which a predecessor must immediately precede it to qualify
        as a derived precondition. Default 0.5 — moderate. Use 0.7
        for high-precision, 0.3 for high-recall bootstrapping.

    Returns: `(preconditions, postconditions)` — each a list of
    strings sorted for deterministic output.

    Edge cases:
      - No episodes / target not seen → `([], [after_<skill_id>])`.
      - Self-predecessor (`X→X`) is filtered (no circular pre).
      - First-position appearances contribute to "occurrences" but
        provide no predecessor.
    """
    if not (0.0 <= threshold <= 1.0):
        raise ValueError(f"threshold must be in [0, 1]; got {threshold}")

    target_occurrences = 0
    predecessor_counts: Counter[str] = Counter()

    for ep in episodes:
        seq = getattr(ep, "skills_used", None) or []
        prev: str | None = None
        for cur in seq:
            if cur == skill_id:
                target_occurrences += 1
                if prev is not None and prev != skill_id:
                    predecessor_counts[prev] += 1
            prev = cur

    pre: list[str] = []
    if target_occurrences > 0:
        for predecessor, count in predecessor_counts.items():
            if count / target_occurrences >= threshold:
                pre.append(_self_marker(predecessor))

    pre.sort()
    post = [_self_marker(skill_id)]
    return pre, post


def derive_predicates_batch(
    *,
    agent: Any,
    threshold: float = 0.5,
    n_episodes: int = 5000,
    apply: bool = False,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Run `derive_predicates_from_episodes` on EVERY skill in the
    library. Bootstrap the predicate graph from the existing episode
    corpus in one sweep — game-changer for STRIPS-on-real-data.

    Optimization: a single pass over the episodes builds a global
    `(predecessor, successor) -> count` index. Per-skill lookup is
    then O(unique_predecessors). Total cost O(E + S * unique_pre)
    instead of O(E * S).

    Args:
      - `agent`: must expose `.skills.all()` and `.memory.all(limit)`.
      - `threshold`: passed to per-skill derivation.
      - `n_episodes`: cap on how far back to look in episode history.
      - `apply`: when True, persists derived predicates via
        `agent.skills.store(skill)`. False = dry-run.
      - `overwrite`: when True, replaces ANY existing predicates on
        the skill. False = only fill skills with EMPTY pre/post,
        skip ones already populated (audit-friendly default).

    Returns: `{stats, skills}` where `stats` is the aggregate
    summary and `skills` is a list of per-skill records
    `{id, name, preconditions, postconditions, applied}`.
    """
    skills_store = getattr(agent, "skills", None)
    memory = getattr(agent, "memory", None)
    if skills_store is None or not hasattr(skills_store, "all"):
        return {
            "stats": {
                "n_skills_processed": 0, "n_with_preconditions": 0,
                "n_skipped_existing": 0, "applied": apply,
            },
            "skills": [],
        }

    all_skills = list(skills_store.all())
    episodes_all = []
    if memory is not None and hasattr(memory, "all"):
        try:
            episodes_all = memory.all(limit=n_episodes)
        except Exception:
            episodes_all = []

    # Single-pass index: (predecessor, target) -> count + total target occurrences.
    pair_count: dict[tuple[str, str], int] = {}
    target_count: dict[str, int] = {}
    for ep in episodes_all:
        seq = getattr(ep, "skills_used", None) or []
        prev: str | None = None
        for cur in seq:
            target_count[cur] = target_count.get(cur, 0) + 1
            if prev is not None and prev != cur:
                pair_count[(prev, cur)] = (
                    pair_count.get((prev, cur), 0) + 1
                )
            prev = cur

    n_with_pre = 0
    n_skipped = 0
    out_skills: list[dict[str, Any]] = []

    for sk in all_skills:
        sid = sk.id
        # Compute predicates from the global index.
        target_n = target_count.get(sid, 0)
        pre: list[str] = []
        if target_n > 0:
            for (predecessor, target), count in pair_count.items():
                if target == sid and (count / target_n) >= threshold:
                    pre.append(_self_marker(predecessor))
        pre.sort()
        post = [_self_marker(sid)]

        # Skip-existing logic.
        had_existing = bool(sk.preconditions) or bool(sk.postconditions)
        applied_this = False
        if apply and (overwrite or not had_existing):
            sk.preconditions = list(pre)
            sk.postconditions = list(post)
            try:
                skills_store.store(sk)
                applied_this = True
            except Exception:
                applied_this = False
        elif had_existing and not overwrite:
            n_skipped += 1

        if pre:
            n_with_pre += 1

        out_skills.append({
            "id": sid,
            "name": getattr(sk, "name", ""),
            "preconditions": pre,
            "postconditions": post,
            "applied": applied_this,
        })

    return {
        "stats": {
            "n_skills_processed": len(all_skills),
            "n_with_preconditions": n_with_pre,
            "n_skipped_existing": n_skipped,
            "applied": apply,
            "threshold": threshold,
            "n_episodes_used": len(episodes_all),
        },
        "skills": out_skills,
    }


__all__ = ["derive_predicates_from_episodes", "derive_predicates_batch"]
