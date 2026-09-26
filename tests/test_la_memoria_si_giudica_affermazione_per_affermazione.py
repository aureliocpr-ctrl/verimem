"""A memory that says more than its source is judged claim by claim (T221).

The promise (``verimem/__init__.py:3``): «a fact its source does not support is
QUARANTINED». Measured on 2026-09-23 on 100 memories extracted from real
conversations: 29 of the 37 memories that say more than the turn they cite were
admitted at the write port, with a median grounding of 99.43. The judge scored
the whole sentence, and the part the turn supports carried the part it does not.

The gate now splits the memory with ``decomponi()`` and judges each claim with the
same judge. The verdict is the WEAKEST claim, and the receipt names it. A simple
sentence (one claim) is judged once, exactly as before.

The cells inject the judge's score as a function of the text it receives, so they
say which text reached the judge. No model runs.

T221, 26/09. Run from the root of the checkout:

    python -m pytest tests/test_la_memoria_si_giudica_affermazione_per_affermazione.py -q -p no:randomly
"""
from __future__ import annotations

from verimem import anti_confab_gate as g
from verimem import grounding_gate as gg

FONTE = "Mara: I took the dogs to the beach today, they loved the waves!"


def _gate(monkeypatch, proposizione: str, punteggi: dict[str, float]):
    """Run the write gate with an injected judge. `punteggi` maps the start of a
    text to its score; every text the judge receives is recorded."""
    visti: list[str] = []

    def giudice(_llm, _fonte, testo, **_k):
        visti.append(testo)
        for inizio, s in punteggi.items():
            if testo.startswith(inizio):
                return s, "local"
        raise AssertionError(f"the judge received a text the cell did not expect: {testo!r}")

    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE_THRESHOLD", raising=False)
    monkeypatch.delenv("ENGRAM_GROUNDING_THRESHOLD", raising=False)
    monkeypatch.setenv("ENGRAM_BAND_LLM", "0")
    monkeypatch.setattr(gg, "fact_grounding_score_ex", giudice)
    gate = g.run_validation_gate(
        proposition=proposizione, verified_by=["source-doc:x:1"], topic="t",
        agent=None, validate="fast", source=FONTE)
    return gate, visti


def test_la_parte_che_la_fonte_non_dice_ferma_la_memoria(monkeypatch):
    gate, visti = _gate(
        monkeypatch,
        "Mara took her dogs to the beach today and they are now asleep on the sofa.",
        {"Mara took her dogs to the beach today and": 95.0,     # the whole memory
         "Mara took her dogs to the beach today.": 97.0,        # claim 1: the turn says it
         "They are now asleep on the sofa.": 12.0})             # claim 2: the turn does not
    assert gate.action != "persist", (gate.action, gate.grounding_score, visti)
    assert gate.grounding_score == 12.0, (gate.grounding_score, visti)
    testo = " ".join(str(v) for w in gate.warnings for v in w.values())
    assert "They are now asleep on the sofa." in testo, testo   # the receipt names the claim


def test_il_claim_in_fascia_e_nominato_nella_ricevuta(monkeypatch):
    # the weakest claim lands in the review band [40, 80): the write is held, and the
    # receipt says WHICH claim the judge doubts, not only the band's number
    monkeypatch.setenv("VERIMEM_CE_BAND_ENFORCE", "1")
    gate, visti = _gate(
        monkeypatch,
        "Mara took her dogs to the beach today and they are now asleep on the sofa.",
        {"Mara took her dogs to the beach today and": 95.0,
         "Mara took her dogs to the beach today.": 97.0,
         "They are now asleep on the sofa.": 60.0})
    assert gate.action != "persist", (gate.action, gate.grounding_score, visti)
    claim = [w for w in gate.warnings if w.get("layer") == "L4-claim"]
    assert claim, [w.get("layer") for w in gate.warnings]
    assert "They are now asleep on the sofa." in claim[0]["reason"], claim
    assert "not sure" in claim[0]["reason"], claim


def test_una_memoria_vera_di_due_affermazioni_resta_ammessa(monkeypatch):
    gate, visti = _gate(
        monkeypatch,
        "Mara took her dogs to the beach today and they loved the waves.",
        {"Mara took her dogs to the beach today and": 96.0,
         "Mara took her dogs to the beach today.": 97.0,
         "They loved the waves.": 93.0})
    assert gate.action == "persist", (gate.action, gate.grounding_score, gate.warnings)
    assert len(visti) == 3, visti                               # the whole, then each claim


def test_una_frase_semplice_si_giudica_una_volta_sola(monkeypatch):
    gate, visti = _gate(monkeypatch, "Mara took her dogs to the beach today.",
                        {"Mara took her dogs to the beach today.": 97.0})
    assert gate.action == "persist", (gate.action, gate.warnings)
    assert visti == ["Mara took her dogs to the beach today."], visti
