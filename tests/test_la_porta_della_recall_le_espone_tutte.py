"""`Memory.search` ha quattro modi e la riga di comando ne esponeva due.

Il docstring di `search` presenta `deep`, `as_of` e `with_history` come le
funzionalita' che distinguono il prodotto. `verimem recall` aveva `--k` e
`--as-of`, e basta.

E il docstring di `recall` racconta gia' questa storia una volta: «Il README
promette il time-travel fra le cinque righe che descrivono il prodotto, e fino
al 2026-07-31 era raggiungibile solo da MCP (`hippo_recall_as_of`) e dall'SDK
(`Memory.search(as_of=…)`): la funzione c'era completa, mancava questa porta.
Chi legge il README e usa la riga di comando concludeva che il prodotto non lo
facesse.» Quella volta e' stato aggiunto `--as-of`; `deep` e `with_history`
sono rimasti fuori dalla stessa porta.

E' la terza occorrenza della stessa classe nella stessa giornata —
`purge_history` raggiungibile solo dall'SDK, `telemetry_analyzer` completo e
irraggiungibile, e adesso questi due — quindi il file non prova solo i due
flag: prova il CRITERIO. Ogni parametro pubblico di `Memory.search` deve avere
una porta sulla riga di comando, e il test fallisce da solo il giorno in cui
qualcuno ne aggiunge un quinto senza aprirla.
"""
from __future__ import annotations

import inspect

from typer.testing import CliRunner

from verimem import cli as cli_mod
from verimem.client import Memory

#: `k` e `query` sono gia' argomenti; il resto sono i MODI della lettura.
_ESCLUSI = {"self", "query", "k"}


def _opzioni_di_recall() -> str:
    return CliRunner().invoke(cli_mod.app, ["recall", "--help"]).output


def test_ogni_modo_di_search_ha_la_sua_porta():
    """Il criterio, non l'elenco: se nasce un quinto modo, questo cade."""
    modi = [p for p in inspect.signature(Memory.search).parameters
            if p not in _ESCLUSI]
    aiuto = _opzioni_di_recall()
    mancanti = [m for m in modi
                if f"--{m.replace('_', '-')}" not in aiuto]
    assert not mancanti, (
        f"modi di lettura senza una porta sulla riga di comando: {mancanti}\n"
        f"la funzione c'e' completa nell'SDK e chi usa la CLI conclude che il "
        f"prodotto non la faccia\n{aiuto}")


def test_deep_e_with_history_ci_sono_per_nome():
    """Gli stessi due, nominati: se il criterio sopra venisse indebolito,
    questo resta a dire quali erano."""
    aiuto = _opzioni_di_recall()
    assert "--deep" in aiuto, aiuto
    assert "--with-history" in aiuto, aiuto


def test_la_recall_normale_non_cambia(tmp_path, monkeypatch):
    """Aggiungere porte non deve spostare il comportamento di default."""
    m = Memory(path=tmp_path / "m.db")
    m.add("Il piano annuale costa 100 euro.", topic="prezzi")
    monkeypatch.setattr(cli_mod, "_open_memory", lambda *a, **k: m)
    res = CliRunner().invoke(cli_mod.app, ["recall", "quanto costa il piano"])
    assert res.exit_code == 0, res.output
    assert "100" in res.output, res.output
