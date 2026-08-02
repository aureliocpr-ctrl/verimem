"""Mezzo cartello in ISO e mezzo in epoch, nella stessa parentesi.

`--with-history` fa portare a ogni hit la sua storia: cosa diceva prima, da
quando, e fino a quando ha tenuto. La porta CLI è nata stamattina
(`ecbe2edf`), e la riga stampava:

    prima: Il piano annuale costa 100 euro. (2026-08-02 → 1785663692.5640569)

Due date della stessa parentesi in due formati diversi: `asserted_date` passa
da `_iso`, `until` usciva grezzo — e `_iso` è importata quattro righe sopra.
`temporal_context.py:154` la converte da sempre; questa superficie, nata oggi,
no.

`None` resta `None` e non diventa la stringa vuota che `_iso` darebbe su un
valore assente: un fatto ancora valido NON ha una data di fine, e «nessuna
fine» non è «fine sconosciuta» — è la stessa distinzione che il prodotto
difende fra un verdetto assente e uno negativo.

Trovato dall'altra istanza, sul commit che l'aveva appena introdotto.
"""
from __future__ import annotations

import re

from verimem.client import Memory

_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _storia(tmp_path):
    m = Memory(path=tmp_path / "m.db")
    vecchio = m.add("Il piano annuale costa 100 euro.", topic="prezzi")["id"]
    m.update(vecchio, "Il piano annuale costa 200 euro.")
    for h in m.search("quanto costa il piano annuale", k=5, with_history=True):
        if h.get("history"):
            return h["history"]
    return []


def test_le_due_date_hanno_lo_stesso_formato(tmp_path):
    storia = _storia(tmp_path)
    assert storia, "presupposto: il fatto aggiornato deve avere una storia"
    for p in storia:
        assert _ISO.match(p.get("asserted_date") or ""), p
        if p.get("until") is not None:
            assert _ISO.match(str(p["until"])), (
                f"«until» non è una data: {p['until']!r} — la stessa "
                f"parentesi mostrerebbe {p.get('asserted_date')} accanto a un "
                f"epoch")


def test_un_fatto_ancora_valido_non_ha_una_fine(tmp_path):
    """`None`, non stringa vuota: «nessuna fine» non è «fine sconosciuta»."""
    m = Memory(path=tmp_path / "m2.db")
    m.add("Il database di produzione è Postgres.", topic="infra")
    for h in m.search("quale database di produzione", k=5, with_history=True):
        for p in h.get("history") or []:
            assert p.get("until") is None or _ISO.match(str(p["until"])), p
