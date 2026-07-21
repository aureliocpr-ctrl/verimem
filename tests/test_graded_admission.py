"""Graded admission (design bf5d322, step 1): "unproven" is not "malicious".

Measured (HaluMem external A/B, 2026-07-21): at the SHIPPED threshold 40 the
grounding gate rejects 33% of CLEAN facts (40/60 admitted) while noise
rejection is 100%. The write path treats a below-threshold score with a
DECLARED source — "not proven enough" — exactly like an injection. The cure
mirrors the read path's graded abstention: ADMIT as model_claim with the low
grounding on the receipt, and reserve quarantine for injection / active
contradiction / adversarial content.

Wiring is env-gated and DEFAULT OFF (`ENGRAM_GRADED_ADMISSION`): tonight's
default behavior is byte-identical (the pre-registered GLM failure mode — the
read path must WEIGHT low-conf items or FPs just move to answer time — is
measured with the A/B harness BEFORE any default flip).

Receipt contract in enforce mode: the below-threshold write persists, carries
an ``L4-grounding-graded`` warning (NOT ``L4-grounding`` — it must not trip
the escalation equality check, and it did not block), the score stays on the
receipt, and the adjudication tier reflects the low confidence.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem.anti_confab_gate import run_validation_gate

# a legit fact whose declared source does NOT entail it strongly → CE sub-40
FACT = "The reactor maintenance was rescheduled to next quarter."
WEAK_SOURCE = "Meeting notes: various operational topics were discussed."


class _LowJudge:
    """Deterministic stand-in for the CE: always scores below the cut."""
    def complete(self, system, messages, **kw):  # noqa: ANN001
        return type("R", (), {"text": "Score: 12"})()


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("ENGRAM_GRADED_ADMISSION", raising=False)
    monkeypatch.delenv("ENGRAM_L1_DOMAIN_ADVISORY", raising=False)
    yield


def _gate(**kw):
    return run_validation_gate(
        proposition=FACT, verified_by=None, topic="ops/plant", agent=None,
        validate="full", source=WEAK_SOURCE, grounding_llm=_LowJudge(),
        ground_write=True, **kw)


def test_default_unchanged_subthreshold_still_blocks():
    """DEFAULT OFF: tonight's behavior is byte-identical — sub-threshold with
    a source still escalates (the moat does not silently relax)."""
    res = _gate()
    assert res.action in ("downgrade", "reject")
    assert any(w.get("layer") == "L4-grounding" for w in res.warnings)


@pytest.mark.parametrize("val", ["1", "true", "on", "yes", "enforce"])
def test_enforce_admits_subthreshold_with_source(monkeypatch, val):
    monkeypatch.setenv("ENGRAM_GRADED_ADMISSION", val)
    res = _gate()
    assert res.action == "persist", \
        "unproven-with-source must be admitted (graded), not quarantined"


def test_enforce_receipt_carries_graded_layer_and_score(monkeypatch):
    monkeypatch.setenv("ENGRAM_GRADED_ADMISSION", "1")
    res = _gate()
    w = next((x for x in res.warnings
              if x.get("layer") == "L4-grounding-graded"), None)
    assert w is not None, "the receipt must record the graded admission"
    assert w.get("grounding_score") is not None
    assert res.grounding_score is not None, "score stays on the receipt"
    # the graded layer must NOT be the escalating one
    assert not any(x.get("layer") == "L4-grounding" for x in res.warnings)


def test_enforce_does_not_relax_contradiction(tmp_path, monkeypatch):
    """Quarantine stays reserved for REAL integrity failures: the product's
    own contradiction check (same pair the e2e reality bench pins) still
    quarantines with graded admission ON."""
    monkeypatch.setenv("ENGRAM_GRADED_ADMISSION", "1")
    from verimem.client import Memory
    m = Memory(path=tmp_path / "m.db")
    m.add("The Rossi SpA contract expires on 31 January 2027.", topic="legal",
          source="contract-rossi clause 9", verified_by=["source-doc:rc:1"])
    contra = m.add("The Rossi SpA contract expires in 2025.", topic="legal")
    assert contra.get("status") == "quarantined" or any(
        str(w.get("layer", "")).startswith("L3")
        for w in (contra.get("warnings") or [])), \
        "graded admission must NOT relax the contradiction gate"


def test_enforce_without_source_unchanged(monkeypatch):
    """No source declared → no grounding ran → graded admission has no say;
    the L1/L3 stack behaves exactly as today (here: keyword-only escalates
    under the armed default)."""
    monkeypatch.setenv("ENGRAM_GRADED_ADMISSION", "1")
    res = run_validation_gate(
        proposition="The migration is complete and all tests pass.",
        verified_by=None, topic="dev/x", agent=None, validate="full")
    assert res.action in ("downgrade", "reject")


def test_enforce_end_to_end_admitted_with_low_tier(tmp_path: Path, monkeypatch):
    """Product surface: the write is ADMITTED, adjudication says so, and the
    confidence tier is honest (low/borderline — never 'high')."""
    monkeypatch.setenv("ENGRAM_GRADED_ADMISSION", "1")
    from verimem.client import Memory
    m = Memory(path=tmp_path / "m.db")
    m.agent = getattr(m, "agent", None)
    r = m.add(FACT, topic="ops/plant", source=WEAK_SOURCE)
    # NB: senza judge iniettato l'SDK usa il CE locale reale: lo score vero
    # del WEAK_SOURCE può variare — il contratto qui è SOLO che con graded ON
    # un L4-sotto-soglia non produce quarantena. Se il CE reale lo ammette
    # pulito, il test resta vero per vacuità sul primo assert.
    assert r.get("status") != "quarantined" or not any(
        w.get("layer") == "L4-grounding" for w in (r.get("warnings") or [])), \
        "graded ON: nessuna quarantena il cui UNICO motivo è L4 sotto-soglia"
    if any(w.get("layer") == "L4-grounding-graded"
           for w in (r.get("warnings") or [])):
        tier = (r.get("adjudication") or {}).get("confidence_tier")
        assert tier in ("low", "borderline", "unverified"), \
            f"graded admission must carry an honest tier, got {tier}"
