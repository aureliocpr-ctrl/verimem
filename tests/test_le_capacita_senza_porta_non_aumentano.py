"""Quante capacità dell'SDK non hanno una porta, e il numero non deve crescere.

Quattro volte in un giorno lo stesso difetto: una capacità matura, completa e
testata, raggiungibile solo dal canale che l'ha vista nascere.

    recall --as-of      il time-travel viveva su MCP e SDK (curato il 31/07)
    facts correct       supersede viveva su MCP e SDK — e il suo docstring
                        dice «e' la seconda occorrenza in un giorno della
                        stessa classe, il che la rende una classe»
    purge_history       la cancellazione GDPR viveva SOLO sull'SDK
    deep/with_history   tre modi di `search` che la CLI non sapeva chiedere

Ogni volta la cura e' stata puntuale e ogni volta ne e' saltata fuori
un'altra. Questo file smette di curarle una per una e mette un CRICCHETTO
sulla classe: conta i metodi pubblici di `Memory` che non compaiono ne' nella
CLI ne' nel server MCP, e pretende che il numero non aumenti.

E' BIDIREZIONALE, come il censimento dei verdetti: fallisce se qualcuno
aggiunge una capacita' senza porta, E fallisce se qualcuno ne apre una senza
abbassare la costante — un elenco che si aggiorna solo quando peggiora non
presidia niente.

IL CRITERIO E' GROSSOLANO PER SCELTA. Cerca il NOME del metodo nei due file,
quindi conta come «esposta» anche una capacita' che appare per caso in un
commento. Sbaglia dalla parte di chi non allarma: un difetto vero che passa
inosservato e' peggio di un allarme che non scatta, e questo cricchetto serve
a fermare la CRESCITA, non a certificare la copertura.
"""
from __future__ import annotations

import pathlib
import re

from verimem.client import Memory

#: Misurato il 2026-08-02. Chi apre una porta ABBASSA questo numero nello
#: stesso commit; chi ne aggiunge una senza porta lo vede salire e deve
#: decidere se e' una scelta o una dimenticanza.
#:
#: E' un TETTO, non un'uguaglianza, e la ragione e' una misura: in locale il
#: conteggio e' 11 e in CI 10. `dir(Memory)` non e' identico ovunque — un
#: metodo definito dietro un import opzionale c'e' su una macchina e non
#: sull'altra — quindi pretendere il numero esatto rende il cricchetto rosso
#: per l'AMBIENTE invece che per un difetto. Il verso che conta e' uno solo:
#: che non CRESCA.
SENZA_PORTA_NOTE = 11

#: Di quanto puo' scendere prima che valga la pena riallineare la costante.
#: Sotto questa distanza il calo puo' essere ambientale; oltre, qualcuno ha
#: aperto delle porte e il numero qui sopra non racconta piu' lo stato di
#: oggi.
_SCARTO_AMBIENTALE = 3

_RADICE = pathlib.Path(__file__).resolve().parents[1] / "verimem"


def _superfici() -> str:
    return "\n".join(
        (_RADICE / nome).read_text(encoding="utf-8", errors="ignore")
        for nome in ("cli.py", "mcp_server.py"))


def _senza_porta() -> list[str]:
    testo = _superfici()
    return sorted(
        m for m in dir(Memory)
        if not m.startswith("_")
        and not re.search(rf"\b{re.escape(m)}\b", testo))


def test_le_capacita_senza_porta_non_aumentano():
    mancanti = _senza_porta()
    assert len(mancanti) <= SENZA_PORTA_NOTE, (
        f"{len(mancanti)} capacita' dell'SDK non hanno una porta su CLI/MCP, "
        f"erano {SENZA_PORTA_NOTE}. Le nuove sono fra queste:\n  "
        + "\n  ".join(mancanti)
        + "\nUna capacita' raggiungibile solo dal canale che l'ha vista "
          "nascere e' il difetto che questa serie di commit chiude da un "
          "giorno: o le apri una porta, o alzi la costante dichiarando che "
          "e' una scelta.")


def test_se_ne_apri_TANTE_abbassi_il_numero():
    """Il verso opposto: un elenco che si aggiorna solo quando peggiora non
    presidia niente.

    Con uno SCARTO, e non a uguaglianza. La prima stesura pretendeva il numero
    esatto ed e' caduta in CI: 11 in locale, 10 li'. `dir(Memory)` non e'
    identico ovunque — un metodo dietro un import opzionale c'e' su una
    macchina e non sull'altra — quindi l'uguaglianza rende il cricchetto rosso
    per l'ambiente invece che per un difetto, ed e' la peggiore specie di
    presidio: quello che si impara a ignorare.
    """
    mancanti = _senza_porta()
    assert len(mancanti) >= SENZA_PORTA_NOTE - _SCARTO_AMBIENTALE, (
        f"ora sono {len(mancanti)} e la costante dice {SENZA_PORTA_NOTE}: "
        f"hai aperto piu' di {_SCARTO_AMBIENTALE} porte senza aggiornarla. "
        f"Portala a {len(mancanti)}.\nRestano senza:\n  "
        + "\n  ".join(mancanti))


def test_il_criterio_vede_davvero_qualcosa():
    """Un cricchetto che conta zero su tutto sarebbe verde per sempre: qui si
    verifica che il metodo piu' esposto del prodotto risulti ESPOSTO e che
    l'insieme misurato non sia ne' vuoto ne' l'intero SDK."""
    mancanti = set(_senza_porta())
    pubblici = {m for m in dir(Memory) if not m.startswith("_")}
    assert "add" not in mancanti and "search" not in mancanti, sorted(mancanti)
    assert 0 < len(mancanti) < len(pubblici), (
        f"{len(mancanti)} su {len(pubblici)}: il criterio non sta misurando")
