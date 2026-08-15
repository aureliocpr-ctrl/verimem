"""La dimensione del modello del giudice è la stessa in tutti i posti che la dicono.

La cifra vive in **quattro** punti: due nell'aiuto della riga di comando e due
nella vetrina pubblica. Sono quattro copie dello stesso numero, e le copie
divergono: basta che qualcuno aggiorni il modello e ne corregga tre.

Non è un rischio teorico. Nella stessa giornata in cui questo collaudo è stato
scritto, l'ultimo passo della procedura di rilascio nominava ancora il pacchetto
precedente al rinominamento — una copia rimasta indietro nel commit stesso che
aveva rinominato tutto il resto.

Qui non si può leggere il numero dal prodotto come si farebbe con una costante:
la dimensione di un file remoto non è nel codice. Quindi il collaudo fa l'unica
cosa che resta e che ha valore — **verifica che le copie coincidano fra loro**,
così una diventa impossibile da cambiare da sola.

Il secondo test è quello che tiene onesto il primo: se il numero sparisse da
tutti i posti, «tutte le copie coincidono» sarebbe vero e vuoto.
"""
from __future__ import annotations

import re
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent

#: Dove la cifra è dichiarata. Aggiungere un posto qui è più facile che
#: accorgersi di una copia dimenticata.
SORGENTI = {
    "riga di comando": RADICE / "verimem" / "cli.py",
    "vetrina": RADICE / "README.md",
}

#: «~656 MB», «656 MB», «656MB». Cattura il numero, non la formattazione.
_TAGLIA = re.compile(r"~?\s*(?P<mb>\d{3,4})\s*MB\b[^.\n]{0,40}(gate|judge)", re.IGNORECASE)


def _taglie_dichiarate(percorso: Path) -> list[str]:
    testo = percorso.read_text(encoding="utf-8", errors="replace")
    return [m.group("mb") for m in _TAGLIA.finditer(testo)]


def test_la_taglia_del_giudice_coincide_ovunque():
    """Quattro copie dello stesso numero: se una cambia, cambiano tutte o è rosso."""
    per_sorgente = {nome: _taglie_dichiarate(p) for nome, p in SORGENTI.items()}
    tutte = [mb for valori in per_sorgente.values() for mb in valori]

    assert tutte, (
        f"nessuna dichiarazione della taglia del modello trovata in "
        f"{list(SORGENTI)}: o è sparita, o la forma è cambiata e questo collaudo "
        f"va riscritto — non cancellato")

    distinte = set(tutte)
    assert len(distinte) == 1, (
        f"la taglia del modello del giudice è dichiarata con valori diversi: "
        f"{per_sorgente}. Le copie hanno divergiuto: allinearle tutte, o farle "
        f"leggere da un posto solo.")


def test_la_cifra_e_dichiarata_in_ENTRAMBE_le_superfici():
    """Il controllo che impedisce al primo di essere vero e vuoto.

    Se il numero sparisse dalla vetrina, «tutte le copie coincidono» resterebbe
    vero — e l'utente non saprebbe più quanto scarica.
    """
    mancanti = [nome for nome, p in SORGENTI.items() if not _taglie_dichiarate(p)]
    assert not mancanti, (
        f"queste superfici non dichiarano più quanto pesa il modello: {mancanti}. "
        f"Chi installa deve poterlo sapere prima di lanciare il comando.")
