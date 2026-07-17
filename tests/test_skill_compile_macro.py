"""FORGIA pezzo #253 — Wave 52: skill compile macro.

For a SCHEMA-stage skill (composed via #235 compose_macro), extract
a deterministic compiled_macro from its parent_skills sequence.
Stores it on the skill so the fast-path can bypass LLM next time.
"""
from __future__ import annotations

from verimem.skill import Skill


class _FakeSkillsStore:
    def __init__(self, skills: list[Skill]) -> None:
        self._by_id = {s.id: s for s in skills}
        self.stored: list[Skill] = []

    def get(self, sid: str) -> Skill | None:
        return self._by_id.get(sid)

    def store(self, s: Skill) -> None:
        self._by_id[s.id] = s
        self.stored.append(s)


class _FakeAgent:
    def __init__(self, skills: list[Skill]) -> None:
        self.skills = _FakeSkillsStore(skills)


def test_unknown_returns_not_found():
    from verimem.skill_compile_macro import compile_macro

    a = _FakeAgent([])
    out = compile_macro(skill_id="ZZZ", agent=a)
    assert out["found"] is False


def test_non_schema_skill_skipped():
    from verimem.skill_compile_macro import compile_macro

    sk = Skill(id="x", name="x", stage="nrem")
    a = _FakeAgent([sk])
    out = compile_macro(skill_id="x", agent=a)
    assert out["compiled"] is False


def test_schema_with_empty_parents_no_macro():
    from verimem.skill_compile_macro import compile_macro

    sk = Skill(id="x", name="x", stage="schema",
               parent_skills=[])
    a = _FakeAgent([sk])
    out = compile_macro(skill_id="x", agent=a)
    # Empty parent chain → no useful macro.
    assert out["compiled"] is False


def test_schema_compiles_from_parents():
    from verimem.skill_compile_macro import compile_macro

    parents = [
        Skill(id="a", name="step_a"),
        Skill(id="b", name="step_b"),
        Skill(id="c", name="step_c"),
    ]
    schema = Skill(
        id="meta", name="meta", stage="schema",
        parent_skills=["a", "b", "c"],
    )
    a = _FakeAgent([*parents, schema])
    out = compile_macro(skill_id="meta", agent=a, apply=True)
    assert out["compiled"] is True
    assert len(out["steps"]) == 3
    # Order preserved.
    assert [s["skill_id"] for s in out["steps"]] == ["a", "b", "c"]


def test_apply_persists_compiled_macro():
    from verimem.skill_compile_macro import compile_macro

    parents = [Skill(id="a", name="a"), Skill(id="b", name="b")]
    schema = Skill(id="m", name="m", stage="schema",
                    parent_skills=["a", "b"])
    a = _FakeAgent([*parents, schema])
    compile_macro(skill_id="m", agent=a, apply=True)
    sk = a.skills.get("m")
    assert sk.compiled_macro is not None


def test_dry_run_no_mutation():
    from verimem.skill_compile_macro import compile_macro

    parents = [Skill(id="a", name="a")]
    schema = Skill(id="m", name="m", stage="schema",
                    parent_skills=["a"])
    # Single-parent edge case: too few to make a useful macro.
    a = _FakeAgent([*parents, schema])
    out = compile_macro(skill_id="m", agent=a, apply=False)
    # No macro stored.
    sk = a.skills.get("m")
    assert sk.compiled_macro is None


def test_payload_shape_complete():
    from verimem.skill_compile_macro import compile_macro

    a = _FakeAgent([])
    out = compile_macro(skill_id="x", agent=a)
    for k in ("skill_id", "found", "compiled", "steps", "applied"):
        assert k in out
