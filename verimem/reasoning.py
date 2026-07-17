"""Composite reasoning orchestrator over the skill library.

FORGIA pezzo #212 — Wave 11. Combines the four lenses HippoAgent has
(semantic recall, SR forward planning, STRIPS chaining, structural
analogy) into a single call: `reason_about_task(...)`.

The host LLM (Claude Code) gets a structured dict it can inspect to
pick its move with much more information than just "top-1 semantic
match". All four sections run independently and degrade gracefully:
empty input → empty section, never an exception.

Cost: O(corpus_size) for recall + O(N²) for forward (N = unique
skills in recent episodes) + O(skill_count × max_depth) for STRIPS
+ O(corpus) for analogy. For ≤ 1000 skills and ≤ 5000 episodes,
this is < 200 ms total — fast enough to call on every turn that
might benefit from reasoning.

This is **PURE LOCAL** — no LLM call inside. Compatible with HOSTED
MODE (FORGIA #206).
"""
from __future__ import annotations

from typing import Any

from .analogy import find_structural_analogues
from .strips import plan_strips
from .successor_repr import build_transition_matrix, forward_plan


def _safe_recall(agent: Any, task: str, k: int) -> list[tuple]:
    """Try the agent's semantic-retrieval surface. Different code
    paths exist (`skills.retrieve`, `memory.recall`, `recall_skills`
    on the agent itself). Returns `[(skill, score), ...]` or `[]`."""
    skills_store = getattr(agent, "skills", None)
    if skills_store is None:
        return []
    if hasattr(skills_store, "retrieve"):
        try:
            return list(skills_store.retrieve(task, k=k)) or []
        except Exception:
            return []
    if hasattr(skills_store, "recall_skills"):
        try:
            return list(skills_store.recall_skills(task, k=k)) or []
        except Exception:
            return []
    return []


def _summarise(payload: dict[str, Any]) -> str:
    """Compose a deterministic 1-paragraph summary the host LLM can
    show the user (or use as additional context). Stable across
    runs given the same input (no timestamps, no random ids in the
    text other than what the input already has)."""
    parts: list[str] = []
    parts.append(f"Task: {payload['task']!r}")
    if payload["recall"]:
        top_names = ", ".join(
            r["name"] for r in payload["recall"][:3]
        )
        parts.append(
            f"Top recall ({len(payload['recall'])} skill): {top_names}"
        )
    else:
        parts.append("Recall: no skill matches the task semantically.")
    if payload["forward_plans"]:
        n = len(payload["forward_plans"])
        top = payload["forward_plans"][0]
        path_str = " -> ".join(top["path"])
        parts.append(
            f"Forward SR ({n} plan): top trajectory {path_str} "
            f"(prob={top['prob']:.3f})"
        )
    if payload["strips_plan"] is not None:
        n_steps = len(payload["strips_plan"])
        chain = " -> ".join(s["name"] for s in payload["strips_plan"])
        parts.append(
            f"STRIPS plan ({n_steps} step): {chain}"
        )
    if payload["analogues"]:
        names = ", ".join(a["name"] for a in payload["analogues"][:3])
        parts.append(f"Structural analogues: {names}")
    return "; ".join(parts) + "."


