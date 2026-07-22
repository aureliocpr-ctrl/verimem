"""L1 domain-precision carve-out (design (d), env-gated, DEFAULT OFF).

The surgical alternative to re-flipping the L1 default (reverted this morning as
d15e4ca). ENGRAM_L1_DOMAIN_ADVISORY disarms L1 for the WHOLE deployment;
ENGRAM_L1_DOMAIN_PRECISION disarms it ONLY for the individual facts the
subject-based classifier (verimem.subject_extract.is_domain_professional) reads
as third-party PROFESSIONAL facts — an agent's self-claim about its own software
STILL escalates even with the env on. Per-fact, content-based, not a global
switch. Observe-first: the stand-down is recorded on the receipt as
``L1-domain-precision-observe`` (never a block reason nor a ledger credit).

Default OFF: behavior byte-identical. The pre-registered promotion gate is the
vertical corpus + HaluMem measure (roadmap G1/G2), not this file.
"""
from __future__ import annotations

import pytest

from verimem.anti_confab_gate import run_validation_gate

# domain-professional fact that trips L1.13 (completed) — wrongly quarantined
DOMAIN = "The surgical procedure was completed without complications."
# agent self-claim about its own software work — MUST still escalate
AGENT = "The migration is complete and all tests pass."


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("ENGRAM_L1_DOMAIN_PRECISION", raising=False)
    monkeypatch.delenv("ENGRAM_L1_DOMAIN_ADVISORY", raising=False)
    yield


def _gate(text: str):
    return run_validation_gate(
        proposition=text, verified_by=["source-doc:x:1"],
        topic="clinical/x", agent=None, validate="full")


def test_default_on_domain_fact_advisory_with_marker():
    """DEFAULT ON (2026-07-22): the domain fact is admitted, stand-down on the
    receipt. This is the shipped cure — no env needed."""
    res = _gate(DOMAIN)
    assert res.action == "persist"
    assert any(w.get("layer") == "L1-domain-precision-observe"
               for w in res.warnings)


@pytest.mark.parametrize("val", ["0", "false", "off", "no"])
def test_explicit_optout_restores_legacy_escalation(monkeypatch, val):
    """The opt-out: an agent-self-memory deployment that wants the legacy
    always-escalate sets the env to an off value."""
    monkeypatch.setenv("ENGRAM_L1_DOMAIN_PRECISION", val)
    res = _gate(DOMAIN)
    assert res.action == "downgrade"
    assert not any(w.get("layer") == "L1-domain-precision-observe"
                   for w in res.warnings)


@pytest.mark.parametrize("val", ["1", "true", "on", "yes"])
def test_on_domain_fact_becomes_advisory_with_marker(monkeypatch, val):
    monkeypatch.setenv("ENGRAM_L1_DOMAIN_PRECISION", val)
    res = _gate(DOMAIN)
    assert res.action == "persist", "a recognized domain fact must be admitted"
    assert any(w.get("layer") == "L1-domain-precision-observe"
               for w in res.warnings), "the stand-down must be on the receipt"
    # the original L1 keyword warning is still surfaced (advisory, not silent)
    assert any(str(w.get("layer", "")).startswith("L1.") for w in res.warnings)


def test_on_agent_self_claim_still_escalates(monkeypatch):
    """The precision carve-out must NOT relax an agent's own software claim —
    is_domain_professional('the migration ...') is False, so L1 still fires."""
    monkeypatch.setenv("ENGRAM_L1_DOMAIN_PRECISION", "1")
    res = _gate(AGENT)
    assert res.action == "downgrade"
    assert not any(w.get("layer") == "L1-domain-precision-observe"
                   for w in res.warnings)


def test_on_does_not_relax_l4_grounding(monkeypatch):
    """The precision carve-out touches ONLY L1: a domain-subject fact whose
    source does NOT entail it must still be gated by L4, env on."""
    monkeypatch.setenv("ENGRAM_L1_DOMAIN_PRECISION", "1")

    class _Low:
        def complete(self, system, messages, **kw):  # noqa: ANN001
            return type("R", (), {"text": "Score: 5"})()

    res = run_validation_gate(
        proposition="The surgical procedure was completed without complications.",
        verified_by=None, topic="clinical/x", agent=None, validate="full",
        source="Unrelated: the cafeteria menu changes on Fridays.",
        grounding_llm=_Low(), ground_write=True)
    assert res.action in ("downgrade", "reject"), \
        "precision must not disable the L4 grounding gate"


def test_on_first_person_claim_still_escalates(monkeypatch):
    """First-person is agent voice — never domain, always escalates."""
    monkeypatch.setenv("ENGRAM_L1_DOMAIN_PRECISION", "1")
    res = run_validation_gate(
        proposition="I completed the deployment and everything works.",
        verified_by=["source-doc:x:1"], topic="ops/x", agent=None,
        validate="full")
    assert res.action == "downgrade"
