"""Counting the assertions in a rejected claim, on claims that were really rejected.

The three cases below are verbatim from 2026-07-29: three consecutive attempts
to save one checkpoint, each rejected with the same unactionable "the source
does not support this proposition". The facts were true — I had verified them —
but each was proven SOMEWHERE ELSE than in the source attached, and the verdict
named no part. Three tries to find it by hand, and what worked every time was
SPLITTING the sentence.

Naming the guilty clause was tried first and does not work: see the module
docstring for the two measurements (per-clause scoring answers backwards;
ablation scored 0 of 2). So these tests cover the only thing that can be said
without a model — that the sentence makes more than one assertion — and the one
way that claim could still be wrong: cutting a LIST into fake assertions.
"""
from __future__ import annotations

import re

import pytest

from verimem.unsupported_span import split_claim_clauses

# Case 1 — the source was a commit message about the MCP channel; the claim also
# asserted what the SDK preset does, which that message never mentions.
CASO_1 = ("Il moat non girava sul canale MCP: hippo_remember non passava "
          "ground_write e ricadeva sull ambiente, mentre il preset balanced "
          "dell SDK passa ground=True e faceva giudicare la CLI.")

# Case 2 — same checkpoint, causal link added; the source reports the two facts
# separately and never joins them.
CASO_2 = ("Sul canale MCP la stessa scrittura con e senza source finiva con "
          "grounding NULL, perche il gate risolveva il moat dall ambiente.")

# Case 3 — the source was the abstention bench numbers; the claim opened with a
# diagnosis about which surfaces were off, which the numbers do not state.
CASO_3 = ("L astensione era spenta di default per SDK console e gateway "
          "mentre il canale MCP si asteneva, e su venti domande il gate "
          "acceso non toglie alcuna risposta che lo store poteva dare.")


def test_a_list_is_not_three_claims():
    """"SDK, console e gateway" is one enumeration. Cutting on a bare `e` would
    turn every list into separate assertions and point at a fragment."""
    clauses = split_claim_clauses("Il gate copre SDK, console e gateway.")
    assert len(clauses) == 1, clauses


@pytest.mark.parametrize("text,attesa", [
    (CASO_1, "mentre il preset balanced"),
    (CASO_2, "perche il gate risolveva"),
    (CASO_3, "e su venti domande"),
])
def test_a_new_assertion_starts_a_new_clause(text, attesa):
    clauses = split_claim_clauses(text)
    assert len(clauses) >= 2, clauses
    assert any(attesa in c for c in clauses), clauses


def test_the_gate_says_how_many_assertions_it_judged_as_one(monkeypatch):
    """The advice a writer actually reads, wired end to end.

    The rejection used to end at "likely a confabulated inference", which is a
    verdict, not a next step. It now states the one fact that makes the next
    step obvious and that no model has to guess.
    """
    import types

    from verimem.anti_confab_gate import run_validation_gate

    class _Judge:
        def complete(self, system, messages, *, model=None, max_tokens=None):  # noqa: ANN001
            return types.SimpleNamespace(text="SCORE: 5")

    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    monkeypatch.delenv("ENGRAM_GRADED_ADMISSION", raising=False)
    r = run_validation_gate(
        proposition=CASO_3, verified_by=None, topic=None, agent=None,
        source="commit b7771f7a: 0 wrong abstentions, 8/8 caught",
        grounding_llm=_Judge(),
    )
    l4 = [w for w in (r.warnings or []) if w.get("layer") == "L4-grounding"]
    assert l4, f"no L4 warning on a rejected write: {r.warnings}"
    advice = l4[0].get("advice", "")
    # QUESTO PRESIDIO CHIEDE IL FATTO, NON LA FORMULAZIONE — riscritto il
    # 2026-08-26 dopo che ha tenuto la CI rossa per una notte intera.
    #
    # Chiedeva la stringa letterale «3 separate assertions». `f48a45b9` ha
    # riscritto l advice in «This proposition splits into 3 clauses and the
    # moat judges them as ONE», che e la STESSA promessa detta meglio: il
    # difetto curato la dentro era proprio che il messaggio prometteva
    # ASSERZIONI e mostrava CLAUSOLE. Il presidio e diventato rosso su un
    # MIGLIORAMENTO, e un rosso cosi non distingue le due diagnosi opposte
    # («la promessa e caduta» / «qualcuno ha scelto una parola migliore»).
    #
    # In queste settimane i messaggi del gate li stiamo riscrivendo tutti,
    # perche e il mandato: un test che pinna la frase e garantito rompersi.
    # Quindi si asserisce cio che il docstring qui sopra promette davvero —
    # che l advice DICA QUANTE parti ha giudicato come una, e che inviti a
    # dividerle.
    #
    # E il numero non e scritto a mano: viene da `split_claim_clauses`, la
    # stessa funzione che il gate usa. Cosi il test verifica la COERENZA fra
    # cio che il gate CONTA e cio che DICE all utente — che e la promessa —
    # e resta rosso se l advice smette di dire il numero o ne dice un altro.
    atteso = len(split_claim_clauses(CASO_3))
    assert atteso == 3, (
        "il banco presuppone 3 clausole in CASO_3, ne conta "
        + str(atteso) + ": se il conteggio e cambiato aggiorna il CASO, "
        "non questo assert")
    # lookaround invece di una word-boundary: «3» non deve combaciare dentro
    # «13» o «30», e questa forma non ha escape che si perdano riscrivendo.
    assert re.search("(?<![0-9])" + str(atteso) + "(?![0-9])", advice), (
        "l advice non dice QUANTE parti ha giudicato come una: e il fatto "
        "che rende ovvio il passo successivo, ed e la ragione per cui "
        "questo test esiste (vedi il docstring). advice: " + advice)
    assert "split" in advice.lower(), advice


