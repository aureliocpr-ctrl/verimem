"""Muro 1, pezzo 3b: il moat giudica OGNI claim, e il verdetto e' il MINIMO.

Pezzo 3a (main 22947ae9): la scrittura composta viene decomposta e ogni claim
nudo passa da L1. Il moat pero' giudicava ancora l'INTERO: una coda non
provata dalla fonte viaggiava attaccata a un fatto vero, e il giudice — che
vede la proposizione come una frase sola — poteva promuoverla insieme al
resto. Il gate stesso lo diceva nell'advice: «this proposition splits into N
clauses and the moat judges them as ONE — a single unproven piece sinks the
rest», cioe' confessava di non sapere QUALE.

Design (docs/ricerca/2026-09-05-design-write-n-claim-atomici.md §2):
    score_i = giudice(source, c_i)      verdetto_L4 = MIN_i score_i
`claims_verdict[i].score` porta il punteggio di ogni claim e il layer
`L4-grounding` finisce sul claim che non regge; `grounding_score` della
ricevuta e' il minimo. N=1 ⇒ identita' (P-D).

Il giudice qui e' FINTO e per claim (nessun modello: costo zero): 95 a ogni
claim, 5 a quello che nomina i «746 MB», che la fonte non dice. La coda non e'
una self-claim, cosi' L1 tace e decide solo il moat. Il MAX sulle frasi della
fonte (zavorra) e' il pezzo 3b-bis.
"""
from __future__ import annotations

import os

import pytest

from verimem import anti_confab_gate as g

COMPOSTA = ("Il comando warmup e' finito alle 14:53 e ha scaricato 746 MB "
            "di modello")
SEMPLICE = "Il comando warmup e' finito alle 14:53."
FONTE = ("$ verimem warmup\n[14:52:10] downloading gate model...\n"
         "[14:53:02] warmup finished OK")


class _GiudicePerClaim:
    """95 a tutto, 5 al claim che parla dei 746 MB (non nella fonte)."""

    def __init__(self) -> None:
        self.visti: list[str] = []

    def complete(self, system, messages, **kw):  # noqa: ANN001
        testo = " ".join(str(m.get("content", "")) for m in messages)
        self.visti.append(testo)
        punteggio = 5 if "746" in testo else 95
        return type("R", (), {"text": f"Score: {punteggio}"})()


def _gate(testo: str, giudice, **kw):
    kw.setdefault("verified_by", None)
    kw.setdefault("topic", "prova/muro-1-moat")
    kw.setdefault("agent", None)
    return g.run_validation_gate(proposition=testo, source=FONTE,
                                 grounding_llm=giudice, ground_write=True, **kw)


@pytest.fixture(autouse=True)
def _giudice_iniettato(monkeypatch):
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "claude")
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "0")
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE_THRESHOLD", raising=False)


def test_CONTROLLO_quale_albero_sto_misurando():
    import verimem
    qui = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert os.path.abspath(verimem.__file__).startswith(os.path.abspath(qui)), (
        verimem.__file__, qui)


def test_CONTROLLO_una_scrittura_semplice_e_giudicata_una_volta_sola():
    """P-D: N=1 e' identita' anche per il moat."""
    giudice = _GiudicePerClaim()
    r = _gate(SEMPLICE, giudice)
    assert r.decomposed is False
    assert r.grounding_score == 95.0, r.grounding_score
    assert len(giudice.visti) == 1, giudice.visti
    assert r.claims_verdict == [{"claim": 0, "layer": None, "score": 95.0}], (
        r.claims_verdict)


def test_IL_ROSSO_il_verdetto_e_il_minimo_e_dice_quale_claim_non_regge():
    giudice = _GiudicePerClaim()
    r = _gate(COMPOSTA, giudice)
    assert r.decomposed is True and len(r.claims) == 2, r.claims
    # ogni claim e' stato giudicato da solo
    assert len(giudice.visti) >= 2, giudice.visti
    punteggi = [v.get("score") for v in r.claims_verdict]
    assert punteggi == [95.0, 5.0], r.claims_verdict
    # il verdetto della scrittura e' il minimo
    assert r.grounding_score == 5.0, r.grounding_score
    assert r.action == "downgrade", (r.action, r.warnings)
    # e il layer sta sul claim che non regge, non su tutta la scrittura
    assert r.claims_verdict[1]["layer"] == "L4-grounding", r.claims_verdict
    assert r.claims_verdict[0]["layer"] is None, r.claims_verdict
    l4 = [w for w in r.warnings if w.get("layer") == "L4-grounding"]
    assert l4 and l4[0].get("claim") == 1, r.warnings
    # e l'advice non dice piu' «the moat judges them as ONE»
    assert "judges them as ONE" not in str(l4[0].get("advice", "")), l4[0]
    assert "746" in str(l4[0].get("advice", "")), l4[0]


def test_una_scrittura_composta_tutta_provata_passa_col_minimo_alto():
    """Controllo dall'altro lato: se ogni claim regge, il minimo e' alto."""
    giudice = _GiudicePerClaim()
    r = _gate("Il comando warmup e' partito alle 14:52 ed e' finito alle 14:53",
              giudice)
    assert r.decomposed is True
    assert [v.get("score") for v in r.claims_verdict] == [95.0, 95.0], (
        r.claims_verdict)
    assert r.grounding_score == 95.0
    assert r.action == "persist", (r.action, r.warnings)
