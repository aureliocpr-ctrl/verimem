"""Skill diff markdown renderer.

FORGIA pezzo #243 — Wave 42. Renders a side-by-side comparison of
two skills as markdown. Useful before merging near-duplicates.
"""
from __future__ import annotations

from .skill import Skill


def _list_diff(a: list[str], b: list[str]) -> str:
    """Compact representation of two list values."""
    return f"`{sorted(a) or '(none)'}` vs `{sorted(b) or '(none)'}`"


def _fmt(v: object, dp: int = 2) -> str:
    if isinstance(v, float):
        return f"{v:.{dp}f}"
    return str(v)


def render_skill_diff(a: Skill, b: Skill) -> str:
    """Render a markdown side-by-side of two skills."""
    lines: list[str] = []
    lines.append(
        f"## Skill diff: `{a.name}` (`{a.id}`) vs `{b.name}` (`{b.id}`)"
    )
    lines.append("")
    lines.append("| Field | A | B |")
    lines.append("|-------|---|---|")
    lines.append(f"| name | {a.name} | {b.name} |")
    lines.append(f"| status | {a.status} | {b.status} |")
    lines.append(f"| stage | {a.stage} | {b.stage} |")
    lines.append(f"| version | {a.version} | {b.version} |")
    lines.append(f"| trials | {a.trials} | {b.trials} |")
    lines.append(f"| successes | {a.successes} | {b.successes} |")
    lines.append(
        f"| fitness_mean | {_fmt(a.fitness_mean)} | "
        f"{_fmt(b.fitness_mean)} |"
    )
    lines.append(
        f"| preconditions | "
        f"`{sorted(a.preconditions) or '(none)'}` | "
        f"`{sorted(b.preconditions) or '(none)'}` |"
    )
    lines.append(
        f"| postconditions | "
        f"`{sorted(a.postconditions) or '(none)'}` | "
        f"`{sorted(b.postconditions) or '(none)'}` |"
    )
    lines.append(
        f"| parent_skills | "
        f"{sorted(a.parent_skills) or '(none)'} | "
        f"{sorted(b.parent_skills) or '(none)'} |"
    )

    # Trigger / body comparison (truncated).
    a_trig = (a.trigger or "")[:80]
    b_trig = (b.trigger or "")[:80]
    lines.append(f"| trigger | {a_trig} | {b_trig} |")

    lines.append("")
    # Diff summary.
    diffs = 0
    for attr in ("name", "status", "stage", "version", "trials",
                  "successes", "trigger", "body"):
        if getattr(a, attr, None) != getattr(b, attr, None):
            diffs += 1
    for attr in ("preconditions", "postconditions", "parent_skills"):
        if sorted(getattr(a, attr) or []) != sorted(
            getattr(b, attr) or []
        ):
            diffs += 1
    lines.append(f"**Differences**: {diffs} field(s) differ.")

    return "\n".join(lines)


__all__ = ["render_skill_diff"]
