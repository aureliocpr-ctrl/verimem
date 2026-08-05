"""Il tier documenti sul canale flow — l'unico che non emetteva NULLA.

Censimento delle camere dark (ws6, 2026-08-05): gli altri tier emettevano
almeno sotto un nome che le superfici live scartano; `document_index.py` e
`documents.py` non avevano una sola chiamata a `emit`. Ed è il tier su cui
tutta la squadra si appoggia come "canale robusto" per le consegne — 25
documenti, 598 chunk, 307 (51,3%) di versioni superate (misurato da ws4).

I due campi che rendono leggibile un ingest sono `version` (quale versione
ha vinto: la ricerca serve solo l'ultima) e `chunks_flagged` (quanto è stato
trattenuto dallo screen anti-injection). Sul lato lettura, `flagged_hidden`
dice se la risposta è stata costruita mentre qualcosa veniva nascosto — il
tier lo fa di default e finora non lo diceva a nessuno.
"""
from __future__ import annotations

import json

import pytest

from verimem import event_jsonl_log, flow_events
from verimem.document_index import DocumentIndex

_TESTO = (
    "Protocollo di laboratorio. Sezione 1: il campione va conservato a "
    "quattro gradi. Sezione 2: la curva di taratura richiede cinque punti. "
    "Sezione 3: il limite di quantificazione del piombo e' zero virgola due."
)


@pytest.fixture()
def idx(tmp_path, monkeypatch):
    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    monkeypatch.delenv("ENGRAM_FLOW_SURFACE", raising=False)
    flow_events.reset_flow_context()
    return DocumentIndex(db_path=tmp_path / "docs.db"), tmp_path


def _flow(tmp_path, kind=None):
    p = tmp_path / "events.jsonl"
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        rec = json.loads(ln)
        if rec.get("name") == "flow.document" and (
                kind is None or rec["payload"].get("kind") == kind):
            out.append(rec)
    return out


def test_l_indicizzazione_esce_con_versione_e_chunk(idx):
    di, tmp = idx
    res = di.index_document("protocollo", _TESTO)
    evts = _flow(tmp, "index")
    assert len(evts) == 1, "il tier non emetteva NULLA"
    p = evts[0]["payload"]
    assert p["source_id"] == "protocollo"
    assert p["version"] == res["version"]
    assert p["chunks_indexed"] == res["chunks_indexed"]
    assert p["chunks_flagged"] == res.get("chunks_flagged", 0)


def test_la_reindicizzazione_alza_la_versione_e_si_vede(idx):
    """Il numero che spiega il 51,3% di chunk superati: ogni reindicizzazione
    crea una versione nuova e la ricerca serve solo l'ultima."""
    di, tmp = idx
    di.index_document("protocollo", _TESTO)
    di.index_document("protocollo", _TESTO + " Sezione 4: resa attesa 90%.")
    versioni = [e["payload"]["version"] for e in _flow(tmp, "index")]
    assert versioni == [1, 2], versioni


def test_la_ricerca_esce_con_n_e_best_e_senza_testo(idx):
    di, tmp = idx
    di.index_document("protocollo", _TESTO)
    hits = di.search("a che temperatura si conserva il campione?", k=2)
    evts = _flow(tmp, "search")
    assert len(evts) == 1
    p = evts[0]["payload"]
    assert p["n"] == len(hits)
    if hits:
        assert p["best"] == hits[0]["score"]
    blob = json.dumps(p)
    assert "campione va conservato" not in blob, (
        "il feed porta metadati, mai il testo della citazione")


def test_una_ricerca_a_vuoto_non_emette(idx):
    """Query vuota: esce prima, e un evento per un non-evento e' rumore."""
    di, tmp = idx
    di.index_document("protocollo", _TESTO)
    assert di.search("   ", k=2) == []
    assert _flow(tmp, "search") == []
