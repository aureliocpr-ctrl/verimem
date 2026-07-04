"""Structured query over the skill library.

FORGIA pezzo #217 — Wave 16. Pragmatic alternative to a full DSL:
explicit kwargs the caller composes. Easier to validate against
JSON-schema, no parser needed, MCP-friendly.

Returns a filtered + sorted + capped `list[Skill]`. PURELY LOCAL
(uses only `Skill.fitness_mean`, `last_used_at`, etc).
"""
from __future__ import annotations

from .skill import Skill, SkillStatus

_SORT_KEYS = {
    "fitness": lambda s: float(getattr(s, "fitness_mean", 0.0)),
    "trials": lambda s: int(getattr(s, "trials", 0)),
    "recency": lambda s: float(getattr(s, "last_used_at", 0.0)),
    "name": lambda s: (getattr(s, "name", "") or "").lower(),
}


def query_skills(
    skills: list[Skill],
    *,
    status: SkillStatus | None = None,
    min_trials: int | None = None,
    max_trials: int | None = None,
    min_fitness: float | None = None,
    max_fitness: float | None = None,
    name_contains: str | None = None,
    has_predicates: bool | None = None,
    has_compiled_macro: bool | None = None,
    sort_by: str = "fitness",
    desc: bool = True,
    limit: int = 50,
) -> list[Skill]:
    """Filter + sort + cap the given skill list.

    Filters AND together. None means "no filter on this dimension".

    Args:
      - `status`: candidate / promoted / retired.
      - `min_trials` / `max_trials`: inclusive bounds on `trials`.
      - `min_fitness` / `max_fitness`: inclusive bounds on
        `fitness_mean`.
      - `name_contains`: case-insensitive substring on `name`.
      - `has_predicates`: True → both pre AND post non-empty;
        False → at least one empty.
      - `has_compiled_macro`: True → `compiled_macro` is non-None.
      - `sort_by`: one of `fitness | trials | recency | name`.
        Unknown keys fall back to `fitness`.
      - `desc`: descending sort (default True).
      - `limit`: cap on result list (default 50).

    Returns: list of skills.
    """
    out: list[Skill] = []
    for s in skills:
        if status is not None and getattr(s, "status", None) != status:
            continue
        trials = int(getattr(s, "trials", 0))
        if min_trials is not None and trials < min_trials:
            continue
        if max_trials is not None and trials > max_trials:
            continue
        fm = float(getattr(s, "fitness_mean", 0.0))
        if min_fitness is not None and fm < min_fitness:
            continue
        if max_fitness is not None and fm > max_fitness:
            continue
        if name_contains is not None:
            name = (getattr(s, "name", "") or "").lower()
            if name_contains.lower() not in name:
                continue
        if has_predicates is not None:
            pre = list(getattr(s, "preconditions", []) or [])
            post = list(getattr(s, "postconditions", []) or [])
            both_set = bool(pre) and bool(post)
            if has_predicates and not both_set:
                continue
            if not has_predicates and both_set:
                continue
        if has_compiled_macro is not None:
            cm = getattr(s, "compiled_macro", None)
            has_cm = cm is not None
            if has_compiled_macro and not has_cm:
                continue
            if not has_compiled_macro and has_cm:
                continue
        out.append(s)

    # Sort.
    keyfn = _SORT_KEYS.get(sort_by, _SORT_KEYS["fitness"])
    out.sort(key=keyfn, reverse=desc)

    return out[:limit]


__all__ = ["query_skills"]
