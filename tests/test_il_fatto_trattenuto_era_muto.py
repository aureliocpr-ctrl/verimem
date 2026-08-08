"""C'era un fatto, il gate l'ha trattenuto, e a chi interroga non lo diceva nessuno.

IL DIFETTO, dalla fetta ⑦ del censimento consegnato oggi: nel corpus di casa 746
fatti su 8.999 sono in quarantena. Non tornano dalle letture — ed è giusto, è il
loro mestiere — ma **chi interroga non riceve nessun segnale**. Chi ha scritto
quel fatto crede di averlo salvato; chi legge crede che sulla memoria non ci sia
niente.

⚠️ MISURATO DALLA PORTA, prima di scrivere una riga::

    nel database   quarantined   «Ho implementato l'export e funziona…»
                   model_claim   «Il magazzino di Verona contiene 480 pallet.»
    search("export del magazzino")  ->  1 risultato (solo l'ammesso)  ✅ la
        quarantena FUNZIONA: il fatto trattenuto non esce da nessuna porta
        (verificato in indipendenza da ws1 su sei porte e da ws4 sul briefing)
    res.sotto_il_pavimento -> {'pavimento': 0.8698, …}   ← un avviso C'È
        ma parla d'altro: dice «nessun risultato supera la soglia di rilevanza»,
        non «c'era un fatto e l'ho trattenuto».

⇒ **Il difetto non è che il quarantinato esca. È che il suo silenzio è
indistinguibile dall'assenza.**

📌 LA CURA NON INVENTA UN CANALE, e non poteva: il canale esiste già ed è la
classe ② di questa casa (la cura c'è, manca il collegamento). ``Risultati`` è una
``list`` vera con attributi — ``sotto_il_pavimento`` per la rilevanza, ``nascosti``
in ``document_index`` per i documenti. Qui si aggiunge ``trattenuti`` accanto agli
altri, con la stessa disciplina:

    · DICHIARA E NON TAGLIA — non restituisce il fatto quarantinato. Restituirlo
      sarebbe spegnere la quarantena, cioè curare un avviso mancante rompendo la
      garanzia che dà valore al prodotto.
    · È UNA ``list`` VERA — chi non legge l'attributo non si accorge di niente, e
      ``search`` ha una quantità di consumatori che la iterano e ne fanno ``len()``.
    · NON DICE COSA c'era dentro — un fatto è in quarantena perché non ci si
      fida: mostrarne il testo per «trasparenza» lo rimetterebbe in circolo per
      la porta di servizio.
"""
from __future__ import annotations

import sqlite3

import pytest

VANTO = "Ho implementato l'export del magazzino e funziona perfettamente."
VERO = "Il magazzino di Verona contiene 480 pallet."
FONTE = "Inventario 2026-03-01: magazzino Verona, 480 pallet a scaffale."


@pytest.fixture()
def memoria(tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    from verimem.client import Client
    return Client()


def test_chi_interroga_SA_che_qualcosa_e_stato_trattenuto(memoria):
    """IL CUORE: il silenzio di un fatto trattenuto non deve essere
    indistinguibile dall'assenza di quel fatto."""
    memoria.add(VANTO, topic="mag")
    res = memoria.search("export del magazzino")
    assert getattr(res, "trattenuti", None), (
        "nessun segnale: chi interroga non sa che il gate ha trattenuto qualcosa")
    assert res.trattenuti["quanti"] >= 1


def test_NON_restituisce_il_fatto_trattenuto(memoria):
    """⚠️ IL PRESIDIO PIÙ IMPORTANTE. Curare un avviso mancante restituendo il
    fatto significherebbe spegnere la quarantena — cioè rompere la garanzia che
    dà valore al prodotto per aggiungere un messaggio."""
    memoria.add(VANTO, topic="mag")
    res = memoria.search("export del magazzino")
    testi = " ".join(str(r) for r in res)
    assert "funziona perfettamente" not in testi
    # e nemmeno dentro l'avviso: un fatto trattenuto non si mostra «per trasparenza»
    assert "funziona perfettamente" not in str(getattr(res, "trattenuti", ""))


def test_CONTROLLO_POSITIVO_senza_quarantinati_l_avviso_NON_compare(memoria):
    """⚠️ LA POPOLAZIONE OPPOSTA. Senza questa metà, la cura è soddisfatta da un
    avviso che compare sempre — che è rumore, non informazione."""
    memoria.add(VERO, topic="mag", source=FONTE)
    res = memoria.search("magazzino di Verona")
    assert len(res) >= 1
    assert getattr(res, "trattenuti", None) is None


def test_CONTROLLO_POSITIVO_i_risultati_veri_non_si_muovono(memoria):
    """L'avviso è un di più: la lista dei risultati deve restare identica, e
    `search` continua a essere una lista che si itera e si conta."""
    memoria.add(VANTO, topic="mag")
    memoria.add(VERO, topic="mag", source=FONTE)
    res = memoria.search("magazzino di Verona")
    assert len(res) == 1
    assert "480 pallet" in str(res[0])


def test_l_avviso_arriva_anche_da_recall(memoria):
    """`search` e `recall` sono due porte per la stessa cosa: se una avvisa e
    l'altra tace, l'utente che ne usa una sola resta al buio — ed è esattamente
    il difetto che stiamo curando."""
    memoria.add(VANTO, topic="mag")
    res = memoria.recall("export del magazzino")
    assert getattr(res, "trattenuti", None)


def test_l_avviso_NON_fa_cadere_una_lettura(memoria, monkeypatch):
    """⚠️ Un avviso non deve mai costare una risposta. Se il conteggio dei
    trattenuti fallisce — database occupato, schema vecchio, qualunque cosa — la
    lettura deve tornare comunque i suoi risultati."""
    memoria.add(VERO, topic="mag", source=FONTE)

    def esplode(*a, **k):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(type(memoria), "_conta_trattenuti", esplode, raising=False)
    res = memoria.search("magazzino di Verona")
    assert len(res) == 1
