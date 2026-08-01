"""`verimem status` esplodeva sul ramo che avevo scritto io per il DB assente.

CodeQL l'ha segnalato sulla PR #4 (py/uninitialized-local-variable, error,
cli.py:222) e ha ragione. La riga di partenza inizializza DUE variabili su tre::

    _held = _judged = None
    try:
        ...
        if _db.exists():
            with sqlite3.connect(...) as _c:
                _held   = _c.execute(...)
                _judged = _c.execute(...)
                _lab    = _c.execute(...)     # <- aggiunta il 31/07, e basta
    except Exception:
        _held = _judged = _lab = None

Se il file del DB non c'e', il `with` non gira, il `try` finisce SENZA
eccezione — quindi nemmeno l'`except` ripara — e tre righe piu' giu'
``if _lab is not None`` legge una variabile che non esiste mai stata::

    UnboundLocalError: cannot access local variable '_lab' where it is not
    associated with a value

MISURATO, non dedotto, e la prima deduzione era SBAGLIATA: pensavo colpisse
«l'utente appena installato», che e' il metro con cui questa settimana si
giudica il prodotto. Provato su data dir vergine e il pannello risponde EXIT=0
con tutti zero, perche' `VerimemAgent.build()` il DB lo CREA. Il ramo resta
raggiungibile da chi il file se lo vede sparire sotto — data dir su volume
smontato, store ripulito da un altro processo, `db_path` che non e' un file.

Il difetto vero non e' la rarita' dello scenario: e' che un ramo scritto
apposta per reggere l'assenza del DB e' l'unico che non la regge. E la classe
e' quella che il repo continua a pagare — una variabile aggiunta a un blocco
senza aggiungerla al punto in cui il blocco puo' non girare.
"""
from __future__ import annotations

from typer.testing import CliRunner

import verimem.cli as cli
from verimem.cli import app

runner = CliRunner()


class _DbCheNonEsiste:
    """L'oggetto `semantic` VERO, con il solo `db_path` spostato su un file
    che non c'e'. Non un finto store: cosi' i conteggi del pannello restano
    quelli reali e l'unica cosa che cambia e' il ramo sotto esame."""

    def __init__(self, vero):
        self._vero = vero

    def __getattr__(self, nome):
        return getattr(self._vero, nome)

    @property
    def db_path(self):
        return "/un/percorso/che/non/esiste/semantic.db"


def test_senza_il_file_del_db_il_pannello_risponde_lo_stesso(monkeypatch):
    vero_build = cli.VerimemAgent.build

    def _build_senza_db(*a, **k):
        agent = vero_build(*a, **k)
        agent.semantic = _DbCheNonEsiste(agent.semantic)
        return agent

    monkeypatch.setattr(cli.VerimemAgent, "build", staticmethod(_build_senza_db))

    res = runner.invoke(app, ["status"])
    assert res.exit_code == 0, (
        f"`verimem status` e' morto quando il DB non c'era: "
        f"{res.exception!r}")
    assert "Verimem" in res.stdout
    assert "episodes" in res.stdout, (
        "il pannello non ha stampato nemmeno cio' che sapeva contare senza "
        "aprire il DB")


def test_le_tre_righe_di_verita_spariscono_INSIEME(monkeypatch):
    """Il contratto sotto la cura, non solo l'assenza del crash.

    Le tre righe — quarantined, moat-judged, epistemic — vengono tutte dallo
    stesso `SELECT`. Se il DB non si apre non se ne conosce NESSUNA, e il
    pannello deve tacerle tutte e tre invece di stamparne una a zero: uno zero
    inventato su un conteggio mai fatto e' esattamente la bugia che questo
    pannello esiste per non dire.
    """
    vero_build = cli.VerimemAgent.build

    def _build_senza_db(*a, **k):
        agent = vero_build(*a, **k)
        agent.semantic = _DbCheNonEsiste(agent.semantic)
        return agent

    monkeypatch.setattr(cli.VerimemAgent, "build", staticmethod(_build_senza_db))

    testo = runner.invoke(app, ["status"]).stdout
    for riga in ("quarantined", "moat-judged", "epistemic"):
        assert riga not in testo, (
            f"«{riga}» compare col DB chiuso: e' un numero che nessuno ha "
            "contato")