def reason_about_task(
    task: str,
    *,
    agent: Any,
    initial_state: list[str] | None = None,
    goal_state: list[str] | None = None,
    k_recall: int = 3,
    forward_depth: int = 3,
    forward_beam: int = 3,
    forward_n_episodes: int = 500,
    strips_max_depth: int = 5,
    analogy_min_structural: float = 0.3,
    analogy_max_semantic: float = 0.6,
    analogy_top_k: int = 3,
    analogy_cosine_fn: Any = None,
) -> dict[str, Any]:
    """Run all 4 reasoning lenses on the task and return a structured
    composite. See module docstring.

    Args:
      - `task`: natural-language task description (used for recall).
      - `agent`: HippoAgent instance (or duck-type with `.skills` and
        `.memory`).
      - `initial_state` / `goal_state`: STRIPS predicate sets. When
        BOTH provided, runs `plan_strips`; otherwise STRIPS skipped.
      - `forward_*`: parameters for `forward_plan`. Skipped when
        recall is empty (no seed skill).
      - `analogy_*`: thresholds + size for `find_structural_analogues`.
        `analogy_cosine_fn` lets the caller inject a semantic-cosine
        function; defaults to `lambda a, b: 0.0` (no semantic filter)
        when not provided — the caller can wire in
        `verimem.embedding.encode` for real cosine.
      - `k_recall`: top-k semantic matches.

    Returns: dict with keys
      - `task` (str)
      - `recall` (list of `{id, name, score}`)
      - `forward_plans` (list of `{path, log_prob, prob}` — empty if
        no seed)
      - `strips_plan` (list of `{id, name, preconditions, postconditions}`
        or None if not requested / not found)
      - `analogues` (list of `{id, name, structural, semantic}`)
      - `summary` (deterministic str)
    """
    payload: dict[str, Any] = {
        "task": task,
        "recall": [],
        "forward_plans": [],
        "strips_plan": None,
        "analogues": [],
        "summary": "",
    }

    # ----- 1. SEMANTIC RECALL ------------------------------------------
    recall_pairs = _safe_recall(agent, task, k=k_recall)
    payload["recall"] = [
        {"id": s.id, "name": s.name, "score": float(score)}
        for s, score in recall_pairs
    ]

    top_skill = recall_pairs[0][0] if recall_pairs else None

    # ----- 2. FORWARD SR PLANNING --------------------------------------
    if top_skill is not None:
        episodes_all = []
        try:
            mem = getattr(agent, "memory", None)
            if mem is not None and hasattr(mem, "all"):
                episodes_all = mem.all(limit=forward_n_episodes)
        except Exception:
            episodes_all = []
        sequences = [
            ep.skills_used for ep in episodes_all
            if getattr(ep, "skills_used", None)
        ]
        if sequences:
            ids, P = build_transition_matrix(sequences)
            if top_skill.id in ids:
                import math
                raw = forward_plan(
                    top_skill.id, ids, P,
                    depth=forward_depth, beam_width=forward_beam,
                )
                payload["forward_plans"] = [
                    {
                        "path": list(path),
                        "log_prob": float(lp),
                        "prob": float(math.exp(lp)),
                    }
                    for path, lp in raw
                ]

    # ----- 3. STRIPS PLANNING ------------------------------------------
    if initial_state is not None and goal_state is not None:
        skills_store = getattr(agent, "skills", None)
        if skills_store is not None and hasattr(skills_store, "all"):
            pool = skills_store.all()
            plan = plan_strips(
                initial_state=list(initial_state),
                goal_state=list(goal_state),
                skills=pool,
                max_depth=strips_max_depth,
            )
            if plan is not None:
                payload["strips_plan"] = [
                    {
                        "id": s.id,
                        "name": s.name,
                        "preconditions": list(s.preconditions),
                        "postconditions": list(s.postconditions),
                    }
                    for s in plan
                ]

    # ----- 4. STRUCTURAL ANALOGY ---------------------------------------
    if top_skill is not None:
        skills_store = getattr(agent, "skills", None)
        if skills_store is not None and hasattr(skills_store, "all"):
            pool = skills_store.all()
            cos_fn = analogy_cosine_fn or (lambda a, b: 0.0)
            analogues = find_structural_analogues(
                top_skill, pool,
                semantic_cosine_fn=cos_fn,
                min_structural=analogy_min_structural,
                max_semantic=analogy_max_semantic,
                top_k=analogy_top_k,
            )
            payload["analogues"] = [
                {
                    "id": cand.id,
                    "name": cand.name,
                    "structural": float(info["structural"]),
                    "semantic": float(info["semantic"]),
                }
                for cand, info in analogues
            ]

    # ----- 5. SUMMARY --------------------------------------------------
    payload["summary"] = _summarise(payload)
    return payload


__all__ = ["reason_about_task"]
