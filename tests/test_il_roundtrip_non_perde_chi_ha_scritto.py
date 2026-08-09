"""Un fatto riletto dal DB si porta dietro CHI l'ha scritto.

`_row()` ricostruisce ogni Fact letto dallo store, e popolava tutti i campi
tranne `writer_principal` — l'identita' stampata dal server, quella che il
dataclass descrive come «never taken from tool arguments: the entrypoint stamps
it». Persistita su 205 righe del corpus vivo, e persa a ogni lettura.

Non e' la prima volta su questa funzione: un commento del 2026-06-02 dice
«SCAN-68 FIX (NONNA): erano OMESSI -> provenance v6 persa nel roundtrip» per
writer_role e meta_narrative. `writer_principal` e' arrivato dopo (v16,
2026-07-23) e nessuno l'ha aggiunto qui.

E' venuto fuori solo il 2026-07-30, quando il contratto di uscita ha iniziato a
mostrare il campo: `hippo_facts_recent` sul corpus vero dava
writer_principal=None su fatti che nel DB hanno 'cli:local'. Prima non lo
esponeva nessuna superficie, quindi nessuno poteva accorgersene — un campo
invisibile non ha modo di risultare sbagliato.

Il test non guarda solo questo campo: li confronta TUTTI fra la riga scritta e
la riga riletta, cosi' il prossimo campo aggiunto al dataclass non potra'
sparire in silenzio nel roundtrip.
"""
from __future__ import annotations

import dataclasses

import pytest

from verimem.semantic import Fact, SemanticMemory

#: Campi che il roundtrip puo' legittimamente non restituire identici, col
#: perche'. Ogni voce e' una perdita accettata e spiegata.
PERDITE_AMMESSE = {
    "source_signature": "la ricalcola lo store, non e' un dato del chiamante",
    "confidence": "il write-path puo' riscalarla (preset, gate)",
    "status": "lo decide il gate, non chi scrive",
    "verified_by": "il gate puo' normalizzarlo",
    "created_at": "lo stampa lo store",
    "last_verified_at": "lo stampa lo store",
}


@pytest.fixture
def sm(tmp_path):
    return SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")


def _pieno() -> Fact:
    return Fact(
        proposition="Il servizio ascolta sulla porta 8443.", topic="prova",
        writer_principal="cli:local", writer_role="user",
        confidence_tier="high", grounding_score=93.5, asserted_at=1000.0,
        valid_until=4102444800.0, derives_from=["aaaaaaaaaaaa"],
        lineage_to=["bbbbbbbbbbbb"], trigger_keywords=["porta"],
        applicable_when="quando serve la porta", worked_example="8443",
        epistemic={"kind": "unbeaten", "bound": 10.0}, meta_narrative=True,
    )


def test_chi_ha_scritto_sopravvive_alla_rilettura(sm):
    f = _pieno()
    sm.store(f)
    riletto = sm.get(f.id)
    assert riletto is not None
    assert riletto.writer_principal == "cli:local", (
        "writer_principal si perde nel roundtrip: e' l'identita' stampata dal "
        "server, quella che nessuno puo' auto-dichiarare, ed e' proprio quella "
        "che sparisce")


def test_nessun_campo_sparisce_nel_roundtrip(sm):
    """L'invariante: il prossimo campo aggiunto al dataclass non potra'
    sparire in silenzio come e' successo a writer_principal."""
    f = _pieno()
    sm.store(f)
    riletto = sm.get(f.id)
    persi = []
    for campo in dataclasses.fields(Fact):
        n = campo.name
        if n in PERDITE_AMMESSE:
            continue
        prima, dopo = getattr(f, n), getattr(riletto, n, None)
        if prima and not dopo:
            persi.append(f"{n}: scritto {prima!r}, riletto {dopo!r}")
    assert not persi, (
        "campi persi nella rilettura dallo store:\n  " + "\n  ".join(persi)
        + "\naggiungili a _row(), oppure a PERDITE_AMMESSE con il perche'.")
