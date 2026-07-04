"""R9: Hierarchical schema abstraction.

When the same RULE PATTERN appears across different domains, extract
the cross-domain template. This is the "schema" stage of skills:
abstract patterns transferable to new domains.

Example: 3 rules "Prefer X over Y in this context" across pentest,
code review, architecture → abstract schema "prefer X over Y".
"""
from __future__ import annotations


def test_extract_template_finds_common_pattern():
    from engram.schema_abstraction import extract_template

    rules = [
        "Prefer `crtsh` over `nmap` in this context",
        "Prefer `tsc-strict` over `tsc-loose` in this context",
        "Prefer `snapshot-svc` over `event-log` in this context",
    ]
    out = extract_template(rules)
    assert out is not None
    assert "prefer" in out["template"].lower()
    assert "over" in out["template"].lower()


def test_extract_template_returns_none_when_no_pattern():
    from engram.schema_abstraction import extract_template

    rules = [
        "Use TypeScript strict mode",
        "Run nmap with -sS flag",
        "Always commit before refactoring",
    ]
    out = extract_template(rules)
    # No common token-level pattern → None
    assert out is None


def test_template_with_slots():
    from engram.schema_abstraction import extract_template

    rules = [
        "Prefer `crtsh` over `nmap`",
        "Prefer `python` over `bash`",
        "Prefer `safe` over `risky`",
    ]
    out = extract_template(rules)
    assert out is not None
    # Template should contain slots
    assert "<" in out["template"] or "_" in out["template"] or "X" in out["template"]


def test_payload_includes_instances():
    from engram.schema_abstraction import extract_template

    rules = ["Prefer A over B", "Prefer C over D"]
    out = extract_template(rules)
    assert out is not None
    assert "instances" in out
    assert len(out["instances"]) == 2


def test_find_cross_domain_schemas():
    """Multiple skill clusters, each with template > 1 instance."""
    from dataclasses import dataclass

    from engram.schema_abstraction import find_cross_domain_schemas
    @dataclass
    class _Skill:
        id: str
        name: str
        body: str
        stage: str = "compiled"
        status: str = "promoted"

    skills = [
        _Skill("s1", "recon", "Prefer crtsh over nmap"),
        _Skill("s2", "review", "Prefer tsc-strict over tsc-loose"),
        _Skill("s3", "design", "Prefer snapshot over event-log"),
        _Skill("s4", "other", "Just a random skill body"),
    ]
    out = find_cross_domain_schemas(skills, min_instances=2)
    assert out["n_schemas"] >= 1
    # The "Prefer X over Y" template should have 3 instances
    found = False
    for sc in out["schemas"]:
        if sc["n_instances"] >= 3:
            found = True
    assert found


def test_min_instances_threshold():
    from dataclasses import dataclass

    from engram.schema_abstraction import find_cross_domain_schemas
    @dataclass
    class _Skill:
        id: str
        body: str
        name: str = "n"
        stage: str = "compiled"
        status: str = "promoted"

    skills = [
        _Skill("s1", "Prefer A over B"),
    ]
    out = find_cross_domain_schemas(skills, min_instances=2)
    # Only 1 instance — no schema
    assert out["n_schemas"] == 0


def test_payload_shape():
    from engram.schema_abstraction import (
        extract_template,
        find_cross_domain_schemas,
    )

    out1 = find_cross_domain_schemas([])
    for k in ("schemas", "n_schemas", "n_skills_scanned"):
        assert k in out1

    out2 = extract_template(["A", "B"])
    # Could be None — that's fine
    if out2 is not None:
        for k in ("template", "instances", "n_instances"):
            assert k in out2
