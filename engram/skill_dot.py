"""Graphviz DOT export of the skill library.

FORGIA pezzo #219 — Wave 18. Renders the skill library (optionally
with lineage edges) as a DOT string the user can pipe to
`dot -Tpng > skills.png` for a visual overview.

Color coding by status:
  - promoted → darkgreen
  - candidate → gray
  - retired → red

Pure string generation. No graphviz Python dep needed at runtime
(only the `dot` CLI for rendering, which is optional).
"""
from __future__ import annotations

from .skill import Skill

_STATUS_COLOR = {
    "promoted": "darkgreen",
    "candidate": "gray",
    "retired": "red",
}


def _escape_label(label: str) -> str:
    """Escape characters that break DOT label syntax."""
    return (label or "").replace("\\", "\\\\").replace('"', '\\"')


def skills_to_dot(
    skills: list[Skill],
    *,
    include_lineage: bool = True,
    max_skills: int = 200,
) -> str:
    """Generate a Graphviz DOT representation of the skill library.

    Args:
      - `skills`: list of Skill objects.
      - `include_lineage`: when True, draws `parent -> child` edges
        from `parent_skills` (only edges where BOTH endpoints are
        in the visible set).
      - `max_skills`: cap on visible nodes (skills are taken in the
        order given; pre-sort for stable rendering).

    Returns: DOT-format string.
    """
    visible = list(skills)[:max_skills]
    by_id = {s.id: s for s in visible}
    lines = [
        "digraph SkillLibrary {",
        "  rankdir=LR;",
        '  node [shape=box, style=filled, fillcolor=white];',
    ]
    for s in visible:
        color = _STATUS_COLOR.get(s.status, "black")
        label = _escape_label(s.name or s.id)
        lines.append(
            f'  "{s.id}" [label="{label}", color={color}, '
            f'fontcolor={color}];'
        )
    if include_lineage:
        for s in visible:
            for parent in (s.parent_skills or []):
                if parent in by_id:
                    lines.append(f'  "{parent}" -> "{s.id}";')
    lines.append("}")
    return "\n".join(lines)


__all__ = ["skills_to_dot"]
