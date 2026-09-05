"""`as_of` sulle due porte ordinarie: il presidio dei tre rossi del pezzo 3.

I tre banchi in `docs/stato-reale/banchi/` non girano in CI: senza questo file
la cura entrerebbe senza presidio e la prossima istanza che tocca quelle righe
la romperebbe senza saperlo (condizione posta dal CTO in revisione, 05/09).

LE TRE CELLE, ognuna ROSSA su `origin/main` prima della cura:

  ① `as_of` ACCETTATO E IGNORATO — la porta prendeva il parametro e serviva il
     presente. Chi chiedeva il passato non aveva modo di accorgersene.
  ② LA PESCA AFFAMATA — le porte pescavano `k` e filtravano dopo, mentre
     `hippo_recall_as_of` pesca `max(k*6, k)` «so the as-of filter doesn't
     starve top-k». Se i primi `k` sono nati DOPO l'istante chiesto, il filtro
     li scarta tutti e la porta risponde vuota pur avendo la risposta in
     archivio.
  ③ IL TAGLIO PRIMA DELLO SCOPE (H3, trovata dalla QA leggendo) — `_tenuti[:k]`
     precedeva il filtro di scope, mentre la porta gemella faceva il contrario.
     `agent_id` senza `user_id` non e' un prefisso leading: la pesca allarga e
     il post-filtro stringe, quindi tagliare prima buttava i candidati buoni.

⚠️ NIENTE GIUDICE: `as_of` non ne usa, e le scritture passano da `sm.store()`
diretto — una scrittura dal gate costa ~3,5 s e questo file deve stare sotto i
30 s. Le date sono su `asserted_at` con un epoch FISSO, mai `time.time()`:
l'orologio del muro in un test e' una prova che cambia da sola.

⚠️ OGNI CELLA VERIFICA LA PROPRIA PRECONDIZIONE. Sotto pytest l'embedder e'
uno STUB deterministico: se l'ordinamento non mette i fatti nuovi davanti, il
caso ② non e' riprodotto e il test lo DICE invece di passare per caso — un
verde su una condizione non esercitata e' peggio di un rosso.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from verimem import mcp_server
from verimem.scope import scoped_topic
from verimem.semantic import Fact, SemanticMemory

_BASE = 1_700_000_000.0     # epoch fisso: nessun orologio del muro
_DAY = 86400.0
#: l'istante che chiediamo: dopo i fatti "di allora", prima di quelli "di oggi"
_ALLORA = _BASE + 10 * _DAY
_OGGI = _BASE + 20 * _DAY
_QUANDO = _BASE + 15 * _DAY


def _chiama(nome: str, argomenti: dict) -> dict:
    from mcp.types import CallToolRequest, CallToolRequestParams

    async def _go() -> dict:
        res = await mcp_server.server.request_handlers[CallToolRequest](
            CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(name=nome, arguments=argomenti)))
        p = res.root if hasattr(res, "root") else res
        testo = next(c.text for c in p.content if hasattr(c, "text"))
        return json.loads(testo)

    return asyncio.run(_go())


def _quanti(risposta: dict) -> int:
    """Quanti fatti sono stati RESTITUITI — dalla struttura, mai dal testo.

    Un record porta `superseded_by`, cioe' l'id del suo sostituto: cercare un
    id come sottostringa lo trova anche quando quel fatto non e' fra i
    risultati (rosso falso pagato il 03/09).
    """
    for chiave in ("items", "results", "facts", "hits"):
        valore = risposta.get(chiave)
        if isinstance(valore, list):
            return len(valore)
    raise AssertionError(f"nessuna lista di risultati in {sorted(risposta)}")


@pytest.fixture()
def store(tmp_path, monkeypatch) -> SemanticMemory:
    sm = SemanticMemory(db_path=tmp_path / "s.db")

    class _FakeAgent:
        def __init__(self) -> None:
            self.semantic = sm

    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent())
    return sm


def _scrivi(sm, testo: str, *, id: str, quando: float, topic: str = "t") -> None:
    sm.store(Fact(id=id, proposition=testo, topic=topic, asserted_at=quando),
             embed="sync")


# ── ① as_of accettato e IGNORATO ──────────────────────────────────────────
@pytest.mark.parametrize(("tool", "chiave_k"),
                         [("hippo_facts_recall", "k"),
                          ("hippo_facts_search", "limit")])
def test_as_of_e_applicato_e_dichiarato(store, tool: str, chiave_k: str) -> None:
    _scrivi(store, "Il conto della societa e' presso la Banca Beta.",
            id="f-oggi", quando=_OGGI)

    q = "banca del conto della societa"
    adesso = _chiama(tool, {"query": q, chiave_k: 5})
    assert _quanti(adesso) == 1, (
        "CONTROLLO POSITIVO SPENTO: senza `as_of` la porta non serve nemmeno "
        "il fatto che c'e', quindi il resto della cella non misura nulla")

    passato = _chiama(tool, {"query": q, chiave_k: 5, "as_of": _QUANDO})
    assert _quanti(passato) == 0, (
        "as_of ACCETTATO E IGNORATO: la porta serve un fatto asserito DOPO "
        "l'istante chiesto (era il difetto su main)")
    assert passato.get("as_of") == _QUANDO, (
        "un filtro applicato si DICHIARA: senza l'eco la cura e' invisibile "
        "a chi chiama, che e' il difetto di partenza in un'altra forma")
    assert passato.get("as_of_scartati") == 1, (
        "e dice QUANTI ne ha tolti perche' non erano ancora nati")


# ── ② la pesca affamata ───────────────────────────────────────────────────
@pytest.mark.parametrize(("tool", "chiave_k"),
                         [("hippo_facts_recall", "k"),
                          ("hippo_facts_search", "limit")])
def test_la_pesca_non_affama_il_filtro(store, tool: str, chiave_k: str) -> None:
    """Con k=1 e i primi k nati dopo l'istante, solo l'oversample salva."""
    _scrivi(store, "Il conto della societa e' presso la Banca Alfa.",
            id="f-allora", quando=_ALLORA)
    for i in range(6):
        _scrivi(store, f"Il conto della societa e' presso la Banca Beta {i}.",
                id=f"f-oggi-{i}", quando=_OGGI)
    store.supersede("f-allora", "f-oggi-0", principal="test:suite",
                    reason="same-source evolution")

    q = "banca del conto della societa"
    #: PRECONDIZIONE: con k=1 il primo posto deve andare a un fatto di OGGI,
    #: altrimenti il filtro non ha nulla da scartare e la cella e' cieca.
    primo = _chiama(tool, {"query": q, chiave_k: 1})
    assert _quanti(primo) == 1, "il corpus non risponde: cella cieca"

    passato = _chiama(tool, {"query": q, chiave_k: 1, "as_of": _QUANDO})
    assert _quanti(passato) == 1, (
        "LA PESCA AFFAMATA: con k=1 la porta pescava 1 candidato, il filtro "
        "lo scartava perche' nato dopo, e rispondeva VUOTO pur avendo in "
        "archivio il fatto che a quell'istante era corrente. Serve la pesca "
        "allargata come in hippo_recall_as_of (k*6)")


# ── ③ H3: il taglio prima dello scope ─────────────────────────────────────
def test_as_of_con_agent_id_non_perde_i_risultati(store) -> None:
    """`agent_id` senza `user_id` non e' leading: oversample + post-filtro."""
    dentro = scoped_topic("t", agent_id="atlas")
    for i in range(4):
        _scrivi(store, f"La politica di rimborso prevede il caso {i}.",
                id=f"f-fuori-{i}", quando=_ALLORA)
    for i in range(2):
        _scrivi(store, f"Il rimborso di Atlas segue la regola {i}.",
                id=f"f-dentro-{i}", quando=_ALLORA, topic=dentro)

    q = "politica di rimborso"
    senza = _quanti(_chiama("hippo_facts_recall",
                            {"query": q, "k": 2, "agent_id": "atlas"}))
    assert senza > 0, (
        "CONTROLLO POSITIVO SPENTO: lo scope da solo non rende nulla, "
        "quindi il confronto con `as_of` non direbbe niente")

    con = _quanti(_chiama("hippo_facts_recall",
                          {"query": q, "k": 2, "agent_id": "atlas",
                           "as_of": _OGGI}))
    assert con == senza, (
        "H3: il taglio a k avveniva PRIMA del filtro di scope, quindi "
        "`as_of` + `agent_id` perdeva risultati su cui il tempo non aveva "
        "nulla da dire (la QA ha misurato 2 -> 0 su main)")
