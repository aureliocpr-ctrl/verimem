"""Il tetto per test c'è, ed è ACCESO — o questa cella è rossa.

PERCHÉ ESISTE, e non è pedanteria. Una chiave `timeout` in `pyproject.toml`
senza il plugin installato **pytest la ignora senza dire niente**: la rete
sparisce e la suite resta verde. È lo stesso modo in cui, fino al 2026-09-18,
un `except ImportError: pass` faceva sparire la guardia dell'isolamento — la
cura di quel difetto e questa cella sono la stessa lezione applicata due volte.

E non è un caso di scuola: il plugin era installato su una macchina di sviluppo
e **assente dal gruppo `dev`**, cioè presente dove non serviva e assente in CI,
che è l'unico posto dove un job si blocca per cinquanta minuti.

COSA NON FA: non cura il blocco e non dice perché il giudice si ferma. Rende il
blocco NOMINABILE. Ticket T108.

Registro: riga nuova, classe «un rosso che non si riproduce è una variabile che
non controlli» — il 13/09 su T38 mezza giornata su un blocco senza nome.
Decisione: nessuna, non tocca il nucleo.
"""
from __future__ import annotations

import importlib.util

import pytest

#: Il valore dichiarato in `pyproject.toml`. Sta qui come NUMERO perché la
#: cella deve cadere anche se qualcuno lo abbassa "per fare prima": 300 s è
#: misurato (44,5 s di silenzio massimo sul runner macOS ×3 = 134 s; 54,2 s
#: l'elemento più lento in locale), non scelto.
TETTO_ATTESO = 300


def test_il_plugin_del_tetto_e_INSTALLATO():
    """Senza il plugin la chiave `timeout` è una decorazione."""
    assert importlib.util.find_spec("pytest_timeout") is not None, (
        "pytest-timeout non è installato: la chiave `timeout` di pyproject.toml "
        "viene IGNORATA IN SILENZIO e un test che si blocca torna a uccidere il "
        "job intero senza dire quale sia. Sta nel gruppo `dev`; se questo cade "
        "in CI, il passo di installazione non lo sta prendendo."
    )


def test_il_tetto_e_quello_misurato(pytestconfig):
    """Il numero, letto da chi lo applica davvero (la configurazione viva)."""
    valore = pytestconfig.getini("timeout")
    assert valore, (
        "la chiave `timeout` non è nella configurazione di questa esecuzione: "
        "o manca da pyproject.toml, o pytest non l'ha vista (plugin assente)."
    )
    assert int(float(valore)) == TETTO_ATTESO, (
        f"il tetto per test è {valore} e non {TETTO_ATTESO} s. Se lo si cambia, "
        "si cambia con una MISURA accanto: il silenzio più lungo fra due test "
        "sul runner che si blocca, moltiplicato per tre."
    )


def test_il_tetto_copre_anche_il_setup(pytestconfig):
    """`timeout_func_only` spegnerebbe il tetto proprio dove vive il blocco.

    Misurato il 18/09: sul file che seguiva il punto fermo, 49,5 s dei 54,2 s
    stanno nel SETUP — il giudice che carica. Un tetto che guarda solo la
    chiamata lascia fuori il caso per cui è nato.

    ⚠️ RILIEVO DEL LEAD, accettato: la prima stesura chiamava
    `_pytest.config.get_config()` e leggeva `cfg._parser._inidict` — due API
    private che costruiscono una configurazione NUOVA. Misurava un'esecuzione
    che non era questa, cioè non misurava niente. Qui si chiede la
    configurazione VIVA, e il presidio viene in regalo: se il plugin non è
    caricato l'opzione non è registrata, `getini` alza, e la cella è rossa.
    """
    assert not pytestconfig.getini("timeout_func_only"), (
        "`timeout_func_only` è acceso: il tetto non guarderebbe setup e "
        "fixture, dove il blocco misurato vive."
    )


@pytest.mark.timeout(2)
def test_CONTROLLO_il_tetto_MORDE_davvero():
    """Il controllo che può fallire: un tetto di 2 s su un test che dura ~0 s.

    Se `pytest.mark.timeout` non fosse registrato — plugin assente — questa
    cella fallirebbe per `--strict-markers` invece di passare in silenzio.
    Il caso opposto (una cella che DORME oltre il tetto) non può stare qui:
    col metodo `thread` pytest-timeout stampa gli stack e termina l'INTERO run,
    quindi la prova di morso sta in un file eseguito da solo —
    `verimem-studio/strumenti/prova_tetto_timeout.py`, comando nel suo docstring.
    """
    assert True
