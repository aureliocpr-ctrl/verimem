"""Il lettore dell'esito di un processo: **uno solo** per tutto il banco.

Perché condiviso e non una riga in ogni file: la classe che questo cura è nata
proprio da una lettura copiata male, e tredici copie della stessa lettura
divergono — la prima a divergere sarà quella che nessuno rilegge. La lista dei
banchi che ancora non lo usano, e il cricchetto che impedisce al
quattordicesimo di entrare, stanno in
``test_nessun_banco_nuovo_ignora_l_esito_del_subprocess.py``.

IL DIFETTO CHE CURA, misurato il 2026-08-14 su
``test_la_ricevuta_non_diceva_quale_cifra_mancava.py``: il banco leggeva
``(stdout or "") + (stderr or "")`` e non guardava mai il ``returncode``. Un
processo morto lascia un output TRONCO, quindi ogni assert riferiva «manca la
stringa X» invece di «il processo è morto» — e in CI il danno raddoppia, perché
la piattaforma tronca le righe lunghe e la coda, dove starebbe la causa, viene
tagliata via. Quel rosso è rimasto senza causa per un giorno intero.
"""
from __future__ import annotations

import subprocess


def _testo(canale) -> str:
    """⚠️ `subprocess` rende `None` quando un canale non è stato catturato, e
    `bytes` quando manca `text=True`. Sommare i due canali senza questo esplode
    con `TypeError` PRIMA di arrivare all'assert: in CI si legge l'errore del
    banco al posto del motivo per cui il banco è rosso — il difetto vero resta
    sotto. Non è cosmesi difensiva: qui il fallimento del banco MASCHERA il
    fallimento che il banco esiste per mostrare.
    """
    if canale is None:
        return ""
    if isinstance(canale, bytes):
        return canale.decode("utf-8", errors="replace")
    return canale


def esito(risultato: subprocess.CompletedProcess, atteso: int | None = 0) -> str:
    """L'output del processo, dopo aver dichiarato com'è finito.

    ``atteso=0``   il processo doveva riuscire (il caso normale).
    ``atteso=None`` qualunque uscita va bene — **da usare solo dichiarando
    perché**, per esempio in un banco dove il fallimento del comando *è* il
    dato misurato.

    Il messaggio mette il codice PRIMA e la coda DOPO: se viene tagliato si
    perde la coda, non il verdetto.
    """
    grezzo = _testo(risultato.stdout) + _testo(risultato.stderr)
    if atteso is not None and risultato.returncode != atteso:
        raise AssertionError(
            f"PROCESSO-MORTO exit={risultato.returncode} (atteso {atteso}) "
            f"len_stdout={len(_testo(risultato.stdout))} "
            f"len_stderr={len(_testo(risultato.stderr))} "
            f"coda={grezzo[-200:]!r}")
    return grezzo
