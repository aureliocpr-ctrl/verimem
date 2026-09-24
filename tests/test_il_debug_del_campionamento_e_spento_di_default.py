"""T213 — il debug del campionamento scriveva contenuto dell'utente su disco a ogni risposta.

`MCPSamplingLLM._async_complete` (`llm.py`) appendeva a OGNI risposta 200
caratteri del prompt di sistema, 300 del primo messaggio e 600 della risposta in
`mcp_sampling_debug.log`, e sul ramo del fallimento gli stessi 300 caratteri del
messaggio: contenuto dell'utente su disco senza che l'abbia chiesto. Non è una
capacità del prodotto ma una traccia per chi indaga, quindi è SPENTA di default
e si accende con `ENGRAM_SAMPLING_DEBUG_LOG=1`; accesa, sta nella cartella dati
(T208).

Le due vie (risposta e fallimento), spente e accese. Da spente la cella controlla
anche che la sessione finta sia stata CHIAMATA: senza, «nessun file» passerebbe
pure se la chiamata non arrivasse mai al punto che scrive. Da accese è il
controllo positivo: il file nasce, nella cartella dati, col testo dentro.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

VAR = "ENGRAM_SAMPLING_DEBUG_LOG"


def _debug() -> Path:
    from verimem.config import CONFIG
    return Path(str(CONFIG.data_dir)) / "mcp_sampling_debug.log"


class _Risponde:
    def __init__(self) -> None:
        self.chiamate = 0

    async def create_message(self, **kw):  # noqa: ANN003
        self.chiamate += 1
        return SimpleNamespace(content=SimpleNamespace(text="risposta riservata"),
                               model="finto")


class _Cade:
    def __init__(self) -> None:
        self.chiamate = 0

    async def create_message(self, **kw):  # noqa: ANN003
        self.chiamate += 1
        raise RuntimeError("l'host ha rifiutato")


def _chiama(sessione) -> str:
    from verimem.llm import MCPSamplingLLM
    llm = MCPSamplingLLM(loop=None, session=sessione)
    return asyncio.run(llm._async_complete(
        "sistema riservato", [{"role": "user", "content": "il mio messaggio privato"}],
        temperature=0.0, max_tokens=16, stop_sequences=None))


@pytest.fixture
def nessuna_variabile(monkeypatch):
    for prefisso in ("ENGRAM_", "VERIMEM_", "HIPPO_"):
        monkeypatch.delenv(prefisso + "SAMPLING_DEBUG_LOG", raising=False)


def _contenuto() -> str:
    return _debug().read_text(encoding="utf-8") if _debug().exists() else ""


@pytest.mark.parametrize("valore", [None, "0", "false"])
def test_spento_una_risposta_non_lascia_niente_su_disco(nessuna_variabile, monkeypatch,
                                                        valore):
    if valore is not None:
        monkeypatch.setenv(VAR, valore)
    s = _Risponde()
    _chiama(s)
    assert s.chiamate == 1, "la sessione finta non è stata chiamata: la cella non misura"
    assert not _debug().exists(), f"traccia scritta da spenta: {_contenuto()[:300]!r}"


def test_spento_un_fallimento_non_lascia_niente_su_disco(nessuna_variabile):
    from verimem.llm import LLMError
    s = _Cade()
    with pytest.raises(LLMError):
        _chiama(s)
    assert s.chiamate == 1, "la sessione finta non è stata chiamata: la cella non misura"
    assert not _debug().exists(), f"traccia scritta da spenta: {_contenuto()[:300]!r}"


@pytest.mark.parametrize("valore", ["1", "true", "on"])
def test_acceso_la_risposta_lascia_la_traccia_nella_cartella_dati(nessuna_variabile,
                                                                   monkeypatch, valore):
    monkeypatch.setenv(VAR, valore)
    _chiama(_Risponde())
    testo = _contenuto()
    assert "risposta riservata" in testo and "il mio messaggio privato" in testo, testo


def test_acceso_anche_il_fallimento_lascia_la_traccia(nessuna_variabile, monkeypatch):
    from verimem.llm import LLMError
    monkeypatch.setenv(VAR, "1")
    with pytest.raises(LLMError):
        _chiama(_Cade())
    assert "l'host ha rifiutato" in _contenuto(), _contenuto()
