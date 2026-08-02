"""La promozione di un chunk prometteva il gate e non ne chiamava nessuno.

`document_promote.py` si presenta come «the last brick of the document RAG» e
dichiara, nel suo docstring, di promuovere un chunk «through the same
anti-confab discipline as everything else, NEVER AROUND IT», con
«``writer_role="document_promote"`` — a dedicated, non-trusted writer, SO THE
FULL ADMISSION GATE RUNS».

Misurato eseguendo (store isolato, quattro promozioni sullo stesso chunk):

    chunk grezzo (claim = testo)     stored=True  status=model_claim  grounding=None
    claim SOSTENUTA dal chunk        stored=True  status=model_claim  grounding=None
    claim NON sostenuta (falsa)      stored=True  status=model_claim  grounding=None
    claim confabulatoria             stored=True  status=model_claim  grounding=None

Nessun gate. Non «un gate parziale»: `grounding_score` e' None su quattro
promozioni su quattro, e passa anche «La migrazione e' stata completata e
tutti i test passano» — la confabulazione-scuola che il prodotto quarantina
su ogni altro canale — e passa «Il piano annuale costa 500 euro», che il
chunk CONTRADDICE.

E PESA PIU' DI UNA SCRITTURA QUALUNQUE, perche' la promozione mette la
citazione esatta del file in `verified_by`: il fatto esce con l'aria di essere
verificato DAL DOCUMENTO, mentre il documento puo' dire il contrario. La
provenienza diventa una decorazione.

LA SOURCE C'ERA GIA' E VENIVA BUTTATA. `hit["text"]` e' il testo del chunk, e
quando il chiamante passa un `claim` distillato quel testo e' esattamente
l'input che L4 vuole: source = il chunk, claim = la frase. Il caso d'uso
principale del modulo E' il caso d'uso principale del moat, e il chunk
finiva usato solo come proposizione.

Il difetto e' stato trovato in sola lettura dall'altra istanza; qui e'
eseguito, ed e' risultato piu' largo di quanto la lettura mostrasse — non
mancava solo L4, non girava nemmeno lo screen lessicale.
"""
from __future__ import annotations

import pytest

from verimem.document_promote import promote_chunk_to_fact
from verimem.semantic import SemanticMemory

CHUNK = ("Il piano annuale del prodotto costa 100 euro e include il supporto "
         "via email.")


def _hit() -> dict:
    return {"text": CHUNK, "source_id": "listino.md", "start": 0, "end": 80,
            "version": 1}


@pytest.fixture()
def mem(tmp_path):
    return SemanticMemory(db_path=tmp_path / "s.db")


def _promosso(mem, **kw):
    r = promote_chunk_to_fact(mem, _hit(), **kw)
    f = mem.get(r.get("fact_id") or "") if r.get("stored") else None
    return r, f


def test_una_claim_SOSTENUTA_dal_chunk_viene_giudicata(mem):
    """Il contratto minimo: se il gate gira, lascia un verdetto. `None`
    significa «mai giudicato», e su questo canale era sempre None."""
    _r, f = _promosso(mem, claim="Il piano annuale costa 100 euro.")
    assert f is not None, "la promozione non ha nemmeno scritto"
    assert f.grounding_score is not None, (
        "grounding_score None: il moat non ha girato, e il docstring del "
        "modulo promette «the full admission gate runs»")


def test_una_claim_che_il_chunk_CONTRADDICE_non_passa_pulita(mem):
    """Il caso che conta: il documento dice 100 euro e supporto via email, la
    claim dice 500 e telefonico. Promuoverla con la citazione del file in
    `verified_by` la fa sembrare verificata DAL documento che la smentisce."""
    _r, f = _promosso(
        mem, claim="Il piano annuale costa 500 euro e include il supporto "
                   "telefonico.")
    if f is None:
        return  # respinta del tutto: va bene
    # `(grounding or 0) < 40` sarebbe vero anche col gate SPENTO — un test
    # cosi' passa sul difetto che dovrebbe prendere. Serve che il gate abbia
    # GIRATO (verdetto presente) e che il verdetto sia negativo.
    assert f.status == "quarantined" or (
        f.grounding_score is not None and f.grounding_score < 40), (
        f"promossa come sana: status={f.status} "
        f"grounding={f.grounding_score} — il chunk dice il contrario")


def test_una_confabulazione_non_diventa_un_fatto_citato(mem):
    """«La migrazione e' stata completata e tutti i test passano» e' la
    confabulazione-scuola: il prodotto la quarantina su ogni altro canale."""
    _r, f = _promosso(
        mem, claim="La migrazione e stata completata e tutti i test passano.")
    if f is None:
        return
    assert f.status == "quarantined" or (
        f.grounding_score is not None and f.grounding_score < 40), (
        f"confabulazione promossa: status={f.status} "
        f"grounding={f.grounding_score}")


def test_il_chunk_grezzo_resta_promuovibile(mem):
    """Senza `claim` la proposizione E' il chunk: si implica da se', e deve
    continuare a passare. Il gate non deve rendere inutile il modulo."""
    r, f = _promosso(mem)
    assert r["stored"], r
    assert f is not None and f.status != "quarantined", (
        f"il chunk grezzo non passa piu': {f.status if f else None}")


def test_la_citazione_resta_attaccata(mem):
    """Il valore del modulo non si perde con la cura: la citazione esatta
    resta in `verified_by` e in `source_episodes`."""
    r, f = _promosso(mem, claim="Il piano annuale costa 100 euro.")
    assert r["citation"] == "file:listino.md:0-80", r
    assert f is not None
    assert r["citation"] in (f.verified_by or []), f.verified_by
    assert r["citation"] in (f.source_episodes or []), f.source_episodes
