"""L'avviso sul fatto troppo lungo esisteva, ed era ottimo. Nel log.

MISURATO da utente, scrivendo un fatto di 4476 caratteri con `Memory.add`::

    log:  «long fact: id=… is 4476 chars — beyond the embedder window
           (~512 tokens); recall will only see the head. For whole documents
           use DocumentIndex/index_file (chunked + cited).»
    ricevuta:  warnings = []

L'avviso dice tutto quello che serve — la dimensione, il limite, e cosa fare
invece — e **non arriva nel canale che chi scrive legge**. Il commento che lo
accompagna in `semantic.py` lo chiama «non-silent over-window guard»: è stato
scritto apposta per non essere silenzioso, ed è silenzioso esattamente per il
chiamante.

⚠️ È «il meccanismo c'è, il chiamante non lo alimenta» sul lato SCRITTURA. E le
conseguenze sono note e già in memoria: un fatto oltre la finestra embedda solo
la testa, quindi il recall semantico non vede il resto — è la ragione per cui
il protocollo di casa prescrive di spezzare i fatti lunghi o di usare
`verimem index`.

Il controllo sta in `client.py` e non in `semantic.py` per due motivi: quel
file è di un'altra istanza mentre scrivo, e soprattutto **la soglia va letta da
una funzione sola**. Qui c'è quella funzione; quando `semantic.py` verrà
toccato, potrà chiamarla invece di rileggere l'ambiente per conto suo — due
copie di una soglia divergono, ed è la classe che questa casa paga di più.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from verimem.client import Memory, soglia_fatto_lungo

LUNGO = ("Il protocollo di analisi prevede che " + " ".join(
    f"il passo numero {i} venga eseguito dall'operatore di turno registrando "
    f"il valore rilevato sul registro di reparto" for i in range(1, 40))
    + ". Il limite di quantificazione è 0,2 mg/l.")


@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "s.db"))


def _avvisi_lunghezza(ricevuta) -> list:
    return [w for w in (ricevuta.get("warnings") or [])
            if "long_fact" in str(w.get("layer", ""))]


def test_chi_scrive_un_fatto_lungo_lo_viene_a_sapere(mem):
    """IL CUORE: l'avviso c'era e non arrivava a chi scrive."""
    assert len(LUNGO) > soglia_fatto_lungo(), "il banco non supera la soglia"
    ric = mem.add(LUNGO, topic="lab/protocollo")
    avvisi = _avvisi_lunghezza(ric)
    assert avvisi, f"nessun avviso sulla lunghezza: {ric.get('warnings')}"
    testo = str(avvisi[0])
    assert str(len(LUNGO)) in testo, testo
    assert "index" in testo.lower(), "l'avviso deve dire cosa fare invece"


def test_un_fatto_normale_non_porta_avvisi_di_lunghezza(mem):
    """IL PRESIDIO: quasi tutto il corpus è fatto di frasi brevi, e lì non
    deve comparire nulla di nuovo."""
    ric = mem.add("Il magazzino K-77 di Rovigo ha 4200 metri quadrati.",
                  topic="az/mag")
    assert not _avvisi_lunghezza(ric)


def test_il_fatto_lungo_ENTRA_lo_stesso(mem):
    """L'ALTRO PRESIDIO, e vale più del primo: l'avviso AVVISA, non blocca.
    Un fatto lungo è legittimo — il testo non viene mai troncato e il fatto
    resta servibile. Se questo cade, abbiamo trasformato un consiglio in un
    divieto."""
    ric = mem.add(LUNGO, topic="lab/protocollo")
    assert ric.get("stored") is True
    assert ric.get("status") != "quarantined", ric.get("status")


def test_la_soglia_si_legge_da_UNA_funzione(monkeypatch):
    """Perché la soglia non finisca in due posti che divergono: c'è una
    funzione, e legge la stessa variabile d'ambiente documentata."""
    monkeypatch.setenv("ENGRAM_LONG_FACT_WARN_CHARS", "500")
    assert soglia_fatto_lungo() == 500
    monkeypatch.setenv("ENGRAM_LONG_FACT_WARN_CHARS", "non-un-numero")
    assert soglia_fatto_lungo() == 2000, "un valore illeggibile torna al default"
    monkeypatch.setenv("ENGRAM_LONG_FACT_WARN_CHARS", "0")
    assert soglia_fatto_lungo() == 0, "zero disattiva, come documentato"
