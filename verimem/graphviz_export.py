"""R49: Skill DAG → Graphviz DOT export."""
from __future__ import annotations

from typing import Any

_STATUS_STYLE = {
    "promoted": 'style=filled,fillcolor="#90EE90"',
    "candidate": 'style=filled,fillcolor="#FFE4B5"',
}


def export_dot(skills: list[Any]) -> dict[str, Any]:
    """Return {dot, n_nodes, n_edges}."""
    lines: list[str] = ["digraph SkillDAG {", "  rankdir=LR;"]
    n_nodes = 0
    n_edges = 0
    ids = set()
    for s in skills:
        if getattr(s, "status", "") == "retired":
            continue
        ids.add(getattr(s, "id", ""))
        n_nodes += 1
    for s in skills:
        sid = getattr(s, "id", "")
        if sid not in ids:
            continue
        label = (getattr(s, "name", sid) or sid)[:30]
        style = _STATUS_STYLE.get(getattr(s, "status", ""), "")
        attrs = f'label="{label}"'
        if style:
            attrs += "," + style
        lines.append(f'  "{sid}" [{attrs}];')
    for s in skills:
        sid = getattr(s, "id", "")
        if sid not in ids:
            continue
        for p in getattr(s, "parent_skills", []) or []:
            if p in ids:
                lines.append(f'  "{p}" -> "{sid}";')
                n_edges += 1
    lines.append("}")
    return {
        "dot": "\n".join(lines),
        "n_nodes": n_nodes,
        "n_edges": n_edges,
    }


__all__ = ["export_dot"]
