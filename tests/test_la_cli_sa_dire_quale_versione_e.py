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


def _out(r: subprocess.CompletedProcess) -> str:
    """stdout+stderr, con i None normalizzati a stringa vuota.

    ⚠️ NON e' difensivita' di maniera: senza, questo file ESPLODE invece di
    dare un verdetto. Nel run 32485515818 su `5c131789`, cella
    `test (windows-latest / py3.12)`, due dei tre test qui sotto sono morti
    cosi'::

        tests\test_la_cli_sa_dire_quale_versione_e.py:47:
            testo = r.stdout + r.stderr        <- com'era, prima di questa cura
        E   TypeError: unsupported operand type(s) for +: 'NoneType' and 'str'

    ⇒ `r.stdout` era None. `capture_output=True` dovrebbe sempre restituire
    stringhe, e in locale su Windows restituisce (3 passed): **la causa non e'
    stabilita**, ed e' scritto qui invece di essere indovinata. Le due celle
    Linux e macOS non lo vedono affatto — erano gli UNICI due rossi che
    Windows aveva in piu' (11 contro 9).

    Quel che la cura ottiene, e che vale a prescindere dalla causa: il test
    smette di esplodere e comincia a DIRE. Un `TypeError` a riga 47 non
    racconta se l'aiuto sia stato mostrato o no — racconta solo che il banco
    si e' rotto mentre lo chiedeva, e chi legge il referto resta senza il
    verdetto che cercava. Se l'aiuto davvero non compare, adesso lo dice.
    """
    return (r.stdout or "") + (r.stderr or "")


def test_version_risponde_col_numero_e_esce_pulita():
    r = _cli("--version")
    assert r.returncode == 0, (
        f"`verimem --version` esce con {r.returncode}: "
        f"{_out(r)[-200:]}")
    assert verimem.__version__ in _out(r), (
        f"la versione dichiarata ({verimem.__version__}) non compare "
        f"nell'output: {_out(r)[-200:]}")


def test_CONTROLLO_senza_argomenti_mostra_ancora_l_aiuto():
    """`no_args_is_help=True` è un comportamento che l'utente si aspetta:
    aggiungere il callback non deve trasformare l'invocazione nuda in un
    silenzio o in un errore."""
    r = _cli()
    testo = _out(r)
    assert "Usage" in testo or "Commands" in testo, (
        "l'invocazione senza argomenti non mostra piu' l'aiuto.\n"
        f"rc={r.returncode} · type(stdout)={type(r.stdout).__name__} · "
        f"type(stderr)={type(r.stderr).__name__}\n"
        f"testo (coda): {testo[-300:]!r}")


def test_CONTROLLO_un_sottocomando_continua_a_funzionare():
    """Il callback gira PRIMA di ogni sottocomando: se sbagliasse, romperebbe
    tutta la CLI, non solo `--version`."""
    r = _cli("save", "--help")
    assert r.returncode == 0, (
        f"`verimem save --help` rotto: rc={r.returncode} · "
        f"type(stdout)={type(r.stdout).__name__} · {_out(r)[-300:]!r}")
    assert "save" in _out(r), (
        "`save` non compare nell'aiuto del sottocomando.\n"
        f"rc={r.returncode} · type(stdout)={type(r.stdout).__name__} · "
        f"type(stderr)={type(r.stderr).__name__}\n"
        f"testo (coda): {_out(r)[-300:]!r}")
