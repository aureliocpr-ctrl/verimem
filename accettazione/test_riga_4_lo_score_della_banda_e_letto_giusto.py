"""RIGA 4 — lo score della banda è letto giusto.

LA PROMESSA. Lista chiusa della 0.7.7, riga 4 (21/09 21:5x). Il README, sulla banda a
due soglie: la banda «escalates to one llm adjudication OFFLINE-FIRST … a local ollama
judge … is preferred, then a `claude` CLI on PATH (subscription, no key) … The verdict
admits (judge-of-record `local-band`/`claude-band` on the receipt) or blocks … an
unreadable verdict never admits».

COSA VEDE L'UTENTE. Il giudice della banda risponde «Score: 69.6»: il prodotto decide su
69.6, non su 69 (a 70 di taglio, 69.6 e 69 cadono dallo stesso lato, ma un 70.4 letto 70
no: T189). E se la risposta non ha un numero leggibile, la scrittura non entra.

LA PROVA, e il suo LIVELLO dichiarato. Un `claude` finto sul PATH (un vero processo, come
il CLI dell'utente) risponde; ollama e' reso irraggiungibile (`OLLAMA_HOST` su una porta
chiusa) perche' su una macchina che lo ha la banda passerebbe di la'. Si chiama
`band_escalation.escalate_band`, la funzione che il cancello chiama quando il punteggio
locale cade nella banda: provocare una scrittura che il giudice locale metta nella banda
non e' deterministico, e una prova che dipende da dove cade un punteggio misurerebbe il
giudice, non la lettura.

CHI LA CHIUDE: T189 (chiuso per misura, impatto zero). Oggi: VERDE (predizione).
"""
from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

CODICE = r'''
import json
from verimem import band_escalation as b
b._resolve_cli.cache_clear()
b._local_ollama_available.cache_clear()
print("ESITO " + json.dumps(b.escalate_band(
    "The office opens at 9 and closes at 18.", "The office closes at 18.")))
'''


def _claude_finto(cartella: Path, risposta: str) -> None:
    cartella.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        (cartella / "claude.cmd").write_text(f"@echo off\r\necho {risposta}\r\n",
                                             encoding="ascii")
    else:
        f = cartella / "claude"
        f.write_text(f"#!/bin/sh\necho '{risposta}'\n", encoding="ascii")
        f.chmod(f.stat().st_mode | stat.S_IEXEC)


def _banda(utente, risposta: str):
    cartella = utente.radice / f"bin-{abs(hash(risposta))}"
    _claude_finto(cartella, risposta)
    uscita = utente.python(
        CODICE, PATH=str(cartella) + os.pathsep + utente.env.get("PATH", ""),
        OLLAMA_HOST="http://127.0.0.1:9")
    righe = [r for r in uscita.stdout.splitlines() if r.startswith("ESITO ")]
    assert righe, f"la banda non ha risposto (exit {uscita.returncode}): {uscita.stderr[-800:]}"
    return json.loads(righe[-1][len("ESITO "):])


def test_riga_4_il_punteggio_della_banda_arriva_coi_decimali(utente):
    esito = _banda(utente, "Score: 69.6")
    assert esito is not None, "il claude sul PATH ha risposto e la banda non ha deciso"
    punteggio, giudice = esito
    assert giudice == "claude-band", esito
    assert abs(punteggio - 69.6) < 1e-9, (
        f"il giudice della banda ha detto 69.6 e il prodotto ha letto {punteggio}")


def test_riga_4_un_verdetto_illeggibile_non_ammette(utente):
    assert _banda(utente, "I cannot tell from this source.") is None, (
        "un verdetto senza numero e' stato letto come un punteggio: il README promette "
        "che un verdetto illeggibile non ammette mai")
