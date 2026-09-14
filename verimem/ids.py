"""Gli id del prodotto, generati in un posto solo.

Un id era un uuid tagliato — `uuid.uuid4().hex[:n]` — in diciannove punti di
sedici file. In esadecimale ogni carattere è una cifra con probabilità 10/16,
quindi un id di sole cifre esce con probabilità (10/16)^n::

    hex[: 8]    2.3283%   uno ogni 43
    hex[:12]    0.3553%   uno ogni 281
    hex[:16]    0.0542%   uno ogni 1.845

Un id di sole cifre si legge come un numero: dai rilevatori che contano le
quantità in una frase, da chi guarda un registro, da chiunque lo incontri fuori
dal campo che lo ospita. Il caso peggiore non era quello segnalato per primo —
la lunghezza 8 sbaglia sei volte e mezzo più spesso di quella dei fatti.

🔑 LA CURA NON CAMBIA L'ALFABETO. «Almeno una lettera» in esadecimale vuol dire
almeno un carattere fra ``a`` e ``f``: l'id resta un esadecimale valido della
stessa lunghezza, e nessun consumatore se ne accorge — tranne chi lo stava
scambiando per un numero.

Ticket: T84.
"""
from __future__ import annotations

import uuid

#: I caratteri esadecimali che NON sono cifre. Un id che ne contiene almeno
#: uno non può essere letto come un numero.
_LETTERE = frozenset("abcdef")


def id_nuovo(lunghezza: int = 12) -> str:
    """Un id esadecimale di ``lunghezza`` caratteri, con almeno una lettera.

    Rigenera un numero LIMITATO di volte, poi ripiega. Rigenerare è la via
    pulita — non tocca l'entropia e non rende prevedibile nessuna posizione —
    ma un ciclo senza uscita sta in un percorso di SCRITTURA: se il generatore
    sottostante fosse rotto o truccato, il prodotto si pianterebbe invece di
    scrivere, e un difetto raro diventerebbe un blocco. Otto tentativi portano
    la probabilità di arrivare al ripiego sotto una su 10^13 nel formato
    peggiore; il ripiego, quando tocca, sostituisce l'ultimo carattere con una
    lettera DERIVATA dall'uuid stesso, così resta casuale e non costante.

    Args:
        lunghezza: quanti caratteri esadecimali. I formati in uso sono 8, 12 e
            16; valori maggiori di 32 non hanno più uuid da tagliare.

    Returns:
        l'id. Stessa forma di prima — esadecimale minuscolo, stessa
        lunghezza — con la sola differenza che non è mai tutto cifre.
    """
    if lunghezza < 1:
        raise ValueError(f"lunghezza {lunghezza}: un id vuoto non è un id")
    if lunghezza > 32:
        raise ValueError(
            f"lunghezza {lunghezza}: un uuid ha 32 caratteri esadecimali, "
            "oltre non c'è niente da tagliare")
    #: ⚠️ Con lunghezza 1 le lettere disponibili sono 6 su 16: si rigenera più
    #: spesso, e non è un formato che il prodotto usi.
    candidato = ""
    for _ in range(8):
        candidato = uuid.uuid4().hex[:lunghezza]
        if _LETTERE.intersection(candidato):
            return candidato
    #: IL RIPIEGO, che in pratica non si raggiunge mai e che esiste perché il
    #: «mai» di un percorso di scrittura deve essere scritto, non sperato. La
    #: lettera si ricava dai caratteri scartati dell'ultimo uuid: nessuna
    #: costante, nessuna posizione con un valore fisso.
    coda = uuid.uuid4().hex
    lettera = next((c for c in coda if c in _LETTERE), "a")
    return candidato[:-1] + lettera


__all__ = ["id_nuovo"]
