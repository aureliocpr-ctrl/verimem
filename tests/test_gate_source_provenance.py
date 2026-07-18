"""Source-provenance rule for the L1 shape detectors (vertical probe 2026-07-18).

The L1.x "lacks evidence" detectors target an AGENT confabulating the state of
ITS OWN work with no provenance ("shipped / approved / tested / monitored").
A write that DECLARES a ``source=`` is a different act — provenance is on the
record — so the filter of record shifts from L1 (claim SHAPE) to L4 (semantic
source⊢fact grounding):

* a sourced write is NOT L1-escalated (it stays recallable);
* when a grounding judge is present, L4 decides entailment — a confab the
  source does not support is quarantined by L4;
* when NO judge is configured, the write is admitted but carries an explicit
  ``L4-skipped`` advisory: honestly labelled "grounding not verified", never
  passed off as verified;
* an UNSOURCED claim is unchanged — L1 still fail-closed quarantines it.

History (why not a lexical heuristic): an earlier "source-echo" attempt tried
to disarm L1 by matching the keyword in the source text. The adversarial critic
broke it twice — a subject-substitution confab ("il pagamento è approvato" over
a source that approves only "l'autenticazione" and says payment "resta in
revisione") echoes the keyword and even shares the document's date anchor. No
lexical test binds the keyword to its subject; and the local CE judge scores
that IT confab 99.9/100, so it cannot rescue it either. The honest contract is
therefore: don't pretend to verify what only a real judge can — admit with a
loud "not verified" flag, and let L4 (LLM judge) be the filter of record.
"""
from __future__ import annotations

import pytest

from verimem.anti_confab_gate import run_validation_gate

SOURCE_APPROVAL = (
    "Relazione di calcolo Rev C del 18/05/2026, capannone logistico Lotto 3, "
    "APPROVATA dal collaudatore ing. Mancini il 22/05/2026: carico neve "
    "1.50 kN/m2, acciaio S355."
)


def _gate(proposition, source=None, grounding_llm=None, ground_write=None):
    return run_validation_gate(
        proposition=proposition, verified_by=None, topic=None, agent=None,
        source=source, grounding_llm=grounding_llm, ground_write=ground_write)


# ── sourced writes are admitted (filter shifts to L4) ──────────────────────
def test_sourced_shape_claim_is_admitted_not_l1_quarantined():
    """A documental write with an L1 keyword ('approvata') stays recallable —
    L1 does not quarantine a write that declares its provenance."""
    r = _gate(
        "La Rev C (approvata il 22/05/2026) del capannone Lotto 3 "
        "prescrive carico neve 1.50 kN/m2.",
        source=SOURCE_APPROVAL,
    )
    assert r.action == "persist", (
        f"a sourced write must not be L1-quarantined, got {r.action} "
        f"with warnings {r.warnings}"
    )


def test_sourced_write_without_judge_carries_explicit_unverified_advisory():
    """No judge → the admission is honestly flagged 'grounding not verified'."""
    r = _gate(
        "La Rev C (approvata il 22/05/2026) del capannone Lotto 3 "
        "prescrive carico neve 1.50 kN/m2.",
        source=SOURCE_APPROVAL,
        ground_write=True,
    )
    from verimem.grounding_gate import _resolve_backend
    if _resolve_backend() == "local":
        pytest.skip("local CE judge present: L4 ran, no L4-skipped advisory")
    skips = [w for w in (r.warnings or []) if w.get("layer") == "L4-skipped"]
    assert skips, (
        f"sourced write with no judge must carry an explicit L4-skipped "
        f"advisory, warnings: {r.warnings}"
    )


# ── the real filter is L4 with a judge; a confab the source contradicts
#    is quarantined when the judge rejects entailment ────────────────────────
class _RejectingJudge:
    """A grounding judge that always reports the source does NOT entail the
    proposition (score 0). Stands in for an LLM judge on a confab."""
    def complete(self, system, messages, **kw):  # pragma: no cover - shape only
        return "0"


def test_confab_is_quarantined_when_judge_rejects_entailment():
    """With a judge that rejects entailment, a sourced confab is quarantined by
    L4 — the grounding gate is the filter of record."""
    r = run_validation_gate(
        proposition="Il modulo di pagamento è stato approvato dal comitato.",
        verified_by=None, topic=None, agent=None,
        source="Verbale comitato: il modulo di autenticazione è stato "
               "approvato. Il modulo di pagamento resta in revisione.",
        grounding_llm=_RejectingJudge(),
        ground_write=True,
    )
    assert r.action in ("downgrade", "reject"), (
        f"a confab the judge rejects must be quarantined by L4, got {r.action} "
        f"with warnings {r.warnings}"
    )
    assert any(w.get("layer") == "L4-grounding" for w in (r.warnings or [])), (
        f"the quarantine must come from L4-grounding, got {r.warnings}"
    )


# ── unsourced claims: fail-closed, unchanged ───────────────────────────────
def test_unsourced_shape_claim_stays_quarantined():
    """No declared provenance → L1 still fail-closed quarantines the claim."""
    r = _gate("La Rev C è stata approvata il 22/05/2026.")
    assert r.action != "persist", (
        f"unsourced approval claim must stay gated, got {r.action}"
    )


def test_unsourced_confab_stays_quarantined():
    r = _gate("Everything works perfectly and every test is green.")
    assert r.action != "persist", (
        f"unsourced hype confab must stay gated, got {r.action}"
    )
