"""Il tetto ai thread di calcolo, applicato PRIMA che torch esista.

PERCHE': su una macchina a 20 core torch sceglie 10 thread per processo, e
verimem ne fa girare undici (nove server MCP piu' due daemon). Nessun punto del
prodotto impostava un tetto — misurato il 20/08 con ``git grep`` su
``set_num_threads``, ``OMP_NUM_THREADS`` e ``MKL_NUM_THREADS``: zero occorrenze
in ``verimem/``, in ``scripts/`` e in ``.github/``.

E NON E' UN COMPROMESSO MEMORIA-CONTRO-VELOCITA'. A/B a una variabile, stesso
script, un processo per volta::

    torch   thread   impegnato  residente   batch1   batch32   batch256
     10       35       1522MB      502MB    0,11ms    4,23ms     4,26ms
      4       13        997MB      492MB    0,10ms    0,55ms     3,66ms
      2        9        928MB      487MB    0,11ms    0,81ms     5,87ms

A quattro thread si impegnano 525 MB in meno **e si va piu' veloce su tutti e
tre i carichi**: con dieci, il batch da 32 costa 4,23 ms contro 0,55 — otto
volte tanto. A dieci si perde su ENTRAMBI gli assi, per contesa fra thread.

PERCHE' QUI E NON ACCANTO A ``import torch``: OpenMP legge queste variabili
quando la sua libreria si inizializza, cioe' al primo import di torch — e in
questo prodotto torch entra tardi e da piu' strade (il giudice locale, il
reranker, l'encoder), non da un punto solo. Chiamare ``set_num_threads``
accanto a ognuna sarebbe la quinta copia di una regola, e le copie divergono.
Qui e' UNA riga che vale per tutte le strade, e vale anche per numpy/MKL, che
pagano la stessa contesa.

SETDEFAULT, MAI SOVRASCRIVERE: chi ha messo il proprio numero in ambiente lo
tiene. E' la stessa disciplina di ``_compat.init_env_aliases`` e di
``mode.apply_engram_mode``, che girano a due righe da qui.

LIMITE DICHIARATO: la misura sopra e' una matmul sintetica, non il percorso
vero degli embedding, e la macchina era sotto carico. I RAPPORTI reggono, i
tempi assoluti valgono meno.
"""
from __future__ import annotations

import os

#: Il tetto scelto: il migliore misurato su memoria E su tempo.
TETTO_PREDEFINITO = 4

#: Le variabili che governano i thread di calcolo. OpenMP le legge
#: all'inizializzazione, quindi vanno impostate prima del primo import.
_VARIABILI = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
              "NUMEXPR_NUM_THREADS")

#: I nomi con cui si puo' chiedere un tetto diverso, nei tre prefissi di casa.
_CHIAVI = ("VERIMEM_TORCH_THREADS", "ENGRAM_TORCH_THREADS",
           "HIPPO_TORCH_THREADS")


def tetto_richiesto() -> int:
    """Il tetto da applicare: quello chiesto in ambiente, o il predefinito.

    Con ``VERIMEM_TORCH_THREADS=0`` il tetto si disattiva — chi fa lotti grandi
    e ha misurato di volerne di piu' deve poterlo dire senza toccare il codice.
    """
    for nome in _CHIAVI:
        grezzo = os.environ.get(nome)
        if grezzo:
            try:
                return max(0, int(grezzo))
            except ValueError:
                continue
    return TETTO_PREDEFINITO


def applica_tetto_thread() -> dict[str, str]:
    """Imposta le variabili non ancora presenti. Rende quelle impostate."""
    tetto = tetto_richiesto()
    if tetto <= 0:                      # 0 = disattivato di proposito
        return {}
    messe: dict[str, str] = {}
    for nome in _VARIABILI:
        if not os.environ.get(nome):
            os.environ[nome] = str(tetto)
            messe[nome] = str(tetto)
    return messe
