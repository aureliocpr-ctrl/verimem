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
    from verimem.local_grounding import local_ce_available
    if _resolve_backend() == "local" or local_ce_available():
        import pytest
        pytest.skip("a grounding judge (local CE) is present: L4 ran, no advisory "
                    "— the no-judge advisory is covered by "
                    "test_no_judge_at_all_carries_advisory below")
    skips = [w for w in (r.warnings or []) if w.get("layer") == "L4-skipped"]
    assert skips, (
        f"sourced write with no judge must carry an L4-skipped advisory, "
        f"warnings: {r.warnings}"
    )


def test_no_judge_at_all_carries_advisory(monkeypatch):
    """IL TEST CHE LO SKIP QUI SOPRA CITAVA E CHE NON ESISTEVA.

    `test_sourced_write_without_judge_carries_explicit_advisory` si astiene
    quando un giudice c'è, e rimanda «al test qui sotto». Quel nome non
    esisteva: `git grep no_judge_at_all -- tests/` restituiva **una sola
    riga, la stringa dentro il messaggio di skip stesso**.

    ⇒ Il risultato è che su ogni macchina con il giudice locale — la CI e
    tutte le nostre — l'advisory `L4-skipped` **alla porta di scrittura** non
    aveva presidio. `L4-skipped` è nominato da altri otto file, ma quelli
    asseriscono su `esito_del_moat` (funzione interna) e sul doctor: livelli
    diversi, e il registro dice che ogni salto di livello può ribaltare il
    verdetto.

    🆕 LA FORMA, che non avevamo in tassonomia: **un puntatore fra presidi che
    punta nel vuoto.** Non è un presidio spento né un sensore scollegato — è
    un'astensione GIUSTIFICATA da una copertura che non esiste, e si nasconde
    meglio delle altre due perché chi legge lo skip trova una ragione e smette
    di guardare.

    Qui il giudice si FORZA assente invece di sperarlo — stessa ricetta che sei
    file già usano (`test_moat_on_by_default.py:58`, `test_gateway_moat_default.py:48`,
    …): il gate importa i due simboli dentro la funzione (`anti_confab_gate.py:2319-2320`),
    quindi la sostituzione sui moduli sorgente li raggiunge a ogni chiamata.
    """
    monkeypatch.setattr("verimem.local_grounding.local_ce_available", lambda: False)
    monkeypatch.setattr("verimem.grounding_gate._resolve_backend", lambda: "none")
    r = _gate(
        "La Rev C (approvata il 22/05/2026) del capannone Lotto 3 "
        "prescrive carico neve 1.50 kN/m2.",
        source=SOURCE_APPROVAL, ground_write=True,
    )
    skips = [w for w in (r.warnings or []) if w.get("layer") == "L4-skipped"]
    assert skips, (
        f"con NESSUN giudice configurato, una scrittura con `source` deve "
        f"portare l'advisory L4-skipped: il chiamante non può sapere "
        f"altrimenti che il moat non è girato. warnings: {r.warnings}"
    )


def test_presidio_col_giudice_PRESENTE_l_advisory_no_judge_NON_c_e(monkeypatch):
    """La controparte: senza di lei il test qui sopra passerebbe anche se
    l'advisory fosse incondizionata, cioè misurerebbe una proprietà più debole
    di quella che promette. Le due popolazioni, non una.

    ⚠️ LIMITE DICHIARATO — QUESTO NON L'HO PROVATO ACCESO, e lo scrivo qui
    invece di lasciarlo credere. Il criterio è «acceso = diventa ROSSO se
    spegni ciò che presidia»; il test sopra lo supera (spegnendo
    `_emit_l4_skipped` esce `1 failed`), questo NO: rendendo l'advisory
    incondizionata (`elif source:` invece di `elif source and not
    _have_judge:` a `anti_confab_gate.py:2732`) restano `6 passed`.
    ⇒ Il motivo è che l'advisory ha DUE punti di emissione — `:2732` e `:2374`
    (`if gscore is None`, il CE annunciato presente che non riesce a scorare) —
    e nessuno dei due casi qui passa dal primo. Quindi questo test **non
    presidia quel ramo**: presidia che, col giudice presente e funzionante,
    l'advisory non compaia — che è una proprietà più debole di quella che il
    nome promette.
    ⇒ Chi ha il fronte del gate può chiuderlo forzando `gscore` a un valore
    invece che a `None`. Non l'ho fatto io: tocca il percorso di scoring, che
    non è il mio perimetro."""
    monkeypatch.setattr("verimem.local_grounding.local_ce_available", lambda: True)
    monkeypatch.setattr("verimem.grounding_gate._resolve_backend", lambda: "local")
    r = _gate(
        "La Rev C (approvata il 22/05/2026) del capannone Lotto 3 "
        "prescrive carico neve 1.50 kN/m2.",
        source=SOURCE_APPROVAL, ground_write=True,
    )
    skips = [w for w in (r.warnings or []) if w.get("layer") == "L4-skipped"]
    assert not skips, (
        f"col giudice presente il moat gira, quindi l'advisory «non ha girato» "
        f"sarebbe FALSA: warnings {r.warnings}"
    )


class _RejectingJudge:
    """A grounding judge that always reports no entailment (score 0).

    Returns an object carrying ``.text``, which is the contract the gate reads
    (``getattr(resp, "text", "")``). It used to return the bare string "0": a
    string has no ``.text``, so the verdict was UNREADABLE and the gate fell back
    to 50 — the quarantine this test asserts came from that fallback, not from
    the judge, which was never actually consulted. The test passed while
    measuring something else. Surfaced 2026-07-28, when an unreadable verdict
    stopped being scored as 50.
    """

    class _Reply:
        text = "SCORE: 0"

    def complete(self, system, messages, **kw):  # pragma: no cover - shape only
        return self._Reply()


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
