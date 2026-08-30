"""La porta di ricerca deve DIRE quando ha ripiegato da AND a OR.

`hippo_facts_search` prova prima l'AND su tutti i token; se non aggancia
nulla ripiega sull'OR, che su una domanda di piu' parole puo' agganciare
una fetta larghissima del corpus. I risultati escono poi in ordine di data
(`ORDER BY created_at DESC`), non di pertinenza.

Oggi il ripiego avviene in silenzio: chi legge riceve i fatti piu' recenti
fra i candidati e non ha modo di sapere ne' che l'AND ha fatto cilecca ne'
che l'ordine non e' la rilevanza. Misurato il 2026-08-30 sul corpus reale:
una domanda di otto parole dava 0 hit in AND e 2575 in OR (16,5% del
corpus), con i fatti cercati in posizione 147.

Questi test pretendono che l'avviso ci sia, e che non compaia quando il
ripiego non e' avvenuto.
"""
from __future__ import annotations

import json

import pytest

from tests.test_mcp_facts_skills_search import _FakeAgent, _invoke_tool
from verimem import mcp_server


@pytest.fixture
def fake_agent(monkeypatch: pytest.MonkeyPatch) -> _FakeAgent:
    """La fixture e' ridichiarata, non importata.

    Importare quella del modulo vicino e riceverla come parametro fa
    scattare F811 (ridefinizione), e la CI lint gira prima dei test.
    """
    a = _FakeAgent()
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a


@pytest.mark.asyncio
async def test_dice_che_ha_ripiegato(fake_agent: _FakeAgent) -> None:
    """AND a vuoto + OR che aggancia => la risposta lo dichiara."""
    blocks = await _invoke_tool(
        "hippo_facts_search", {"query": "database password zebra"},
    )
    payload = json.loads(blocks[0])
    assert payload["items"], "il ripiego OR deve agganciare almeno un fatto"
    ricerca = payload.get("ricerca")
    assert ricerca is not None, "manca il blocco 'ricerca' nella risposta"
    assert ricerca.get("ramo") == "or_fallback"


@pytest.mark.asyncio
async def test_senza_ripiego_dichiara_il_ramo_and(fake_agent: _FakeAgent) -> None:
    """Se l'AND aggancia, il ramo dichiarato e' quello e non l'altro."""
    blocks = await _invoke_tool(
        "hippo_facts_search", {"query": "database password"},
    )
    payload = json.loads(blocks[0])
    assert payload["items"], "l'AND deve agganciare f3"
    assert payload.get("ricerca", {}).get("ramo") == "and"


@pytest.mark.asyncio
async def test_dichiara_che_ordina_per_data(fake_agent: _FakeAgent) -> None:
    """L'ordine non e' la rilevanza, e la porta deve dirlo."""
    blocks = await _invoke_tool(
        "hippo_facts_search", {"query": "database password zebra"},
    )
    payload = json.loads(blocks[0])
    assert payload.get("ricerca", {}).get("ordinati_per") == "created_at DESC"


@pytest.mark.asyncio
async def test_anche_quando_il_ripiego_non_trova_nulla_lo_dice(
    fake_agent: _FakeAgent,
) -> None:
    """AND a vuoto e OR pure: il ramo dichiarato resta quello del ripiego.

    Scoperto verificando alla porta vera, non dai fake: con entrambi i rami a
    zero la risposta dice `or_fallback` con `items` vuoto. E' fedele — il
    ripiego e' davvero avvenuto — ma il caso non era coperto, e un
    comportamento non coperto e' un comportamento accidentale.
    """
    blocks = await _invoke_tool(
        "hippo_facts_search", {"query": "pinguino monopattino"},
    )
    payload = json.loads(blocks[0])
    assert payload["items"] == []
    assert payload.get("ricerca", {}).get("ramo") == "or_fallback"
