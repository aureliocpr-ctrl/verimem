"""R10: Skill Composer — auto-plan multi-skill chain for a new task.

Given a task description and a skill library, produce a plan: an
ordered sequence of skills that — when composed — should accomplish
the task. Foundation for true planning/attack-chain auto-generation.

Algorithm:
  1. For each non-retired skill, compute Jaccard match between
     skill.trigger tokens and task tokens.
  2. Filter to skills above min_match_score.
  3. Expand each matched skill with its parents (parent_skills,
     recursive) — parents come BEFORE children in execution order.
  4. Topological sort to respect dependencies.

Returns: list of {skill_id, match_score, role} where role is
"parent" or "matched".
"""
from __future__ import annotations

import re
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def compose_plan(
    *,
    task: str,
    skills: list[Any],
    min_match_score: float = 0.1,
    top_k: int = 10,
) -> dict[str, Any]:
    """Return an ordered plan of skill_ids to apply to `task`."""
    task_tokens = _tokens(task)
    if not task_tokens or not skills:
        return {
            "plan": [],
            "coverage": 0.0,
            "n_skills_scanned": len(skills),
            "n_skills_matched": 0,
        }

    skills_by_id: dict[str, Any] = {getattr(s, "id", ""): s for s in skills}

    # Match each non-retired skill by trigger Jaccard
    scored: list[tuple[float, Any]] = []
    for s in skills:
        if getattr(s, "status", "") == "retired":
            continue
        trig_tokens = _tokens(getattr(s, "trigger", ""))
        score = _jaccard(trig_tokens, task_tokens)
        if score >= min_match_score:
            scored.append((score, s))
    scored.sort(key=lambda t: -t[0])
    top = scored[:top_k]

    if not top:
        return {
            "plan": [],
            "coverage": 0.0,
            "n_skills_scanned": len(skills),
            "n_skills_matched": 0,
        }

    # Expand with parents (recursive). Track each entry's role
    plan_entries: dict[str, dict[str, Any]] = {}
    for score, s in top:
        sid = getattr(s, "id", "")
        if sid not in plan_entries:
            plan_entries[sid] = {
                "skill_id": sid,
                "match_score": round(score, 3),
                "role": "matched",
                "trigger": getattr(s, "trigger", "")[:80],
            }
        # Walk parents (BFS, cycle-safe)
        seen = {sid}
        stack = list(getattr(s, "parent_skills", []) or [])
        while stack:
            pid = stack.pop(0)
            if pid in seen or pid not in skills_by_id:
                continue
            seen.add(pid)
            psk = skills_by_id[pid]
            if getattr(psk, "status", "") == "retired":
                continue
            if pid not in plan_entries:
                plan_entries[pid] = {
                    "skill_id": pid,
                    "match_score": 0.0,
                    "role": "parent",
                    "trigger": getattr(psk, "trigger", "")[:80],
                }
            for pp in getattr(psk, "parent_skills", []) or []:
                if pp not in seen:
                    stack.append(pp)

    # Topological sort: parents BEFORE children
    sorted_ids: list[str] = []
    visited: set[str] = set()

    def _visit(sid: str) -> None:
        if sid in visited or sid not in plan_entries:
            return
        visited.add(sid)
        skl = skills_by_id.get(sid)
        if skl:
            for pid in getattr(skl, "parent_skills", []) or []:
                if pid in plan_entries:
                    _visit(pid)
        sorted_ids.append(sid)

    # Start from matched skills (highest score first), DFS post-order
    for entry in sorted(plan_entries.values(),
                        key=lambda e: -e["match_score"]):
        _visit(entry["skill_id"])

    plan = [plan_entries[sid] for sid in sorted_ids]
    # Coverage: weighted by match scores of matched entries
    matched_scores = [
        e["match_score"] for e in plan_entries.values()
        if e["role"] == "matched"
    ]
    coverage = (sum(matched_scores) / len(matched_scores)
                if matched_scores else 0.0)

    return {
        "plan": plan,
        "coverage": round(coverage, 3),
        "n_skills_scanned": len(skills),
        "n_skills_matched": len([e for e in plan if e["role"] == "matched"]),
    }


__all__ = ["compose_plan"]
