"""FORGIA pezzo #240 — Wave 39: deep-clone of a skill.

Useful for A/B testing: clone an existing promoted skill, tweak its
body/preconditions, run trials on the clone. Original stays in
production; clone starts as candidate.

The clone:
  - has a fresh id
  - inherits all content (name, body, trigger, pre, post) — name
    can be overridden via the `new_name` kwarg
  - lineage: parent_skills includes the original's id
  - status: "candidate" (must earn promotion through trials)
  - trials/successes: reset to 0 (clean slate)
"""
from __future__ import annotations

from engram.skill import Skill


def test_clone_has_new_id():
    from engram.skill_clone import clone_skill

    original = Skill(id="orig", name="orig_name")
    cloned = clone_skill(original)
    assert cloned.id != original.id


def test_clone_preserves_name_by_default():
    from engram.skill_clone import clone_skill

    original = Skill(id="orig", name="my_skill")
    cloned = clone_skill(original)
    assert cloned.name == "my_skill"


def test_clone_with_new_name():
    from engram.skill_clone import clone_skill

    original = Skill(id="orig", name="old")
    cloned = clone_skill(original, new_name="new_v2")
    assert cloned.name == "new_v2"


def test_clone_parent_includes_original():
    from engram.skill_clone import clone_skill

    original = Skill(id="orig", name="x", parent_skills=["grandparent"])
    cloned = clone_skill(original)
    # The clone's lineage includes the ORIGINAL (not the original's
    # parent — that would skip a generation).
    assert "orig" in cloned.parent_skills


def test_clone_status_reset_to_candidate():
    from engram.skill_clone import clone_skill

    original = Skill(id="orig", name="x", status="promoted")
    cloned = clone_skill(original)
    assert cloned.status == "candidate"


def test_clone_trials_reset():
    from engram.skill_clone import clone_skill

    original = Skill(id="orig", name="x", trials=50, successes=40)
    cloned = clone_skill(original)
    assert cloned.trials == 0
    assert cloned.successes == 0


def test_clone_preserves_content_fields():
    from engram.skill_clone import clone_skill

    original = Skill(
        id="orig", name="x", body="body text",
        trigger="trigger text", rationale="why",
        preconditions=["pre"], postconditions=["post"],
    )
    cloned = clone_skill(original)
    assert cloned.body == "body text"
    assert cloned.trigger == "trigger text"
    assert cloned.preconditions == ["pre"]
    assert cloned.postconditions == ["post"]


def test_clone_compiled_macro_not_copied():
    """compiled_macro is empirical (derived from successful traces).
    The clone has no successful runs yet, so it shouldn't inherit
    the parent's macro."""
    from engram.skill_clone import clone_skill

    original = Skill(
        id="orig", name="x",
        compiled_macro={"steps": ["a", "b"]},
    )
    cloned = clone_skill(original)
    assert cloned.compiled_macro is None
