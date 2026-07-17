"""Structural analogy over the skill library.

FORGIA pezzo #210 — Pezzo C. The third leg of "ragionare su task
nuovi". Gentner (1983) "Structure-mapping: A theoretical framework
for analogy", Cognitive Science 7:155–170: analogy is matching by
RELATIONAL STRUCTURE, not surface similarity. "Atom is like solar
system" works because both have "smaller things orbit a central
larger thing", not because atoms look like planets.

For HippoAgent: when the user faces a task with NO semantically-
similar skill in the library, we still want to surface skills with
similar PROCEDURAL STRUCTURE that might transfer.

Operationally — minimal viable structural matcher:

  signature(skill) = bag-of-tokens drawn from
      name + trigger + preconditions + postconditions

  jaccard(A, B) = |A ∩ B| / |A ∪ B|

  is_analogue(target, candidate) iff
      structural ≥ θ_struct  (overlap of procedural tokens)
      AND semantic ≤ θ_sem   (NOT a near-duplicate in embedding)

The interesting case is HIGH structural / LOW semantic. High both
means "near duplicate" — uninteresting, the existing semantic
retrieval handles it. High structural with LOW semantic means the
two skills are spoken about in different domains but share the same
procedural shape — the regime where analogy actually adds value.

This is the V1, intentionally simple. Future Pezzo D could swap the
bag-of-tokens for an actual structure-mapping engine (SME, Falkenhainer
1989) that aligns predicate ARGUMENTS, not just token presence — but
the corpus has to be big enough (≥ 1k skills) to justify the cost.
"""
from __future__ import annotations

import re
from collections.abc import Callable

from .skill import Skill

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    """Lowercased alphanumeric tokens. Splits on any non-alphanumeric
    character (whitespace, underscore, hyphen, punctuation) — matches
    the way most skill predicate names are written."""
    return set(_TOKEN_RE.findall(text.lower()))


def structural_signature(skill: Skill) -> set[str]:
    """Bag-of-tokens covering name + trigger + pre + post.

    Empty fields contribute nothing. Lowercased. Deduped (it's a
    set). The signature is the input both for `structural_jaccard`
    and as the comparison key for `find_structural_analogues`.
    """
    parts = [
        skill.name or "",
        skill.trigger or "",
        " ".join(skill.preconditions or []),
        " ".join(skill.postconditions or []),
    ]
    return _tokens(" ".join(parts))


def structural_jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two token sets.

    Convention: if BOTH sets are empty, we return 0.0 (no signal —
    trivially "everything matches everything" is a misleading 1.0).
    """
    if not a and not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union > 0 else 0.0


def find_structural_analogues(
    target: Skill,
    candidates: list[Skill],
    *,
    semantic_cosine_fn: Callable[[Skill, Skill], float],
    min_structural: float = 0.4,
    max_semantic: float = 0.5,
    top_k: int = 5,
) -> list[tuple[Skill, dict[str, float]]]:
    """Find skills structurally similar to `target` but semantically
    distant — the "analogy" regime in Gentner's framework.

    Args:
      - `target`: skill we're trying to match-by-structure.
      - `candidates`: pool of skills to search. The target itself
        (by id) is automatically excluded.
      - `semantic_cosine_fn`: callable `(a, b) -> cosine` returning
        the semantic similarity in [0, 1] of two skills' embeddings.
        Injected so the caller controls the embedding source (e.g.
        the agent's existing `embedding.encode`).
      - `min_structural`: structural Jaccard threshold (default
        0.4 — moderately strict). Set to 0.0 to disable.
      - `max_semantic`: semantic cosine ceiling (default 0.5 — half
        of full match). Skills above this are near-duplicates, not
        analogies. Set to 1.0 to disable.
      - `top_k`: cap on returned analogues (default 5). Sorted by
        descending structural Jaccard.

    Returns: list of `(candidate, info)` tuples sorted by structural
    score descending. `info` carries `{structural, semantic}` so the
    caller can show the user WHY a skill was flagged.
    """
    target_sig = structural_signature(target)
    out: list[tuple[Skill, dict[str, float]]] = []
    for cand in candidates:
        if cand.id == target.id:
            continue
        cand_sig = structural_signature(cand)
        struct = structural_jaccard(target_sig, cand_sig)
        if struct < min_structural:
            continue
        sem = float(semantic_cosine_fn(target, cand))
        if sem > max_semantic:
            continue
        out.append((cand, {"structural": struct, "semantic": sem}))
    out.sort(key=lambda x: -x[1]["structural"])
    return out[:top_k]


__all__ = [
    "structural_signature",
    "structural_jaccard",
    "find_structural_analogues",
]
