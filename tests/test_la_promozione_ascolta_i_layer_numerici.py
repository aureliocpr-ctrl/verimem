"""La promozione documento -> fatto ascoltava il giudice e L1, e non i layer numerici.

Misurato il 2026-09-04 su una copia dell'indice vivo (683 chunk, 30 sorgenti), 40 frasi
reali con un numero cambiato di +1 promosse contro il LORO chunk: 25 su 40 AMMESSE con
grounding 99-100. Ricostruito il verdetto del gate su tre di quelle frasi:

    «Gli interessi di mora sono del 5 per cento annuo …»   action=downgrade  L4.1: «5»
    «… store vuoto e store con 4 fatti.»                    action=downgrade  L4.1: «4 fatto»
    «Le sette cose da sapere prima di scegliere una porta…» action=downgrade  L4.1: «443, 1500»

Il gate PARLAVA. `promote_chunk_to_fact` quarantina solo se il punteggio sta sotto il
taglio o se un layer L1 e' scattato: un valore assente dalla fonte entrava con la
citazione esatta del documento in `verified_by`, cioe' con l'aria di essere verificato
DAL documento che lo smentisce. Il gate stesso conta L4.1 come grounding fail
(`anti_confab_gate.has_grounding_fail`: L4-grounding, L4.1) — la promozione no.

E il secondo difetto, misurato nello stesso banco: 3 frasi VERE quarantinate con
`L1-domain-precision-observe,L1.10,L1.15`. Quel marcatore dice che il gate ha TENUTO
L1 come avviso (soggetto di terzi, default ON dal 22/07); la promozione lo leggeva come
un layer L1 in piu', perche' comincia per «L1». Su un fatto legale distillato
(«settlement resolved») e' il ritorno dell'86,7% di falsi positivi curato il 21/07.
"""
from __future__ import annotations

import pytest

from verimem import anti_confab_gate
from verimem.anti_confab_gate import GateResult
from verimem.document_promote import promote_chunk_to_fact
from verimem.semantic import SemanticMemory

CHUNK = ("Le consegne urgenti costano 35 euro a spedizione. Gli interessi di mora sono "
         "del 4 per cento annuo e decorrono dal giorno successivo.")


def _hit() -> dict:
    return {"text": CHUNK, "source_id": "contract.txt", "start": 0, "end": len(CHUNK),
            "version": 1}


@pytest.fixture()
def mem(tmp_path):
    return SemanticMemory(db_path=tmp_path / "s.db")


def _gate_che_risponde(monkeypatch, *, action, warnings, score):
    def _finto(**kw):
        return GateResult(action=action, warnings=list(warnings), grounding_score=score,
                          threshold=40.0, judge="stub")
    monkeypatch.setattr(anti_confab_gate, "run_validation_gate", _finto)


def _quarantined_by(mem, fact_id: str):
    import sqlite3
    with sqlite3.connect(str(mem.db_path)) as con:
        row = con.execute("SELECT quarantined_by FROM facts WHERE id=?", (fact_id,)).fetchone()
    return row[0] if row else None


def _promosso(mem, claim):
    r = promote_chunk_to_fact(mem, _hit(), claim=claim, topic="test/promo")
    assert r["stored"], r
    f = mem.get(r["fact_id"])
    assert f is not None
    return r, f


def test_un_numero_assente_dalla_fonte_ferma_la_promozione(mem, monkeypatch) -> None:
    _gate_che_risponde(
        monkeypatch, action="downgrade", score=100.0,
        warnings=[{"layer": "L4.1",
                   "reason": "il claim afferma un valore che la fonte non contiene: 5"}])
    r, f = _promosso(mem, "Gli interessi di mora sono del 5 per cento annuo.")
    assert r["status"] == "quarantined"
    assert f.status == "quarantined"
    # la ricevuta dice CHI ha fermato: il giudice diceva 100, e' stato L4.1
    assert "L4.1" in (r.get("trattenuto_da") or "")
    assert r.get("grounding_score") == 100.0
    # ...e la colonna che le tre porte del write path compilano lo dice pure:
    # nel banco del 04/09 erano 56 quarantinati su 56 senza autore.
    assert _quarantined_by(mem, r["fact_id"]) == "L4.1"


def test_l1_tenuto_advisory_dal_gate_non_quarantina_la_promozione(mem, monkeypatch) -> None:
    _gate_che_risponde(
        monkeypatch, action="persist", score=99.5,
        warnings=[{"layer": "L1.10", "reason": "Works/confirmed claim lacks runtime evidence"},
                  {"layer": "L1-domain-precision-observe",
                   "reason": "ENGRAM_L1_DOMAIN_PRECISION active: the subject reads as a "
                             "third-party professional fact, so the L1 keyword hit was kept "
                             "advisory rather than escalated"}])
    r, f = _promosso(mem, "La transazione fra le parti risulta conclusa e funziona.")
    assert r["status"] == "model_claim"
    assert f.status == "model_claim"
    assert not r.get("trattenuto_da")


def test_il_vanto_distillato_resta_quarantinato_da_l1(mem, monkeypatch) -> None:
    _gate_che_risponde(
        monkeypatch, action="downgrade", score=99.9,
        warnings=[{"layer": "L1.15", "reason": "Tested/verified claim lacks test evidence"}])
    r, f = _promosso(mem, "Il modulo e' stato testato ed e' pronto.")
    assert r["status"] == "quarantined"
    assert "L1.15" in r["trattenuto_da"]
    assert _quarantined_by(mem, r["fact_id"]) == "L1"


def test_l4_1_ambiguo_resta_un_avviso_e_il_fatto_entra(mem, monkeypatch) -> None:
    _gate_che_risponde(
        monkeypatch, action="persist", score=99.8,
        warnings=[{"layer": "L4.1-ambiguo",
                   "reason": "il claim contiene numeri che NON sono stati verificati: 5.000"}])
    r, f = _promosso(mem, "Il Tribunale ha condannato Verdi a pagare 5.000 euro.")
    assert r["status"] == "model_claim"
    assert f.status == "model_claim"
