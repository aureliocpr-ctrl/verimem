"""Muro 1, pezzo 3a: la CODA di una scrittura composta viene giudicata da L1.

Misurato il 05/09 (Galileo, N4) e rimisurato il 06/09 alle 07:20 dal lead sul
gate di main 3fd1ed31, con `agent=None` e senza fonte:

    INTERO  «Il comando warmup e' finito alle 14:53 ed e' verificata»
            -> persist   (L1.13, L1.15 presenti, ma il soggetto «Il comando
                          warmup» e' letto come fatto professionale di terzi:
                          L1-domain-precision-observe, nessuna escalation)
    CODA NUDA «E' verificata.»              -> downgrade (L1.15 escala)
    CODA CON SOGGETTO «Il comando warmup e' verificata.» -> persist

Cioe': la self-claim in coda ELUDE L1 se viaggia attaccata a un fatto vero
(115/200 fermate sull'intero contro 145/200 sulle code nude, 05/09). La cura
del design «write = N claim atomici» (docs/ricerca/2026-09-05-design-write-n-
claim-atomici.md, §2.3): `decomponi()` spezza, la forma NUDA va a L1, quella
AUTO-CONTENUTA finisce nella ricevuta che l'utente legge.

PERIMETRO DI QUESTO PEZZO, dichiarato: solo L1. Il moat (L4) giudica ancora la
proposizione INTERA come oggi (P-D identita' per costruzione); il MIN sui claim
e il MAX sulle frasi della fonte sono il pezzo 3b.
"""
from __future__ import annotations

import os

import pytest

from verimem import anti_confab_gate as g

COMPOSTA = "Il comando warmup e' finito alle 14:53 ed e' verificata"
SEMPLICE = "Il comando warmup e' finito alle 14:53."


def _gate(testo: str, **kw):
    kw.setdefault("verified_by", None)
    kw.setdefault("topic", "prova/muro-1")
    kw.setdefault("agent", None)
    kw.setdefault("source", None)
    return g.run_validation_gate(proposition=testo, **kw)


def _layer_l1(r) -> list[str]:
    return [str(w.get("layer")) for w in r.warnings
            if str(w.get("layer", "")).startswith("L1")]


def test_CONTROLLO_la_coda_nuda_da_sola_viene_fermata_oggi():
    """Controllo positivo del criterio: senza questo, un L1 spento darebbe
    verde alla cella del rosso per la ragione sbagliata."""
    r = _gate("E' verificata.")
    assert r.action == "downgrade", (r.action, r.warnings)
    assert "L1.15" in _layer_l1(r)


def test_IL_ROSSO_la_coda_di_una_scrittura_composta_viene_fermata():
    r = _gate(COMPOSTA)
    assert r.decomposed is True
    assert len(r.claims) == 2, r.claims
    # la ricevuta porta la forma AUTO-CONTENUTA (quella che l'utente legge)
    assert r.claims[1].startswith("Il comando warmup"), r.claims
    assert r.action == "downgrade", (r.action, r.warnings)
    fermati = [v for v in r.claims_verdict if v.get("layer")]
    assert [v["claim"] for v in fermati] == [1], r.claims_verdict
    assert str(fermati[0]["layer"]).startswith("L1"), r.claims_verdict
    # e il warning dice QUALE claim ha fermato
    assert any(w.get("claim") == 1 for w in r.warnings
               if str(w.get("layer", "")).startswith("L1")), r.warnings


def test_una_scrittura_semplice_e_identita():
    """N=1: nessuna differenza dal gate di oggi (P-D)."""
    r = _gate(SEMPLICE)
    assert r.decomposed is False
    assert r.claims == [SEMPLICE]
    assert r.action == "persist", (r.action, r.warnings)
    assert r.claims_verdict == [{"claim": 0, "layer": None, "score": None}]


def test_il_contenuto_esterno_non_si_decompone():
    """P-F: un documento non e' un'asserzione dell'agente."""
    r = _gate(COMPOSTA, writer_role="external_content")
    assert r.decomposed is False
    assert r.claims == [COMPOSTA]


def test_la_via_d_uscita_d_emergenza_e_dichiarata_nella_ricevuta(monkeypatch):
    monkeypatch.setenv("VERIMEM_DECOMPOSE", "0")
    r = _gate(COMPOSTA)
    assert r.decomposed is False
    assert r.claims == [COMPOSTA]
    assert any(w.get("layer") == "decompose-off"
               and "VERIMEM_DECOMPOSE" in str(w.get("reason", ""))
               for w in r.warnings), r.warnings
    # e l'azione torna quella di oggi: la coda elude L1
    assert r.action == "persist", (r.action, r.warnings)


def test_il_parametro_esplicito_vince_sull_ambiente(monkeypatch):
    monkeypatch.setenv("VERIMEM_DECOMPOSE", "0")
    r = _gate(COMPOSTA, decompose=True)
    assert r.decomposed is True
    assert r.action == "downgrade"


def test_CONTROLLO_quale_albero_sto_misurando():
    """In un worktree `import verimem` puo' risolvere all'albero condiviso
    (due rossi mal attribuiti il 06/09): il verde dice di quale albero e'."""
    import verimem
    qui = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert os.path.abspath(verimem.__file__).startswith(os.path.abspath(qui)), (
        verimem.__file__, qui)
