"""L'ultimo canale che scriveva senza gate era quello dei fatti DERIVATI.

Il README apre con «Every write passes an admission gate». Il consolidamento
notturno sintetizza da un cluster di episodi una skill, e dal suo `rationale`
— un testo che un LLM ha SCRITTO riassumendo il cluster — ricava un fatto, che
finiva in `semantic.store()` (`sleep.py:456`).

`store()` fa redazione, screen di sicurezza e hard-gate sulla provenienza, e
NON fa girare né L1 né il moat L4 (vedi
`test_store_non_e_il_gate_completo`). Quindi la scrittura più a rischio di
tutte — derivata, non osservata, prodotta da un modello — era l'unica a non
essere controllata.

È l'ultimo dei quattro canali: `document_promote` (`8d4d393d`),
`transcript_promote` (`88713b32`), `conversation_ingest` (che una via propria
ce l'aveva già), e questo.

La source è `body`, il testo degli episodi da cui il razionale è tratto: è
esattamente ciò contro cui va confrontato, ed era già nella stessa funzione.
"""
from __future__ import annotations

import inspect

from verimem import sleep as sleep_mod


def test_la_sintesi_chiama_il_gate():
    """Il criterio strutturale: la funzione che costruisce il fatto derivato
    deve nominare il gate. Se un giorno qualcuno la riscrive senza, questo
    test lo dice — ed è il modo in cui il difetto è nato la prima volta."""
    src = inspect.getsource(sleep_mod.SleepEngine._synthesize_from_cluster)
    assert "run_validation_gate" in src, (
        "il fatto derivato dal cluster non passa dal gate: e' la scrittura "
        "piu' a rischio del prodotto — un testo che un LLM ha scritto — e il "
        "README promette che ogni scrittura passi da li'")


def test_la_source_e_il_materiale_del_cluster():
    """Non basta chiamare il gate: senza `source` il moat NON gira e il fatto
    entra come `model_claim` non giudicato. La source giusta è il testo degli
    episodi, che la funzione ha già in mano."""
    src = inspect.getsource(sleep_mod.SleepEngine._synthesize_from_cluster)
    assert "source=body" in src, (
        "il gate viene chiamato senza la source: girerebbe solo lo screen "
        "lessicale, e il confronto con l'evidenza — il pezzo che conta su un "
        "testo generato — non avverrebbe")


def test_il_punteggio_finisce_sul_fatto():
    """Un fatto giudicato che non porta il verdetto è indistinguibile da uno
    mai giudicato: è la distinzione che tutto il prodotto difende."""
    src = inspect.getsource(sleep_mod.SleepEngine._synthesize_from_cluster)
    assert "grounding_score=" in src, src[-400:]


def test_un_giudice_assente_non_promuove():
    """Se il gate non è raggiungibile il fatto resta `model_claim` con
    `grounding_score=None` — «mai giudicato», non «giudicato e passato» — e il
    consolidamento non cade per una scrittura."""
    src = inspect.getsource(sleep_mod.SleepEngine._synthesize_from_cluster)
    assert "except Exception" in src and "_punteggio = None" in src, src[-400:]
