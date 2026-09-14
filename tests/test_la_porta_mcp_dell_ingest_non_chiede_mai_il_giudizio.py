"""T-MAP-11 — RED ALLA PORTA: dalla porta MCP il moat dell'ingest non gira.

Il tool `hippo_ingest_conversation` si descrive così (mcp_server.py:1846):
«store each through the full anti-confab gate». Il gate lessicale gira davvero;
il **moat** — la domanda «il dialogo dice questa cosa?» — no: il chiamante di
`mcp_server.py:8322` non passa `ground`, e la firma di `ingest_conversation`
(conversation_ingest.py:298) ha `ground: bool = False`. La porta SDK invece
passa il default del preset (`client.py:693`, balanced → True).

Il livello, dichiarato: **porta**, non funzione. Il dispatch dei tool
(`mcp_server._call_tool_impl`) contro il metodo pubblico `Memory.add(messages)`.

Il giudice qui è un ORACOLO monkeypatchato, non il cross-encoder: così il test
misura **se la porta chiede il giudizio**, e non quanto è bravo il modello (che
è la seconda metà del ticket, misurata a parte). Per questo gira anche dove il
modello CE non c'è.

Banco: 2026-09-09 23:0x — `python -m pytest tests/test_la_porta_mcp_dell_ingest_non_chiede_mai_il_giudizio.py -x -q`
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import types

import pytest

DIALOGO = ("Cliente: buongiorno, confermo il canone del capannone 12 a 5900 euro. "
           "Agente: perfetto, e la consegna resta il 3 marzo.")

DETTO_1 = "Il canone del capannone 12 e' 5900 euro."
DETTO_2 = "La consegna del capannone 12 e' il 3 marzo."
#: nessuno l'ha detto: non contraddice niente, e' solo INVENTATO.
INVENTATO = "Il capannone 12 e' stato venduto nel 2019."


class _Estrattore:
    """L'LLM di estrazione: rende i due fatti detti e uno inventato."""

    def complete(self, system, messages, *, model=None, max_tokens=1200):
        r = types.SimpleNamespace()
        r.text = "\n".join([DETTO_1, DETTO_2, INVENTATO])
        return r


def _oracolo(chiamate: list[tuple[str, str]]):
    """Il giudice perfetto: registra ogni domanda e boccia cio' che il dialogo
    non dice. Se la porta accende il moat, l'inventato finisce quarantinato."""

    def _grounds(dialogue: str, proposition: str):
        chiamate.append((dialogue[:20], proposition))
        return (proposition != INVENTATO), (0.0 if proposition == INVENTATO else 99.0)

    return _grounds


def _righe(db_path) -> dict[str, str]:
    with sqlite3.connect(str(db_path)) as con:
        return dict(con.execute("SELECT proposition, status FROM facts").fetchall())


@pytest.fixture()
def isolato(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Nessuna scrittura fuori da tmp_path: lo store di casa non si tocca."""
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("HIPPO_ENCODE_DELEGATE_ONLY", raising=False)
    return tmp_path


def test_la_porta_mcp_non_chiede_mai_il_giudizio_al_moat(
        monkeypatch: pytest.MonkeyPatch, isolato) -> None:
    """RED: dalla porta MCP il moat non viene interrogato nemmeno una volta,
    e il fatto che nessuno ha detto entra come gli altri."""
    from verimem import conversation_ingest as ci
    from verimem import mcp_server
    from verimem.semantic import SemanticMemory

    chiamate: list[tuple[str, str]] = []
    monkeypatch.setattr(ci, "_grounds", _oracolo(chiamate))

    sm = SemanticMemory(db_path=isolato / "porta_mcp.db")
    agente = types.SimpleNamespace(
        semantic=sm, wake=types.SimpleNamespace(llm=_Estrattore()))
    monkeypatch.setattr(mcp_server, "_ag", lambda: agente)
    monkeypatch.setattr(mcp_server, "_agent", agente, raising=False)

    fuori = asyncio.run(mcp_server._call_tool_impl("hippo_ingest_conversation", {
        "messages": [{"role": "user", "content": DIALOGO}],
        "conversation_id": "t-map-11",
    }))
    esito = json.loads(fuori[0].text)
    assert esito.get("error") is None, esito

    righe = _righe(sm.db_path)
    assert chiamate, (
        "la porta MCP non ha chiesto NEMMENO UNA VOLTA se il dialogo dica "
        f"queste cose: {righe}")
    assert righe.get(INVENTATO) == "quarantined", (
        f"il fatto che nessuno ha detto e' entrato come {righe.get(INVENTATO)!r} "
        f"— righe: {righe}")


def test_la_stessa_scena_dalla_porta_sdk_ferma_l_invenzione(
        monkeypatch: pytest.MonkeyPatch, isolato) -> None:
    """CONTROLLO POSITIVO che DISTINGUE: identico dialogo, identico estrattore,
    identico oracolo — ma dalla porta SDK. Se anche questo fosse rosso il
    difetto sarebbe della catena; verde qui e rosso sopra dice che il difetto
    e' della PORTA."""
    from verimem import conversation_ingest as ci
    from verimem.client import Memory

    chiamate: list[tuple[str, str]] = []
    monkeypatch.setattr(ci, "_grounds", _oracolo(chiamate))

    m = Memory(str(isolato / "porta_sdk.db"), llm=_Estrattore())
    m.add([{"role": "user", "content": DIALOGO}], conversation_id="t-map-11")

    righe = _righe(m.semantic.db_path)
    assert chiamate, "nemmeno la porta SDK ha interrogato il moat"
    assert righe.get(INVENTATO) == "quarantined", righe
    assert righe.get(DETTO_1) != "quarantined", righe
