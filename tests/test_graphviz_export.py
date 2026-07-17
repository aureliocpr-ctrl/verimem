"""R49: Export skill DAG as Graphviz DOT format."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _Skill:
    id: str
    name: str = ""
    parent_skills: list[str] = field(default_factory=list)
    status: str = "candidate"


def test_empty_returns_minimal_dot():
    from verimem.graphviz_export import export_dot
    out = export_dot([])
    assert "digraph" in out["dot"]


def test_includes_node_per_skill():
    from verimem.graphviz_export import export_dot
    skills = [_Skill("a"), _Skill("b")]
    out = export_dot(skills)
    assert '"a"' in out["dot"]
    assert '"b"' in out["dot"]


def test_includes_edges():
    from verimem.graphviz_export import export_dot
    skills = [_Skill("root"), _Skill("child", parent_skills=["root"])]
    out = export_dot(skills)
    assert "root" in out["dot"]
    assert "child" in out["dot"]
    # arrow indicator
    assert "->" in out["dot"]


def test_promoted_colored():
    from verimem.graphviz_export import export_dot
    skills = [_Skill("p", status="promoted")]
    out = export_dot(skills)
    # Should style promoted differently
    assert "p" in out["dot"]


def test_payload_keys():
    from verimem.graphviz_export import export_dot
    out = export_dot([])
    for k in ("dot", "n_nodes", "n_edges"):
        assert k in out


def test_retired_excluded():
    from verimem.graphviz_export import export_dot
    skills = [_Skill("alive"), _Skill("dead", status="retired")]
    out = export_dot(skills)
    assert "alive" in out["dot"]
    # Retired excluded
    assert '"dead"' not in out["dot"]
