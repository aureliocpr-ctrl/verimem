"""Fail-closed gate + honest L4-skipped advisory on sourced writes (2026-07-18).

Three adversarial-critic rounds settled the design. Attempts to ADMIT a sourced
write whose shape trips an L1 detector all failed: a lexical "source-echo" was
broken twice on subject-substitution, and treating the mere PRESENCE of a
`source` as legitimacy is unsafe because `source` is caller-controlled and
unverified (spoofable, exactly like the writer_role the trusted-hook bypass had
to token-gate). Admitting a confab that simply attaches a source is the failure
the gate exists to prevent.

Contract (fail-closed, the safe default for verified memory):
* a claim whose shape trips L1 is QUARANTINED whether or not a source is
  attached — the presence of an unverified source never downgrades an L1 hit;
* when a `source` is attached but NO grounding judge is configured, the write
  additionally carries an explicit `L4-skipped` advisory ("grounding not
  verified"), so the caller knows the source-entailment moat did not run and
  that the local CE is unreliable on non-English text;
* the honest recovery path for a real documental fact is an LLM grounding judge
  (L4): with one, a confab the source does not support is quarantined by
  L4-grounding, and a truly entailed fact passes.
"""
from __future__ import annotations

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


def test_sourced_shape_claim_is_quarantined_fail_closed():
    """An unverified source does NOT downgrade an L1 hit (spoof-safe)."""
    r = _gate(
        "La Rev C (approvata il 22/05/2026) del capannone Lotto 3 "
        "prescrive carico neve 1.50 kN/m2.",
        source=SOURCE_APPROVAL,
    )
    assert r.action in ("downgrade", "reject"), (
        f"a sourced shape-claim must stay fail-closed quarantined, got "
        f"{r.action} with warnings {r.warnings}"
    )


def test_sourced_write_without_judge_carries_explicit_advisory():
    """No judge -> the write carries an explicit 'grounding not verified'
    advisory so the missing moat is visible."""
    r = _gate(
        "La Rev C (approvata il 22/05/2026) del capannone Lotto 3 "
        "prescrive carico neve 1.50 kN/m2.",
        source=SOURCE_APPROVAL, ground_write=True,
    )
    from verimem.grounding_gate import _resolve_backend
    if _resolve_backend() == "local":
        import pytest
        pytest.skip("local CE judge present: L4 ran, no L4-skipped advisory")
    skips = [w for w in (r.warnings or []) if w.get("layer") == "L4-skipped"]
    assert skips, (
        f"sourced write with no judge must carry an L4-skipped advisory, "
        f"warnings: {r.warnings}"
    )


class _RejectingJudge:
    """A grounding judge that always reports no entailment (score 0)."""
    def complete(self, system, messages, **kw):  # pragma: no cover - shape only
        return "0"


def test_confab_is_quarantined_when_judge_rejects_entailment():
    """The real filter: with a judge that rejects entailment, a sourced confab
    is quarantined by L4-grounding."""
    r = run_validation_gate(
        proposition="Il modulo di pagamento e stato approvato dal comitato.",
        verified_by=None, topic=None, agent=None,
        source="Verbale comitato: il modulo di autenticazione e stato "
               "approvato. Il modulo di pagamento resta in revisione.",
        grounding_llm=_RejectingJudge(), ground_write=True,
    )
    assert r.action in ("downgrade", "reject"), (
        f"a confab the judge rejects must be quarantined, got {r.action}"
    )
    assert any(w.get("layer") == "L4-grounding" for w in (r.warnings or [])), (
        f"the quarantine must come from L4-grounding, got {r.warnings}"
    )


def test_unsourced_shape_claim_stays_quarantined():
    r = _gate("La Rev C e stata approvata il 22/05/2026.")
    assert r.action != "persist", f"unsourced approval must stay gated, got {r.action}"


def test_unsourced_confab_stays_quarantined():
    r = _gate("Everything works perfectly and every test is green.")
    assert r.action != "persist", f"unsourced hype must stay gated, got {r.action}"
