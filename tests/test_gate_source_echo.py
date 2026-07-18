"""Source-echo disarm for the L1 shape detectors (vertical probe 2026-07-18).

The L1.x "lacks evidence" detectors judge the claim SHAPE against
``verified_by`` tags only — a documental write (``source=``) never enters
their judgment. Real-world consequence certified by the vertical probe:

* "La Rev C (approvata il 22/05/2026) prescrive carico neve 1.50 kN/m2"
  with a source that itself states "APPROVATA dal collaudatore ing. Mancini
  il 22/05/2026" -> QUARANTINED by L1.16 (the truthful, sourced update is
  hidden from recall while, without a judge, a fabricated claim on the same
  source is admitted). The gate blocked the true and admitted the false.

Contract under test:

1. An L1 shape warning whose ``matched_text`` is literally present in the
   provided source WITH THE SAME NEGATION POLARITY is advisory only — the
   write is NOT quarantined by L1 (admission of sourced writes belongs to
   L4 when a judge exists).
2. Polarity guard: if the claim asserts the POSITIVE ("è stata confermata")
   while the source states the NEGATIVE ("NON confermata"), the echo does
   NOT disarm — L1 still quarantines.
3. No echo, no change: an approval claim whose source never mentions any
   approval stays quarantined exactly as before.
4. No source, no change: the pre-existing unsourced behaviour is untouched.
"""
from __future__ import annotations

import pytest

from verimem.anti_confab_gate import run_validation_gate

SOURCE_APPROVAL = (
    "Relazione di calcolo Rev C del 18/05/2026, capannone logistico Lotto 3, "
    "APPROVATA dal collaudatore ing. Mancini il 22/05/2026: carico neve "
    "1.50 kN/m2, acciaio S355."
)

SOURCE_SMENTITA = (
    "Referto 20/06/2026, paziente ID 88412: creatinina 0.95 mg/dL. "
    "Nefrologo: quadro rientrato, sospetta IR lieve NON confermata, "
    "episodio da disidratazione."
)


def _gate(proposition, source=None):
    return run_validation_gate(
        proposition=proposition, verified_by=None, topic=None, agent=None,
        source=source)


def test_sourced_approval_claim_is_not_quarantined_when_source_states_it():
    """Case 1 (the Rev C false positive): approval echoed by the source."""
    r = _gate(
        "La Rev C (approvata il 22/05/2026) del capannone Lotto 3 "
        "prescrive carico neve 1.50 kN/m2.",
        source=SOURCE_APPROVAL,
    )
    assert r.action == "persist", (
        f"sourced approval echoed by the source must persist, got "
        f"{r.action} with warnings {r.warnings}"
    )
    # The shape observation stays visible (advisory), flagged as source-echo.
    echoed = [w for w in (r.warnings or [])
              if w.get("layer") == "L1.16" and w.get("source_echo")]
    assert echoed, "the disarmed L1.16 warning must remain advisory with source_echo=True"


def test_sourced_negative_finding_is_not_quarantined_when_source_states_it():
    """Case 2 (the clinical retraction): negative claim, negative source."""
    r = _gate(
        "La sospetta insufficienza renale del paziente ID 88412 non è stata "
        "confermata: episodio attribuito a disidratazione.",
        source=SOURCE_SMENTITA,
    )
    assert r.action == "persist", (
        f"negated finding echoed by a negated source must persist, got "
        f"{r.action} with warnings {r.warnings}"
    )


def test_polarity_flip_confab_stays_quarantined():
    """'è stata confermata' against a source saying 'NON confermata' must NOT
    be disarmed by the lexical echo — polarity disagrees."""
    r = _gate(
        "La diagnosi di insufficienza renale del paziente ID 88412 è stata "
        "confermata dal nefrologo.",
        source=SOURCE_SMENTITA,
    )
    assert r.action != "persist", (
        f"polarity-flipped claim must stay gated, got {r.action}"
    )


