"""Il contratto di uscita di un fatto: un punto solo, per tutte le superfici.

Misurato il 2026-07-30, prima che questo modulo esistesse. In mcp_server.py 13
punti costruivano a mano il dict di un fatto, e altri 34 moduli facevano lo
stesso ognuno a modo suo. Cosa usciva davvero, sui 13:

    proposition        13/13     (il campo del giorno uno)
    grounding_score     6/13
    asserted_at         2/13
    confidence_tier     0/13
    epistemic           0/13
    writer_principal    0/13
    last_verified_at    0/13

Quattro campi calcolati, persistiti e documentati col loro razionale, che
nessun utente poteva leggere da nessuna superficie. Non erano superfici rotte:
era l'assenza di un contratto, e senza contratto la probabilita' di dimenticare
un campo e' quella misurata — sette punti su tredici hanno dimenticato il
verdetto del moat.

Sta in un modulo suo, e non dentro ``semantic``, per due ragioni pratiche: i
moduli che serializzano fatti sono deliberatamente disaccoppiati da ``semantic``
(nessuno lo importa), e importarlo per un solo dizionario avrebbe accoppiato
mezzo prodotto al modulo piu' pesante.
"""
from __future__ import annotations

from typing import Any

#: Campi che di proposito NON escono, col motivo. Un'esclusione costa una riga
#: di spiegazione a chi la fa — e' l'unico attrito che tiene onesta la lista.
NON_ESCONO = frozenset({
    # impronta interna anti-tamper: non dice nulla a chi legge il fatto
    "source_signature",
})

#: Presenti anche da vuoti. Per il verdetto la ragione e' sostanziale: una
#: chiave che manca si legge «questa superficie non lo espone», un null
#: esplicito si legge «il moat non ha girato», e distinguere le due cose e'
#: cio' che questo prodotto vende.
#:
#: `verified_by` sta qui per la stessa ragione e l'ha imposto la suite intera:
#: omettendolo da vuoto, 24 test di provenienza sono andati rossi. Avevano
#: ragione — una lista vuota di garanti DICE qualcosa, «nessuno lo avalla», che
#: non e' «questa superficie non espone i garanti».
SEMPRE = frozenset({
    "id", "proposition", "topic", "confidence", "created_at", "status",
    "grounding_score", "verified_by",
})

_NOMI: tuple[str, ...] | None = None


def _nomi_campi() -> tuple[str, ...]:
    """I nomi dal dataclass, una volta sola.

    Import pigro: ``semantic`` importa questo modulo per ``Fact.as_payload``,
    quindi a livello di modulo sarebbe un ciclo.
    """
    global _NOMI
    if _NOMI is None:
        from dataclasses import fields

        from .semantic import Fact
        _NOMI = tuple(f.name for f in fields(Fact) if f.name not in NON_ESCONO)
    return _NOMI


def fact_payload(f: Any) -> dict[str, Any]:
    """Il fatto come esce dal prodotto, da QUALUNQUE oggetto fatto-simile.

    Accetta anche cio' che non e' un ``Fact``: le superfici ricevono fake nei
    test, righe adattate, proxy. Il primo tentativo chiamava ``f.as_payload()``
    dentro i moduli e ha acceso 15 rossi con ``'_FakeFact' object has no
    attribute 'as_payload'`` — aveva irrigidito un contratto d'ingresso che era
    sempre stato duck-typed, e in produzione sarebbe esploso sul primo oggetto
    non-Fact.

    I nomi dei campi vengono dal dataclass, i valori da ``getattr``: lo schema
    resta uno solo, e il campo aggiunto domani esce da tutte le superfici
    insieme senza chiedere niente a chi lo aggiunge.

    I vuoti si omettono — ogni chiave inutile e' contesto rubato a chi legge
    dall'altra parte — tranne quelli in ``SEMPRE``.
    """
    out: dict[str, Any] = {}
    for nome in _nomi_campi():
        valore = getattr(f, nome, None)
        if nome in SEMPRE:
            out[nome] = valore
        elif valore is None or valore == [] or valore == {} or valore == "":
            continue
        else:
            out[nome] = valore
    return out


__all__ = ["NON_ESCONO", "SEMPRE", "fact_payload"]
