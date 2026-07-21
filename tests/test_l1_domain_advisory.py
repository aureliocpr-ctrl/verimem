"""L1.x domain-advisory mode — the measured cure for the 86.7% vertical FP.

benchmark/bench_l1_business_fp.py measured: the 14 L1.x anti-confabulation
detectors, built to police an AGENT's self-claims about its own code work
('it works', 'deployed', 'tests pass'), quarantine 26/30 legitimate
lawyer/engineer/clinician facts on the product ingest path.

Design (kimi + glm design memos 2026-07-21, verified on source):
  - L1.x stays ENFORCING by default — fail-closed, protects the dogfooding
    agent, backward-compatible.
  - The relaxation is SERVER-SIDE and DEPLOYMENT-LEVEL (env
    ENGRAM_L1_DOMAIN_ADVISORY), NEVER a per-write add() argument: a per-write
    flag is 'writer_role without a token' — spoofable by an injected prompt,
    the exact hole the trusted-hook bypass had to token-gate.
  - observe-first: in advisory mode the L1 warnings are STILL computed and
    surfaced in the receipt (measurable), they simply do not ESCALATE to
    quarantine. Reversible by unsetting the env.
  - it relaxes ONLY the L1 keyword family. L3 (contradiction) and L4
    (grounding) are semantic integrity gates and MUST still escalate — a
    domain deployment is not a licence to store contradictions or ungrounded
    claims.
"""
from __future__ import annotations

import pytest

from verimem.anti_confab_gate import run_validation_gate

# a legit vertical fact that trips L1.10 (works) — quarantined at 86.7% today
LEGAL_FACT = "The new arbitration clause works in favour of the tenant."
# a legit vertical fact that trips L1.13 (completion)
ENG_FACT = "The building inspection is finished and the certificate was issued."


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("ENGRAM_L1_DOMAIN_ADVISORY", raising=False)
    # Since the 2026-07-21 default flip, keyword-only is advisory by DEFAULT; the
    # enforcement baseline these tests contrast against now lives under STRICT.
    monkeypatch.setenv("ENGRAM_L1_STRICT", "1")
    yield


def _gate(fact: str, **kw):
    return run_validation_gate(proposition=fact, verified_by=["source-doc:x:1"],
                               topic="t/x", agent=None, validate="full", **kw)


def test_strict_quarantines_the_keyword_fact(monkeypatch):
    """The enforcement baseline: under ENGRAM_L1_STRICT a keyword-only claim
    escalates. (Out of the box, without strict, it is advisory — see
    test_l1_advisory_by_default.py — this file contrasts DOMAIN_ADVISORY against
    the strict baseline.)"""
    res = _gate(LEGAL_FACT)
    assert res.action == "downgrade"
    assert any(str(w.get("layer", "")).startswith("L1") for w in res.warnings)


@pytest.mark.parametrize("val", ["1", "true", "on", "yes"])
def test_advisory_mode_persists_but_keeps_the_warning(monkeypatch, val):
    """The cure: the domain fact is STORED (not quarantined) while the L1
    warning is preserved in the receipt for observability."""
    monkeypatch.setenv("ENGRAM_L1_DOMAIN_ADVISORY", val)
    res = _gate(LEGAL_FACT)
    assert res.action == "persist"            # no longer quarantined
    assert any(str(w.get("layer", "")).startswith("L1") for w in res.warnings), \
        "advisory != silent: the warning must still surface"


def test_advisory_mode_covers_the_whole_l1_family(monkeypatch):
    monkeypatch.setenv("ENGRAM_L1_DOMAIN_ADVISORY", "1")
    assert _gate(ENG_FACT).action == "persist"


@pytest.mark.parametrize("val", ["0", "false", "off", "no", ""])
def test_off_values_keep_enforcing(monkeypatch, val):
    monkeypatch.setenv("ENGRAM_L1_DOMAIN_ADVISORY", val)
    assert _gate(LEGAL_FACT).action == "downgrade"


def test_advisory_does_not_relax_grounding_layer(monkeypatch):
    """L4 grounding is a semantic integrity gate — advisory mode must NOT let an
    ungrounded contradiction through. Here a source that does NOT entail the
    fact must still be gated even in advisory mode."""
    monkeypatch.setenv("ENGRAM_L1_DOMAIN_ADVISORY", "1")

    class _Judge:
        def complete(self, system, messages, **kw):  # noqa: ANN001
            return type("R", (), {"text": "Score: 2"})()   # not entailed

    # a fact with NO L1 keyword, so only the grounding layer can act on it
    res = run_validation_gate(
        proposition="The reactor core temperature is 900 degrees.",
        verified_by=None, topic="t/x", agent=None, validate="full",
        source="Unrelated: the cafeteria menu changes on Fridays.",
        grounding_llm=_Judge(), ground_write=True)
    assert res.action in ("downgrade", "reject"), \
        "advisory mode must not disable the semantic grounding gate"


def test_advisory_dev_claim_still_hits_L4_grounding(monkeypatch):
    """GLM review a-1, the exact fail-open scenario, PINNED: even in domain
    mode a dev-anchored self-claim ('the migration is complete') with a
    grounding judge that finds no support is STILL quarantined by L4. The mode
    relaxes the L1 keyword family, never the semantic grounding gate — the
    fail-open is bounded, not total."""
    monkeypatch.setenv("ENGRAM_L1_DOMAIN_ADVISORY", "1")

    class _Judge:
        def complete(self, system, messages, **kw):  # noqa: ANN001
            return type("R", (), {"text": "Score: 3"})()   # not entailed

    res = run_validation_gate(
        proposition="The migration is complete and all tests pass.",
        verified_by=None, topic="t/x", agent=None, validate="full",
        source="Unrelated: the office cafeteria closes at 3pm.",
        grounding_llm=_Judge(), ground_write=True)
    assert res.action in ("downgrade", "reject"), \
        "L4 grounding must still quarantine an ungrounded dev claim in advisory"


def test_advisory_dev_claim_persists_without_a_judge(monkeypatch):
    """The documented, conscious fail-open: with NO grounding judge configured
    (the plausible domain-deployment setup), the same dev claim persists. This
    is the operator's declared trade-off, tested so it is a decision, not an
    accident — L3 contradiction is the only remaining backstop."""
    monkeypatch.setenv("ENGRAM_L1_DOMAIN_ADVISORY", "1")
    res = _gate("The migration is complete and all tests pass.")
    assert res.action == "persist"
    assert any(str(w.get("layer", "")).startswith("L1") for w in res.warnings), \
        "even in the fail-open the L1 warning must stay on the receipt"


def test_add_has_no_perwrite_advisory_argument():
    """The switch must be server-side: a per-write add() flag would be
    spoofable. Guard against a future 'convenience' kwarg reopening the hole."""
    import inspect

    from verimem.client import Memory
    params = inspect.signature(Memory.add).parameters
    for banned in ("l1_advisory", "domain_advisory", "skip_l1", "advisory"):
        assert banned not in params, \
            f"add() must not expose a spoofable per-write L1 switch: {banned}"
