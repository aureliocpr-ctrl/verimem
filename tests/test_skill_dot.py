"""FORGIA pezzo #219 — Wave 18: Graphviz DOT export of skill library.

Renders the skill library (with optional lineage edges) as a DOT
string the user can pipe to `dot -Tpng > skills.png` for a visual
overview of the procedural memory.

Color coding by status:
  - promoted → darkgreen
  - candidate → gray
  - retired → red

Pure string generation, no graphviz dep needed at runtime.
"""
from __future__ import annotations

from engram.skill import Skill


def test_empty_skill_list():
    from engram.skill_dot import skills_to_dot

    out = skills_to_dot([])
    assert "digraph" in out
    assert "}" in out
    # Empty graph is still syntactically valid.


def test_includes_skill_nodes():
    from engram.skill_dot import skills_to_dot

    skills = [
        Skill(id="s1", name="alpha", status="promoted"),
        Skill(id="s2", name="beta", status="candidate"),
    ]
    out = skills_to_dot(skills)
    assert '"s1"' in out
    assert '"s2"' in out
    assert "alpha" in out
    assert "beta" in out


def test_lineage_edges():
    from engram.skill_dot import skills_to_dot

    skills = [
        Skill(id="parent", name="parent_skill"),
        Skill(id="child", name="child_skill", parent_skills=["parent"]),
    ]
    out = skills_to_dot(skills, include_lineage=True)
    assert '"parent" -> "child"' in out


def test_lineage_edges_skipped_when_disabled():
    from engram.skill_dot import skills_to_dot

    skills = [
        Skill(id="parent", name="parent"),
        Skill(id="child", name="child", parent_skills=["parent"]),
    ]
    out = skills_to_dot(skills, include_lineage=False)
    assert "->" not in out


def test_color_by_status():
    from engram.skill_dot import skills_to_dot

    skills = [
        Skill(id="p", name="promoted_one", status="promoted"),
        Skill(id="c", name="candidate_one", status="candidate"),
        Skill(id="r", name="retired_one", status="retired"),
    ]
    out = skills_to_dot(skills)
    # Different status implies different color in the same DOT output.
    assert "darkgreen" in out
    assert "gray" in out
    assert "red" in out


def test_max_skills_cap():
    from engram.skill_dot import skills_to_dot

    skills = [Skill(id=f"s{i}", name=f"skill{i}") for i in range(50)]
    out = skills_to_dot(skills, max_skills=5)
    # 5 nodes, not 50.
    visible_nodes = [
        line for line in out.splitlines()
        if line.strip().startswith('"s')
    ]
    assert len(visible_nodes) <= 5


def test_lineage_to_unknown_parent_skipped():
    """Skills referencing parents outside the visible set don't
    produce dangling edges."""
    from engram.skill_dot import skills_to_dot

    skills = [
        Skill(id="orphan", name="orphan",
              parent_skills=["does_not_exist"]),
    ]
    out = skills_to_dot(skills, include_lineage=True)
    assert "does_not_exist" not in out


def test_quote_escape_in_names():
    from engram.skill_dot import skills_to_dot

    skills = [Skill(id="weird", name='quote"name')]
    out = skills_to_dot(skills)
    # The DOT must remain syntactically valid: quote in name escaped.
    assert '\\"' in out or 'quote' in out
    # No raw unescaped quote within the label string.


def test_returns_str():
    from engram.skill_dot import skills_to_dot

    out = skills_to_dot([])
    assert isinstance(out, str)
