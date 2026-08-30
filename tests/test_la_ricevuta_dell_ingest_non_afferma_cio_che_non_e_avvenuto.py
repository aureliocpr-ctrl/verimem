"""«atomic facts stored…» era scritto anche quando NON era stato memorizzato nulla.

MISURATO ALLA PORTA il 2026-08-30 alle 23:29 — due messaggi con un numero
verificabile, store temporaneo, nessun llm raggiungibile::

    stored 0 · rejected 0 · extracted 0 · fact_ids []
    error  null
    note   "atomic facts stored as low-trust model_claim with conversation
            provenance; evidence elevates status, never the chat itself"

⇒ **Nessun fatto memorizzato, nessun errore dichiarato, e una nota che parla al
presente di fatti «stored».** Chi legge `error: null` e quella frase conclude
che l'ingestione sia andata.

🔑 E `rejected: 0` peggiora la lettura invece di aiutarla: si legge come
«niente è stato rifiutato» — vero, e fuorviante, perché **non c'era niente da
rifiutare**. È la forma che questa notte ha incontrato più volte: *una misura
che NON C'È si legge come un risultato buono.*

⚖️ I NUMERI C'ERANO GIÀ TUTTI NELLA RICEVUTA (`stored`, `extracted`,
`rejected`, `error`): mancava che la riga in prosa li leggesse. La cura non
aggiunge un campo — **fa dire alla nota ciò che i campi già dicono**, e
distingue quattro casi: estrazione fallita · nessun fatto estratto · fatti
estratti e tutti respinti · fatti memorizzati.

⚠️ COSA NON DICE questa cura: *perché* l'estrattore non abbia prodotto nulla.
La nota nomina le due possibilità (una conversazione senza affermazioni, o un
estrattore che non può girare) e manda a `doctor`, invece di sceglierne una: da
qui non è distinguibile, e sceglierne una sarebbe la stessa confabulazione che
il prodotto esiste per fermare.
"""

from __future__ import annotations

import asyncio
import json
import re

import pytest

from verimem import mcp_server

CONVERSAZIONE = [
    {"role": "user", "content": "La penale del contratto e' 120 euro al giorno."},
    {"role": "assistant", "content": "Registrato: penale 120 euro al giorno."},
]


def _ingest(tmp_path, monkeypatch, **extra) -> dict:
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "store"))
    args = {"messages": CONVERSAZIONE, "conversation_id": "c1",
            "topic": "ing/x", **extra}
    out = asyncio.run(mcp_server._call_tool_impl("hippo_ingest_conversation", args))
    return json.loads(out[0].text)


@pytest.fixture
def ricevuta(tmp_path, monkeypatch) -> dict:
    return _ingest(tmp_path, monkeypatch)


def test_con_zero_memorizzati_la_nota_non_dice_stored(ricevuta):
    """IL CUORE: la nota non deve affermare un esito che i campi negano."""
    if ricevuta.get("stored"):
        pytest.skip("in questo ambiente l'estrattore ha memorizzato: "
                    "il caso da presidiare non si presenta")
    nota = str(ricevuta.get("note", ""))
    assert not re.search(r"\bfacts stored\b", nota), nota
    assert "NOTHING was ingested" in nota, nota


def test_la_nota_spiega_che_zero_rifiutati_non_vuol_dire_tutto_passato(ricevuta):
    """La riga che disinnesca la lettura sbagliata di `rejected: 0`."""
    if ricevuta.get("stored"):
        pytest.skip("l'estrattore ha memorizzato: caso non applicabile")
    nota = str(ricevuta.get("note", ""))
    assert "nothing to reject" in nota, nota


def test_la_nota_non_sceglie_una_causa_che_non_puo_conoscere(ricevuta):
    """⚠️ IL LIMITE, presidiato: da qui non si distingue «conversazione senza
    affermazioni» da «estrattore che non può girare». La nota deve NOMINARE
    entrambe e mandare a `doctor`, non sceglierne una."""
    if ricevuta.get("stored"):
        pytest.skip("l'estrattore ha memorizzato: caso non applicabile")
    nota = str(ricevuta.get("note", ""))
    assert "either" in nota and "doctor" in nota, nota


def test_i_numeri_restano_quelli_di_prima(ricevuta):
    """⚠️ LA POPOLAZIONE OPPOSTA: la cura tocca SOLO la prosa. Se avesse
    cambiato i conteggi, avrei curato la ricevuta rendendola un'altra cosa."""
    for campo in ("stored", "rejected", "extracted", "fact_ids", "error"):
        assert campo in ricevuta, f"il campo {campo} è sparito dalla ricevuta"
