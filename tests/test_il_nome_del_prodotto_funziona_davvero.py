"""Il README insegna `VERIMEM_*`, e un grep sui moduli dice che nessuno lo legge.

Sono vere entrambe, e per questo il difetto si ripete: il 18/08 il README è
stato corretto da `VERIMEM_SUPERSEDE_SAME_SOURCE` a `ENGRAM_...` proprio perché
il primo «non compare in nessun modulo mentre `anti_confab_gate.py` legge il
secondo». Il grep diceva il vero e la conclusione era falsa — e la correzione ha
reso rosso `test_il_readme_insegna_il_nome_del_prodotto`, che pretende (a
ragione) il nome del prodotto negli esempi.

Chi ha ragione lo dice la PORTA, non il sorgente. Misurato il 19/08::

    VERIMEM_SUPERSEDE_SAME_SOURCE=0  ->  _supersede_same_source_on() False
    ENGRAM_SUPERSEDE_SAME_SOURCE=0   ->  _supersede_same_source_on() False
    nessuna delle due                ->  True

Il nome del prodotto FUNZIONA: `_compat.init_env_aliases()` specchia
`VERIMEM_*` → `ENGRAM_*` prima che i lettori canonici guardino l'ambiente. Un
grep sui moduli non può vederlo, perché la stringa che cerca non c'è mai — e
questa è la stessa classe di «il grep sul sorgente mi ha dato il contrario su
tre campi su tre».

⇒ Questo file esiste per rompere il ciclo: presidia il COMPORTAMENTO, così la
prossima volta che qualcuno fa quel grep trova un test verde che dice «funziona
lo stesso, guarda lo specchio» invece di riaprire il giro.
"""
from __future__ import annotations

import pytest


def _acceso(monkeypatch, **env) -> bool:
    """Il valore che il gate legge davvero, con l'ambiente dato."""
    import importlib

    from verimem import _compat
    for k in ("VERIMEM_SUPERSEDE_SAME_SOURCE", "ENGRAM_SUPERSEDE_SAME_SOURCE",
              "VERIMEM_MULTI_WRITER", "ENGRAM_MULTI_WRITER"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    _compat.init_env_aliases()
    g = importlib.import_module("verimem.anti_confab_gate")
    return g._supersede_same_source_on()


def test_il_nome_del_PRODOTTO_spegne_la_supersessione(monkeypatch):
    """Il caso: un operatore segue il README e usa `VERIMEM_*`."""
    assert _acceso(monkeypatch, VERIMEM_SUPERSEDE_SAME_SOURCE="0") is False, (
        "il nome che il README insegna non ha effetto: o lo specchio degli "
        "alias non gira, o il README sta insegnando una variabile morta")


def test_anche_il_nome_STORICO_continua_a_funzionare(monkeypatch):
    """⚠️ POPOLAZIONE OPPOSTA: le installazioni esistenti usano `ENGRAM_*` e non
    devono rompersi perché il README ha cambiato nome."""
    assert _acceso(monkeypatch, ENGRAM_SUPERSEDE_SAME_SOURCE="0") is False


def test_senza_nessuna_delle_due_il_default_resta_acceso(monkeypatch):
    """⚠️⚠️ IL VINCOLO PIÙ STRETTO: i due test sopra si soddisfano anche con una
    funzione che risponde sempre False. Il default è una scelta di prodotto
    dichiarata nel codice («deliberately left ON pending an explicit product
    decision») e questo test la difende."""
    assert _acceso(monkeypatch) is True