def test_a_single_assertion_gets_no_split_advice(monkeypatch):
    """Telling someone to split a sentence that says one thing is noise, and
    noise is how the useful half of a message stops being read."""
    import types

    from verimem.anti_confab_gate import run_validation_gate

    class _Judge:
        def complete(self, system, messages, *, model=None, max_tokens=None):  # noqa: ANN001
            return types.SimpleNamespace(text="SCORE: 5")

    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    monkeypatch.delenv("ENGRAM_GRADED_ADMISSION", raising=False)
    r = run_validation_gate(
        proposition="Il totale della fattura e 1240 euro.",
        verified_by=None, topic=None, agent=None,
        source="Fattura 88: imponibile 1000, IVA 240.",
        grounding_llm=_Judge(),
    )
    l4 = [w for w in (r.warnings or []) if w.get("layer") == "L4-grounding"]
    if l4:
        assert "separate assertions" not in l4[0].get("advice", "")


def test_a_run_of_spaces_does_not_blow_up_the_split():
    """ReDoS guard, with the numbers that made it necessary.

    _CLAUSE_BOUNDARY puts variable-width whitespace next to lookaheads, so on a
    run of spaces whose lookahead FAILS the engine retries from every position.
    Measured before the fix, on the exact input below:

        2 000 spaces  ->   0.3 s
        8 000 spaces  ->   5.2 s
       16 000 spaces  ->  20.8 s
       32 000 spaces  ->  82.9 s

    This module reads user-written fact text, so that is a denial of service on
    the write path. CodeQL flagged it (py/polynomial-redos, high) on the PR that
    introduced it. Note the first attempt to reproduce it MISSED: a trailing
    "mentre" makes the lookahead succeed immediately and the whole thing runs in
    0.1 ms. The blow-up needs the lookahead to fail.

    The threshold is deliberately loose — post-fix this is ~0.5 ms, so a second
    is a 2000x margin and cannot flake on a loaded CI box; anything quadratic
    sails past it.
    """
    import time

    hostile = "testo," + " " * 32000 + "x"
    t0 = time.perf_counter()
    split_claim_clauses(hostile)
    elapsed = time.perf_counter() - t0
    assert elapsed < 1.0, f"{elapsed:.1f}s on 32k spaces — the split went quadratic again"


def test_la_garanzia_sta_nel_REGEX_non_in_una_riga_lontana():
    """Il test qui sopra passa da quando esiste `_WS_RUN`, e CodeQL segnala il
    punto lo stesso (py/polynomial-redos, high, unsupported_span.py:83).

    NON e' il linter che si sbaglia sul comportamento — misurato oggi, 32 000
    spazi in 0.000 s contro gli 82.9 s di prima. Ha ragione su DOVE sta la
    garanzia: il collasso avviene in `split_claim_clauses`, una funzione piu'
    in la', e il regex resta ambiguo. Chi domani usasse `_CLAUSE_BOUNDARY` da
    un altro punto del modulo — un modulo di parsing, e' la cosa piu' naturale
    del mondo — si riporterebbe in casa il blow-up senza toccare niente di
    rotto.

    Quindi l'invariante si sposta DENTRO il pattern: dopo il collasso una
    corsa di spazi non esiste piu', percio' il confine di clausola puo'
    chiedere UN solo spazio. Nessun quantificatore, nessun backtracking
    possibile, e la promessa non dipende piu' dalla disciplina di chi chiama.

    E' la forma che questo repo ha gia' pagato tre volte per imparare: la cura
    e' un invariante, non la disciplina.
    """
    from verimem.unsupported_span import _CLAUSE_BOUNDARY

    for ambiguo in (r"\s+", r"\s*"):
        assert ambiguo not in _CLAUSE_BOUNDARY.pattern, (
            f"il confine di clausola contiene ancora {ambiguo!r}: su una corsa "
            "di spazi il cui lookahead fallisce il motore riprova da ogni "
            "posizione, e la protezione dipende dal fatto che il chiamante "
            "abbia collassato prima")


def test_il_confine_riconosce_ancora_le_frasi_normali():
    """Controprova della riga qui sopra: stringere il regex non deve fargli
    perdere i confini veri. Se `\\s+` diventasse uno spazio singolo e il testo
    arrivasse NON collassato, i tagli sparirebbero in silenzio — un difetto
    peggiore del ReDoS, perche' non si vede.

    Qui si passa apposta il testo come lo scrive un utente: a capo, doppi
    spazi, tabulazioni."""
    sporco = ("La misura era ferma da giorni.\n\n"
              "\tIl gate copriva SDK e console,  ma   il gateway restava fuori")
    clausole = split_claim_clauses(sporco)
    # Tre, non due: dopo il punto, e di nuovo sul «,  ma» — che e' proprio un
    # confine sporco, doppio spazio compreso. La prima stesura di questa riga
    # ne pretendeva due e il test mi ha corretto prima della cura.
    assert len(clausole) == 3, clausole
    assert clausole[0].startswith("La misura era ferma")
    assert clausole[1].startswith("Il gate copriva")
    assert clausole[2].startswith("ma il gateway")
    assert "  " not in " ".join(clausole), (
        "le corse di spazi sono arrivate fino all'uscita: il collasso non ha "
        "girato, e con un regex che chiede UN solo spazio i confini dopo un "
        "doppio spazio si perdono")
