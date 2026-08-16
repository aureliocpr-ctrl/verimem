"""Le stringhe che l'utente legge non portano il nome di una persona reale.

Un esempio in un aiuto di comando o nella descrizione di un parametro non è un
commento: è testo che arriva a chi usa il prodotto — `--help` lo stampa, e la
descrizione di uno strumento MCP viene letta a runtime dall'agente dell'utente.
Il nome proprio di chi ha scritto il codice, lì dentro, è un residuo di sviluppo
che il pacchetto porta fuori dal progetto.

Trovati due, entrambi nel wheel:

    mcp_server.py   "description": "who is updating (claude/<nome>)"
    teams/cli.py    help="Sender display name (free-form, e.g. '<nome>')."

Il perimetro è stretto **di proposito**, e la parte stretta è la ragione per cui
questo collaudo può esistere senza diventare rumore:

  - guarda **solo** i valori di `help=` e delle chiavi `"description"`, cioè le
    superfici destinate a un lettore esterno;
  - **non** guarda i commenti né i docstring. Là il nome può comparire come dato
    di una misura — «le parole più condivise erano NON, MCP, <nome>: rumore» —
    e quella è una menzione, non un esempio da imitare. Un controllo che non
    distinguesse uso da menzione bloccherebbe una frase corretta;
  - **non** guarda gli URL: l'indirizzo del repository contiene il nome
    dell'organizzazione e deve contenerlo.

Il secondo test è quello che tiene onesto il primo: se il criterio smettesse di
riconoscere il nome, «nessuna occorrenza» resterebbe vero e vuoto.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parent.parent
PACCHETTO = RADICE / "verimem"

#: Il nome proprio da non far uscire. Sta qui una volta sola, e questo file
#: dichiara sotto perché può contenerlo.
#:
#: registro-esente: il nome qui sotto è il dato di prova del controllo, non
#: un'attribuzione: senza, il collaudo non potrebbe cercare nulla.
NOME = "aurelio"

#: `help="…"` di un'opzione, e `"description": "…"` di uno schema MCP.
#:
#: Le due virgolette sono trattate separatamente **di proposito**: una stringa fra
#: doppie contiene quasi sempre apici singoli — proprio negli esempi, che sono ciò
#: che questo collaudo cerca. Un'unica classe `[^"']` si ferma al primo apice e
#: taglia via la parte che conta: scritto così, il primo test restava verde su un
#: pacchetto sporco. Lo ha rivelato il controllo positivo qui sotto.
_SUPERFICI = re.compile(
    r"""(?:help\s*=\s*|["']description["']\s*:\s*)"""
    r"""(?:"(?P<doppie>[^"]{0,300})"|'(?P<singole>[^']{0,300})')""",
    re.IGNORECASE,
)

#: L'indirizzo del repository contiene il nome dell'organizzazione: è legittimo.
_URL = re.compile(r"https?://\S+")


def _occorrenze(percorso: Path) -> list[tuple[int, str]]:
    testo = percorso.read_text(encoding="utf-8", errors="replace")
    fuori = []
    for m in _SUPERFICI.finditer(testo):
        contenuto = m.group("doppie") or m.group("singole") or ""
        if NOME in _URL.sub("", contenuto).lower():
            riga = testo.count("\n", 0, m.start()) + 1
            fuori.append((riga, contenuto[:90]))
    return fuori


def test_nessuna_superficie_pubblica_nomina_una_persona():
    """Gli aiuti dei comandi e le descrizioni degli strumenti non portano un nome."""
    trovati = {
        str(p.relative_to(RADICE)): occ
        for p in PACCHETTO.rglob("*.py")
        if (occ := _occorrenze(p))
    }
    assert not trovati, (
        f"queste stringhe arrivano all'utente e nominano una persona: {trovati}. "
        f"Un esempio in un `--help` o nella descrizione di uno strumento va reso "
        f"generico — il nome è un residuo di sviluppo, non un'informazione.")


def test_il_criterio_riconosce_un_nome_in_una_superficie():
    """Il controllo positivo: senza, «nessuna occorrenza» sarebbe vero e vuoto."""
    finto = (
        f'help="Sender display name (free-form, e.g. \'{NOME}\')."\n'
        f'"description": "the repo is https://github.com/{NOME}cpr-ctrl/verimem"\n'
    )
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "finto.py"
        p.write_text(finto, encoding="utf-8")
        occ = _occorrenze(p)

    assert len(occ) == 1, (
        f"il criterio deve trovare l'esempio nell'aiuto e IGNORARE l'URL del "
        f"repository, che il nome lo contiene per forza: ha trovato {occ}")
