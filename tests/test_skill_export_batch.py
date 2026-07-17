"""FORGIA pezzo #228 — Wave 27: batch skill export.

Existing `hippo_skill_export` exports ONE skill. Batch version
returns ALL skills as portable JSON dicts — same format as the
per-skill export, suitable for backup or migration to another
HippoAgent installation.

Excludes transient fields (learned_embedding, compiled_macro)
unless explicitly requested.
"""
from __future__ import annotations

from verimem.skill import Skill


def test_empty_returns_empty_list():
    from verimem.skill_export import export_all_skills

    out = export_all_skills([])
    assert out["skills"] == []
    assert out["n_total"] == 0


def test_exports_all_skills_by_default():
    from verimem.skill_export import export_all_skills

    skills = [
        Skill(id="a", name="alpha", status="promoted"),
        Skill(id="b", name="beta", status="candidate"),
        Skill(id="c", name="gamma", status="retired"),
    ]
    out = export_all_skills(skills)
    assert out["n_total"] == 3
    ids = {s["id"] for s in out["skills"]}
    assert ids == {"a", "b", "c"}


def test_status_filter():
    from verimem.skill_export import export_all_skills

    skills = [
        Skill(id="a", name="a", status="promoted"),
        Skill(id="b", name="b", status="candidate"),
    ]
    out = export_all_skills(skills, status="promoted")
    assert len(out["skills"]) == 1
    assert out["skills"][0]["id"] == "a"


def test_excludes_transient_fields_by_default():
    """learned_embedding is large + non-portable; excluded by default."""
    from verimem.skill_export import export_all_skills

    skills = [
        Skill(id="a", name="a",
              learned_embedding=[0.1] * 384,
              compiled_macro={"steps": []}),
    ]
    out = export_all_skills(skills)
    record = out["skills"][0]
    assert "learned_embedding" not in record
    assert "compiled_macro" not in record


def test_include_transient_optional():
    from verimem.skill_export import export_all_skills

    skills = [
        Skill(id="a", name="a", learned_embedding=[0.1] * 384),
    ]
    out = export_all_skills(skills, include_transient=True)
    record = out["skills"][0]
    assert "learned_embedding" in record


def test_includes_predicates():
    """STRIPS pre/post (FORGIA #209) preserved in export."""
    from verimem.skill_export import export_all_skills

    skills = [
        Skill(id="a", name="a",
              preconditions=["pre1"], postconditions=["post1"]),
    ]
    out = export_all_skills(skills)
    record = out["skills"][0]
    assert record["preconditions"] == ["pre1"]
    assert record["postconditions"] == ["post1"]


def test_round_trip_via_from_dict():
    """Exported records can be reloaded into Skill instances."""
    from verimem.skill_export import export_all_skills

    skills = [
        Skill(id="a", name="alpha", status="promoted",
              trials=10, successes=8,
              preconditions=["pre"], postconditions=["post"]),
    ]
    out = export_all_skills(skills)
    record = out["skills"][0]
    restored = Skill.from_dict(record)
    assert restored.id == "a"
    assert restored.name == "alpha"
    assert restored.status == "promoted"
    assert restored.preconditions == ["pre"]
    assert restored.postconditions == ["post"]


def test_payload_shape_complete():
    from verimem.skill_export import export_all_skills

    out = export_all_skills([])
    for k in ("skills", "n_total", "schema_version"):
        assert k in out
