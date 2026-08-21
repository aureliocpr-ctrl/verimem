"""`verimem --version` non esisteva, e la sua assenza si vede al primo minuto.

Chi installa il pacchetto digita `pip install verimem` e poi, quasi sempre,
`verimem --version` — per sapere cosa gli è arrivato. Fino a questo commit
rispondeva:

    ┌─ Error ──────────────────────────────┐
    │ No such option: --version            │
    └──────────────────────────────────────┘
    EXIT=2

Un errore di sintassi come prima risposta del prodotto: chi lo legge pensa di
aver sbagliato pacchetto, non che l'opzione non ci sia. E il numero di versione
è la prima cosa che serve quando si apre una segnalazione.

Misurato dal venv pulito col wheel 0.7.6 installato (ws5, 21/08): il comando
esiste, i suoi 9 sottocomandi promessi dal README esistono, e `--version` no.
"""
from __future__ import annotations

import subprocess
import sys

import verimem


def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "verimem.cli", *args],
                          capture_output=True, text=True, timeout=180)


def test_version_risponde_col_numero_e_esce_pulita():
    r = _cli("--version")
    assert r.returncode == 0, (
        f"`verimem --version` esce con {r.returncode}: "
        f"{(r.stdout + r.stderr)[-200:]}")
    assert verimem.__version__ in (r.stdout + r.stderr), (
        f"la versione dichiarata ({verimem.__version__}) non compare "
        f"nell'output: {(r.stdout + r.stderr)[-200:]}")


def test_CONTROLLO_senza_argomenti_mostra_ancora_l_aiuto():
    """`no_args_is_help=True` è un comportamento che l'utente si aspetta:
    aggiungere il callback non deve trasformare l'invocazione nuda in un
    silenzio o in un errore."""
    r = _cli()
    testo = r.stdout + r.stderr
    assert "Usage" in testo or "Commands" in testo, (
        f"l'invocazione senza argomenti non mostra piu' l'aiuto: {testo[-200:]}")


def test_CONTROLLO_un_sottocomando_continua_a_funzionare():
    """Il callback gira PRIMA di ogni sottocomando: se sbagliasse, romperebbe
    tutta la CLI, non solo `--version`."""
    r = _cli("save", "--help")
    assert r.returncode == 0, f"`verimem save --help` rotto: {(r.stdout+r.stderr)[-200:]}"
    assert "save" in (r.stdout + r.stderr)
