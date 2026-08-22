"""`arguments.get("floor", 0.8) or 0.8` — con `floor=0` restituiva 0.8.

**`or` non è un default: è un rimpiazzo.** Distingue il vero dal falso, non
l'assente dal presente — e `0`, `0.0`, `""` sono valori legittimi che
attraversano quella riga e ne escono cambiati.

Misurato alla porta MCP, due alberi, stesso argomento::

    senza la cura   floor=0 -> il tool risponde floor=0.8, deciding_floor=0.8
    con la cura     floor=0 -> floor=0.0, deciding_floor=0.0

⇒ Un agente che chiede *«non filtrare»* (`floor=0`) otteneva **il filtro più
aggressivo**: l'opposto di quello che ha chiesto, in silenzio, con la risposta
che sembra normale.

📌 COME L'HO TROVATO, e vale più del difetto: cercavo default CABLATI
nell'handler MCP che duplicassero quelli dell'SDK — un debito, non un bug. Il
banco disse «4 casi, tutti coincidono»: **confrontavo i default, non il
comportamento sui valori falsy.** Il difetto stava dentro un caso che avevo
appena classificato come innocuo.

⚠️ IL RESTO DELLA CLASSE È MISURATO E NON CURATO. Il pattern
`arguments.get("x", N) or N` compare **26 volte** in `mcp_server.py`. Non sono
26 difetti: per `limit` o `k` uno zero è poco sensato, per una SOGLIA significa
«non filtrare» ed è legittimo. I candidati veri sono gli altri parametri di
soglia (`sim_threshold`, `orphan_sim_threshold`, `freshness_*`), e curarli
richiede sapere per ciascuno se lo zero ha un senso — cosa che non ho
misurato. Chi ha quel perimetro lo trova qui.
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import pytest

_MCP = Path(__file__).resolve().parent.parent / "verimem" / "mcp_server.py"


def _chiama(nome: str, argomenti: dict) -> dict:
    import verimem.mcp_server as m
    r = asyncio.run(m.call_tool(nome, argomenti))
    assert r, "il tool non ha risposto"
    return json.loads(r[0].text)


def test_un_floor_zero_esplicito_arriva_a_zero():
    """IL CUORE: lo zero è una richiesta, non un'assenza."""
    d = _chiama("hippo_ignorance_map",
                {"queries": ["che fatturato ha la sede di Milano"], "floor": 0})
    if "error" in d:
        pytest.skip(f"il tool non è eseguibile qui: {d['error'][:80]}")
    assert d.get("floor") == 0, (
        f"floor=0 esplicito è diventato {d.get('floor')!r}: `or` ha "
        f"rimpiazzato la richiesta dell'agente con il default")


def test_senza_floor_il_default_resta_quello_di_prima():
    """⚖️ L'ALTRA POPOLAZIONE: togliere il rimpiazzo non deve togliere il
    DEFAULT. Chi non passa nulla deve continuare a ricevere 0.8."""
    d = _chiama("hippo_ignorance_map",
                {"queries": ["che fatturato ha la sede di Milano"]})
    if "error" in d:
        pytest.skip(f"il tool non è eseguibile qui: {d['error'][:80]}")
    assert d.get("floor") == pytest.approx(0.8), (
        f"senza `floor` il default non è più 0.8 ma {d.get('floor')!r}")


def test_i_parametri_curati_non_usano_piu_il_rimpiazzo():
    """Il presidio sul sorgente: se qualcuno riscrive `or 0.8`, il difetto
    torna senza che nessuna asserzione sul comportamento se ne accorga —
    perché il comportamento lo prova solo per `floor`, e la classe ha 26
    occorrenze."""
    src = _MCP.read_text(encoding="utf-8", errors="replace")
    i = src.index("_sdk.ignorance(")
    blocco = src[i:i + 900]
    colpevoli = re.findall(r'arguments\.get\(\s*"(floor|k)"[^)]*\)\s*or\s*[\d.]+',
                           blocco)
    assert not colpevoli, (
        f"il rimpiazzo è tornato su {colpevoli}: uno zero esplicito verrebbe "
        f"di nuovo sostituito dal default")
