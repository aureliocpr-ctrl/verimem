"""La soglia dell'ANN, in un modulo che non importa niente di pesante.

Esiste per una ragione sola, e va detta perche' altrimenti sembra un livello in
piu' senza motivo: **decidere se l'ANN serve non deve costare quanto usarlo.**

La soglia viveva in ``ann_index``, che importa ``faiss`` a livello di modulo.
Chiunque volesse sapere «questo corpus e' abbastanza grande da giustificare un
indice?» — una domanda che si risponde confrontando due interi — pagava il
caricamento della libreria e della sua DLL nativa. Misurato il 2026-07-31 su
questa macchina scarica: aprire lo store costa **978,8 ms** con faiss e
**704,2 ms** senza, cioe' **274,6 ms** per una risposta che nel 100% dei casi
reali (corpus da 6517 fatti, gate a 100.000) e' «no». Da un interprete vuoto
l'import completo costa di piu' — 925,2 contro 276,5 ms — ma meta' e' numpy,
che allo store serve comunque: il numero da citare e' il primo.

Il costo si vedeva nei trace degli stalli: su 38 file in
``~/.engram/hang-traces/``, il modulo piu' presente negli stack e' ``faiss``
(387 occorrenze), e i tool piu' colpiti sono i piu' leggeri — ``hippo_health``
13, ``hippo_stats`` 10.

Qui dentro non si importa nulla oltre ``os``: e' l'unico modo perche' la
domanda resti gratis.
"""
from __future__ import annotations

import os

#: Sotto questo numero di fatti la ricerca esatta vince: costruire e
#: sincronizzare l'indice costa piu' di quanto la query sublineare faccia
#: risparmiare. Il gate si somma all'auto-enable (faiss importabile,
#: ``ENGRAM_ANN_RECALL=0`` per uscirne — ``semantic._ann_recall_enabled``).
_ANN_MIN_N = 100_000


def default_min_n() -> int:
    """La soglia effettiva: ``ENGRAM_ANN_MIN_N`` se valorizzata, altrimenti il
    default del modulo. E' la stessa env che il deploy usa per abbassare il
    gate, quindi chi la legge qui e chi la legge in ``ANNCache`` vedono per
    costruzione lo stesso numero."""
    v = os.environ.get("ENGRAM_ANN_MIN_N", "").strip()
    return int(v) if v.isdigit() else _ANN_MIN_N


__all__ = ["_ANN_MIN_N", "default_min_n"]
