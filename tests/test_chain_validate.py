"""FORGIA pezzo #223 — Wave 22: skill chain validation.

Given an initial state and a proposed skill chain, simulate it
step-by-step verifying preconditions, applying postconditions.
Returns whether the chain is valid AND where it breaks if not.

Useful for:
  - "ho questo piano, è valido?" (sanity check)
  - debug a STRIPS plan after manual editing
  - explain to the user WHY a plan failed
"""
from __future__ import annotations

from verimem.skill import Skill


def test_empty_chain_is_valid_no_op():
    from verimem.chain_validate import validate_chain

    out = validate_chain(initial_state=["x"], skill_chain=[])
    assert out["valid"] is True
    assert out["broken_at"] is None
    assert set(out["final_state"]) == {"x"}


def test_valid_chain_step_by_step():
    from verimem.chain_validate import validate_chain

    chain = [
        Skill(id="auth", name="auth",
              preconditions=["have_creds"],
              postconditions=["logged_in"]),
        Skill(id="fetch", name="fetch",
              preconditions=["logged_in"],
              postconditions=["data_loaded"]),
    ]
    out = validate_chain(
        initial_state=["have_creds"],
        skill_chain=chain,
    )
    assert out["valid"] is True
    assert out["broken_at"] is None
    assert "logged_in" in out["final_state"]
    assert "data_loaded" in out["final_state"]


def test_chain_breaks_at_unmet_precondition():
    from verimem.chain_validate import validate_chain

    chain = [
        Skill(id="auth", name="auth",
              preconditions=["have_creds"],
              postconditions=["logged_in"]),
        Skill(id="fetch", name="fetch",
              preconditions=["DIFFERENT_predicate"],
              postconditions=["data_loaded"]),
    ]
    out = validate_chain(
        initial_state=["have_creds"],
        skill_chain=chain,
    )
    assert out["valid"] is False
    assert out["broken_at"] == 1  # second skill (index 1)


def test_first_skill_unmet_pre_breaks_at_zero():
    from verimem.chain_validate import validate_chain

    chain = [
        Skill(id="x", name="x",
              preconditions=["unsatisfied"],
              postconditions=["done"]),
    ]
    out = validate_chain(
        initial_state=["totally_different"],
        skill_chain=chain,
    )
    assert out["valid"] is False
    assert out["broken_at"] == 0


def test_steps_trace_records_every_application():
    from verimem.chain_validate import validate_chain

    chain = [
        Skill(id="a", name="a", preconditions=[], postconditions=["A_done"]),
        Skill(id="b", name="b", preconditions=["A_done"],
              postconditions=["B_done"]),
    ]
    out = validate_chain(initial_state=[], skill_chain=chain)
    assert out["valid"] is True
    assert "steps" in out
    assert len(out["steps"]) == 2
    # First step: applied=True, state grew.
    assert out["steps"][0]["applied"] is True
    assert "A_done" in out["steps"][0]["state_after"]


def test_reason_string_explains_break():
    from verimem.chain_validate import validate_chain

    chain = [
        Skill(id="x", name="needs_login",
              preconditions=["logged_in"],
              postconditions=["finished"]),
    ]
    out = validate_chain(initial_state=[], skill_chain=chain)
    assert out["valid"] is False
    assert "logged_in" in out["reason"] or \
        "needs_login" in out["reason"]


def test_payload_shape_complete():
    from verimem.chain_validate import validate_chain

    out = validate_chain(initial_state=[], skill_chain=[])
    for k in ("valid", "broken_at", "final_state", "steps", "reason"):
        assert k in out
