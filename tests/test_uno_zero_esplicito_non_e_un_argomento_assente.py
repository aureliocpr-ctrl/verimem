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

⚖️ LA CLASSE È CHIUSA SULLE SOGLIE, NON SU TUTTO, e la riga di taglio è
misurata. Il pattern `arguments.get("x", N) or N` compare **26 volte** in
`mcp_server.py`, e non sono 26 difetti:

* **SOGLIE** (`floor`, `sim_threshold`, `orphan_sim_threshold`,
  `freshness_sim_threshold`, `freshness_threshold_days`, `threshold_days`) —
  finiscono in confronti `sim >= threshold`, dove **0 significa "non
  filtrare"**: una richiesta legittima che `or` cancellava. **Curate tutte**,
  e il presidio qui sotto conta che non ne ricompaia nessuna.
* **CONTEGGI** (`limit`, `k`, `top_topics_k`, `max_results`, `max_*`) —
  lasciati com'erano. Lì `0` vale «nessun risultato», che per un conteggio è
  più probabilmente un errore del chiamante che una richiesta, e cambiarlo è
  una decisione di prodotto, non una cura di coerenza.
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


def test_nessuna_SOGLIA_usa_piu_il_rimpiazzo():
    """Lo sweep sull'AST, non un grep: `or` su una struttura annidata non si
    legge con una regex.

    Il taglio è fra soglie e conteggi, e sta scritto nel docstring di questo
    file: se un domani qualcuno reintroduce `or` su un parametro il cui nome
    contiene `threshold` o `floor`, questo diventa rosso.
    """
    import ast
    src = _MCP.read_text(encoding="utf-8", errors="replace")
    visti = set()
    for x in ast.walk(ast.parse(src)):
        if not (isinstance(x, ast.BoolOp) and isinstance(x.op, ast.Or)
                and len(x.values) == 2):
            continue
        d = x.values[1]
        if not (isinstance(d, ast.Constant)
                and isinstance(d.value, (int, float))
                and not isinstance(d.value, bool)):
            continue
        for sub in ast.walk(x.values[0]):
            if (isinstance(sub, ast.Call)
                    and getattr(sub.func, "attr", None) == "get" and sub.args):
                nome = str(getattr(sub.args[0], "value", ""))
                if "threshold" in nome or "floor" in nome:
                    visti.add((x.lineno, nome))
    assert not visti, (
        f"queste soglie rimpiazzano di nuovo uno zero esplicito: "
        f"{sorted(visti)}")
