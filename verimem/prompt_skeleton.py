"""R40: Build a prompt skeleton from memory tiers.

For a task, retrieve relevant memory items and assemble into a
markdown-formatted prompt ready for an LLM. The skeleton includes:
  - TASK header
  - "What we remember" facts section
  - "Past episodes" with outcomes
  - "Skills to consider" with triggers

Designed as a warm-up for LLM calls: the model starts with rich
context, not from zero.
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
    return len(a & b) / len(a | b)


def build_prompt_skeleton(
    *,
    task: str,
    episodes: list[Any],
    facts: list[Any],
    skills: list[Any],
    top_k_each: int = 3,
    min_sim: float = 0.15,
) -> dict[str, Any]:
    """Assemble a markdown prompt seeded with memory context."""
    q_tokens = _tokens(task)

    # Pick top-K facts
    fact_scored = []
    for f in facts:
        sim = _jaccard(q_tokens, _tokens(getattr(f, "proposition", "")))
        if sim >= min_sim:
            fact_scored.append((sim, f))
    fact_scored.sort(key=lambda x: -x[0])
    top_facts = [f for _, f in fact_scored[:top_k_each]]

    # Top episodes
    ep_scored = []
    for e in episodes:
        sim = _jaccard(q_tokens, _tokens(getattr(e, "task_text", "")))
        if sim >= min_sim:
            ep_scored.append((sim, e))
    ep_scored.sort(key=lambda x: -x[0])
    top_eps = [e for _, e in ep_scored[:top_k_each]]

    # Top skills (promoted only)
    sk_scored = []
    for s in skills:
        if getattr(s, "status", "") == "retired":
            continue
        sim = _jaccard(q_tokens, _tokens(getattr(s, "trigger", "")))
        if sim >= min_sim:
            sk_scored.append((sim, s))
    sk_scored.sort(key=lambda x: -x[0])
    top_skills = [s for _, s in sk_scored[:top_k_each]]

    # Build markdown
    lines: list[str] = [
        "# Task", task, "",
    ]
    if top_facts:
        lines.append("## What we remember")
        for f in top_facts:
            topic = getattr(f, "topic", "")
            prop = getattr(f, "proposition", "")[:160]
            lines.append(f"- _[{topic}]_ {prop}")
        lines.append("")
    if top_eps:
        lines.append("## Past episodes")
        for e in top_eps:
            outcome = getattr(e, "outcome", "?")
            marker = "✓" if outcome == "success" else "✗"
            t = getattr(e, "task_text", "")[:80]
            ans = getattr(e, "final_answer", "")[:120]
            lines.append(f"- {marker} _{t}_: {ans}")
        lines.append("")
    if top_skills:
        lines.append("## Skills to consider")
        for s in top_skills:
            sid = getattr(s, "id", "")
            trig = getattr(s, "trigger", "")[:80]
            body = getattr(s, "body", "")[:100]
            lines.append(f"- `{sid}` trigger: _{trig}_")
            if body:
                lines.append(f"  body: {body}")
        lines.append("")
    lines.append("## Plan")
    lines.append("Considering the above memory, propose the next step:")

    prompt = "\n".join(lines)

    return {
        "prompt": prompt,
        "components": {
            "task": task,
            "facts": [getattr(f, "id", "") for f in top_facts],
            "episodes": [getattr(e, "id", "") for e in top_eps],
            "skills": [getattr(s, "id", "") for s in top_skills],
        },
        "n_facts_cited": len(top_facts),
        "n_episodes_cited": len(top_eps),
        "n_skills_cited": len(top_skills),
    }


__all__ = ["build_prompt_skeleton"]
