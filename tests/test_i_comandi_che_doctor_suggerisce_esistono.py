"""`doctor` manda l'utente a eseguire comandi: devono esistere tutti.

`verimem doctor` è il comando che il README prescrive per verificare
l'installazione, e quando un check non è verde **dice cosa fare**. Sette dei
suoi messaggi nominano un comando::

    verimem airgap · verimem doctor · verimem facts list · verimem gateway serve
    verimem save · verimem status · verimem warmup

⇒ Se uno di questi sparisce o cambia nome, `doctor` continua a stamparlo e
l'utente esegue un comando che non esiste. **Non è teorico: è già successo.**
Nella 0.7.0 pubblicata `verimem save` NON esiste — il tag è del 22 luglio e quel
comando è entrato il 23 — e `doctor` lo nomina. Chi installa quella versione e
segue il suggerimento riceve `No such command save`.

Un presidio gemello esiste già per il README (ogni comando che il README insegna
esiste nella CLI, commit 930e1048). `doctor` non ne aveva uno, e a differenza
del README **cambia insieme al codice**: è la superficie con più probabilità di
scollarsi in silenzio.

📌 Il criterio qui è sintattico e va bene che lo sia: «un comando citato» è una
stringa, non un giudizio. Ciò che il test NON dice è se quel comando faccia la
cosa giusta — solo che esiste e che la CLI lo accetta.
"""
from __future__ import annotations

import pathlib
import re

import pytest

from verimem.cli import app

_CITAZIONE = re.compile(r"`verimem ([a-z][a-z\- ]*)`")


def _comandi_della_cli() -> set[str]:
    noti: set[str] = set()
    for c in app.registered_commands:
        n = c.name or (c.callback.__name__.replace("_", "-")
                       if c.callback else "")
        if n:
            noti.add(n)
    for g in getattr(app, "registered_groups", []):
        gn = g.name or ""
        noti.add(gn)
        for c in getattr(g.typer_instance, "registered_commands", []):
            n = c.name or (c.callback.__name__.replace("_", "-")
                           if c.callback else "")
            if n:
                noti.add(f"{gn} {n}")
    return noti


def _comandi_citati_da_doctor() -> list[str]:
    src = (pathlib.Path(__file__).resolve().parents[1]
           / "verimem" / "doctor.py").read_text(encoding="utf-8")
    return sorted({c.strip() for c in _CITAZIONE.findall(src)})


def _esiste(comando: str, noti: set[str]) -> bool:
    return comando in noti or comando.split()[0] in noti


def test_doctor_cita_almeno_un_comando():
    """Premessa: se il regex smettesse di trovare citazioni, il test sotto
    passerebbe a vuoto e nessuno lo saprebbe."""
    citati = _comandi_citati_da_doctor()
    assert len(citati) >= 5, (
        f"doctor cita solo {len(citati)} comandi: o il formato delle citazioni "
        f"è cambiato, o il rilevatore non le vede più. Trovati: {citati}")


@pytest.mark.parametrize("comando", _comandi_citati_da_doctor())
def test_ogni_comando_suggerito_da_doctor_esiste(comando):
    noti = _comandi_della_cli()
    assert _esiste(comando, noti), (
        f"`verimem doctor` suggerisce «verimem {comando}», che la CLI non "
        f"espone: chi segue l'indicazione riceve «No such command». "
        f"È già successo nella 0.7.0 con `save`")


def test_il_rilevatore_vede_un_comando_inventato():
    """⚠️ POPOLAZIONE OPPOSTA. Senza questo, «esistono tutti» si soddisfa anche
    con un controllo che approva qualunque stringa."""
    assert not _esiste("questo-comando-non-esiste", _comandi_della_cli())