def test_approval_claim_without_echo_stays_quarantined():
    """Approval claim whose source never mentions approval: unchanged."""
    r = _gate(
        "Il progetto del capannone Lotto 3 è stato approvato dal comune.",
        source="Verbale sopralluogo 03/03/2026: rilevate quote piazzale e "
               "posizione pali illuminazione esistenti.",
    )
    assert r.action != "persist", (
        f"approval claim with no echo in source must stay gated, got {r.action}"
    )


def test_unsourced_behaviour_unchanged():
    """No source: the pre-existing L1.16 quarantine must be exactly as before."""
    r = _gate("La Rev C è stata approvata il 22/05/2026.")
    assert r.action != "persist", (
        f"unsourced approval claim must stay gated, got {r.action}"
    )


# ── Adversarial: subject-substitution (critic counterexample, 2026-07-18) ──
# The keyword echoes the source but is bound to a DIFFERENT subject; the source
# actually contradicts the claim. Bare-keyword echo must NOT disarm — the L1
# quarantine (pre-fix behaviour) must survive. The distinguishing signal used
# by the fix: legitimate documental ingest shares a HIGH-SPECIFICITY anchor
# (date / id / number) between claim and source; a subject swap that recombines
# words does not.

SOURCE_MODULES = (
    "Verbale comitato: il modulo di autenticazione è stato approvato. "
    "Il modulo di pagamento resta in revisione."
)


def test_subject_substitution_without_anchor_stays_quarantined():
    """The exact critic counterexample: 'pagamento approvato' while the source
    says pagamento is 'in revisione' and only *autenticazione* was approved.
    No shared date/id/number anchor → must NOT be disarmed."""
    r = _gate(
        "Il modulo di pagamento è stato approvato dal comitato.",
        source=SOURCE_MODULES,
    )
    assert r.action != "persist", (
        f"subject-substitution confab (no shared anchor) must stay gated, "
        f"got {r.action} with warnings {r.warnings}"
    )


def test_subject_substitution_even_with_unrelated_number_stays_quarantined():
    """A number present in the claim but ABSENT from the source (so not a
    shared anchor) must not rescue the confab."""
    r = _gate(
        "Il modulo di pagamento è stato approvato dal comitato il 99/99/9999.",
        source=SOURCE_MODULES,
    )
    assert r.action != "persist", (
        f"confab with a non-shared number must stay gated, got {r.action}"
    )


def test_faithful_paraphrase_with_shared_anchor_still_persists():
    """Guard the FP fix is not over-corrected: a faithful sourced paraphrase
    that DOES share the anchor (the approval date) stays admitted."""
    r = _gate(
        "Il modulo di autenticazione è stato approvato il 22/05/2026.",
        source="Verbale comitato del 22/05/2026: il modulo di autenticazione "
               "è stato approvato dal responsabile.",
    )
    assert r.action == "persist", (
        f"faithful sourced paraphrase with shared date anchor must persist, "
        f"got {r.action} with warnings {r.warnings}"
    )


def test_no_judge_sourced_write_carries_explicit_l4_skip_warning():
    """FIX-B1: a sourced write evaluated WITHOUT any grounding judge must say
    so out loud (advisory warning), not silently skip the moat."""
    # ground_write=True mirrors the client's balanced-preset default (the
    # 2026-07-17 moat-ON flip) — this is exactly the sourced-write path a
    # fresh Memory("db").add(fact, source=...) takes.
    r = run_validation_gate(
        proposition="L'immobile foglio 12 particella 455 sub 7 ha rendita "
                    "512,29 euro.",
        verified_by=None, topic=None, agent=None,
        source="Visura catastale: foglio 12 particella 455 sub 7, "
               "rendita euro 512,29.",
        ground_write=True,
    )
    skips = [w for w in (r.warnings or []) if w.get("layer") == "L4-skipped"]
    # Only asserted when the environment truly has no judge (no injected llm
    # here; local CE may exist on dev machines -> then L4 ran and no skip).
    from verimem.grounding_gate import _resolve_backend
    if _resolve_backend() == "local":
        pytest.skip("local CE judge present on this machine: L4 runs, no skip")
    assert skips, (
        f"sourced write without judge must carry an explicit L4-skipped "
        f"advisory, warnings: {r.warnings}"
    )
