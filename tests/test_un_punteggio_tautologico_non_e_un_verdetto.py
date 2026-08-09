"""Un chunk promosso senza claim si giudica da solo, e prende 99.97.

`promote_chunk_to_fact(sm, hit)` senza `claim` mette la proposizione uguale
alla source: `proposition = hit["text"]` e `source = hit["text"]`. Il moat
verifica allora «X implica X», e il verdetto è ~100 **per costruzione**.
Misurato il 2026-08-04 su tre documenti senza niente in comune:

    proposizione = la fonte stessa        99.95   99.96   99.98
    claim che la fonte NON dice            0.00    0.23    0.00

La seconda riga dice che il gate funziona benissimo quando c'è qualcosa da
verificare. La prima dice che quando non c'è, il punteggio esce lo stesso — e
esce **massimo**.

PERCHÉ NON È UN DETTAGLIO. Il prodotto insegna a leggere quel numero come «the
moat's verdict on that fact, 0-100» e a trust-condizionare su di esso; e la
promozione mette in `verified_by` la citazione esatta del file. Un fatto
promosso senza claim esce quindi con il punteggio di fiducia più alto del corpus
E una provenienza puntuale — mentre nessuno ha verificato niente: il documento
può dire qualunque cosa. Lo stesso testo che `facts add` QUARANTINA entra da qui
come `model_claim` con 99.97.

⚠️ NON È IL DIFETTO CHE IL MODULO AVEVA GIÀ CURATO, ed è la ragione per cui non
si era visto. `test_la_promozione_passa_dal_gate_che_promette` presidia che il
gate giri, e `test_il_chunk_grezzo_resta_promuovibile` dichiara persino il caso
— «senza `claim` la proposizione È il chunk: si implica da sé, e deve continuare
a passare». Quel test guarda **se passa**, e ha ragione a volerlo. Nessuno ha
guardato **quale numero pubblica**.

LA CURA È QUELLA CHE IL PRODOTTO GIÀ INSEGNA: `null` significa «MAI GIUDICATO»,
non «giudicato e bocciato», ed è la descrizione esatta di questo caso. Un fatto
che è la propria fonte non è stato verificato da nessuno, e dirlo con `None` è
più onesto che dirlo con 99.97. Il chunk grezzo continua a passare: cambia solo
che non porta più un verdetto che non ha.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from verimem import Memory
from verimem.document_promote import promote_chunk_to_fact

CHUNK = ("Il piano annuale costa 100 euro e include il supporto base. "
         "La migrazione e' completata e tutti i test passano.")
HIT = {"text": CHUNK, "source_id": "listino.md", "start": 0,
       "end": len(CHUNK), "version": 1}


@pytest.fixture()
def mem() -> Memory:
    return Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "p.db"))


def _fatto(mem: Memory, **kw):
    r = promote_chunk_to_fact(mem.semantic, dict(HIT), **kw)
    f = mem.semantic.get(r["fact_id"]) if r.get("fact_id") else None
    return r, f


def test_un_fatto_che_e_la_propria_fonte_non_porta_un_verdetto(mem):
    """Il cuore: senza claim non c'è niente da verificare, e il punteggio non
    deve esistere. 99.97 qui significa «il testo dice quello che dice»."""
    _, f = _fatto(mem)
    assert f is not None
    assert f.grounding_score is None, (
        f"grounding_score={f.grounding_score}: la proposizione È la source, "
        f"quindi il moat ha verificato X contro X. Un punteggio tautologico "
        f"pubblicato come verdetto è peggio di nessun punteggio, perché il "
        f"prodotto insegna a trust-condizionare proprio su quel numero")


def test_il_chunk_grezzo_CONTINUA_a_passare(mem):
    """Il vincolo dell'altro presidio, che resta valido: la cura non deve
    rendere inutile il modulo. Cambia il numero, non l'ammissione."""
    r, f = _fatto(mem)
    assert r["stored"], r
    assert f is not None and f.status != "quarantined", (
        f"il chunk grezzo non passa più: {f.status if f else None}")


def test_e_la_citazione_resta_attaccata(mem):
    """L'altro valore del modulo: la provenienza puntuale non si perde."""
    r, f = _fatto(mem)
    assert r["citation"] == f"file:listino.md:0-{len(CHUNK)}"
    assert r["citation"] in (f.verified_by or [])


def test_una_claim_DISTILLATA_viene_giudicata_davvero(mem):
    """Il caso per cui il moat serve, e che non deve cambiare: quando la
    proposizione è diversa dalla fonte, c'è qualcosa da verificare."""
    _, f = _fatto(mem, claim="Il piano annuale costa 100 euro.")
    assert f is not None and f.grounding_score is not None, (
        "una claim distillata DEVE essere giudicata: è il caso d'uso "
        "principale del modulo")
    assert f.grounding_score > 40, f.grounding_score


def test_una_claim_che_la_fonte_NON_dice_resta_bocciata(mem):
    """E il verso opposto: la cura non deve spegnere il gate."""
    _, f = _fatto(mem, claim="Il sistema e' certificato ISO 27001 dal 2019.")
    assert f is not None
    assert f.status == "quarantined" or (
        f.grounding_score is not None and f.grounding_score < 40), (
        f"una proposizione che la fonte non sostiene è passata pulita: "
        f"status={f.status} grounding={f.grounding_score}")


def test_il_risultato_DICE_perche_non_c_e_un_punteggio(mem):
    """Un `None` silenzioso si legge come «il gate non ha girato». Qui il gate
    HA girato — è la domanda a non esserci — e il chiamante deve poter
    distinguere i due casi, che è tutta la differenza fra «non verificato» e
    «non verificabile»."""
    r, _ = _fatto(mem)
    nota = str(r.get("grounding_note") or "")
    assert nota, (
        f"il risultato non dice perché manca il punteggio: {r}")
    assert "source" in nota.lower() or "fonte" in nota.lower(), nota
