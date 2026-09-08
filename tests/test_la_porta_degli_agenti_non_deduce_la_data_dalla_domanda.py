"""La porta degli agenti serve il presente a una domanda che nomina una data.

2026-09-08, T33 riformulato. Il ticket diceva «la porta MCP ignora `as_of`»:
FALSO, misurato — `as_of` e' nello schema di `hippo_facts_recall` e funziona
(senza 3400, con 2900). Il difetto e' un altro e piu' grave dell'avviso
mancante: la porta non DEDUCE la data dalla domanda, quindi a chi chiede «cosa
risultava al 1 giugno 2024» serve il valore di OGGI, con la confidenza di una
risposta giusta.

    SDK  «cosa risultava sul canone al 1 giugno 2024»  ->  2900   (di allora)
    CLI  idem, dopo la cura 964ea12d                   ->  2900
    MCP  idem                                          ->  3400   (di oggi)

`Memory.search` ha `as_of="auto"` nella firma (client.py) e deduce dentro
`if as_of == "auto"`; l'handler MCP chiama `a.semantic.recall(...)` direttamente
e quella riga non la incontra mai. E' la stessa forma che `mcp_server.py`
documenta gia' sopra due cure precedenti — pavimento (terza generazione) e
ranking degradato («⚠️ QUARTA GENERAZIONE DELLA STESSA CURA […] per lo stesso
identico motivo»).

⚠️ NON E' IL PRESIDIO DELL'AVVISO. `test_la_porta_degli_agenti_non_dice_perche_
ha_tolto` misura se la porta DICHIARA di aver viaggiato nel tempo; questo misura
se ci VIAGGIA. Un avviso mancante e' un'assenza; una risposta sbagliata servita
come giusta e' quello che il prodotto scrive di non voler fare.

⚠️ DUE CONTROLLI POSITIVI, e il primo e' quello che rende il rosso leggibile:
la stessa porta, con `as_of` ESPLICITO, risponde 2900. Quindi sa viaggiare nel
tempo e il difetto e' solo nella deduzione — non «MCP non sa fare il passato».
Se quel controllo cadesse, il rosso qui sotto parlerebbe di un'altra cosa.

⛔ Store in tempdir. Nessuna scrittura sul prodotto.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from verimem import mcp_server  # noqa: E402
from verimem.client import Memory  # noqa: E402
from verimem.semantic import Fact  # noqa: E402

_B = 1_700_000_000.0
_GIORNO = 86400.0
#: fra B (+100 giorni) e C (+500): a questo istante il corrente e' B.
_T = _B + 300 * _GIORNO
#: la domanda nomina «1 giugno 2024», che cade dentro quella finestra.
DOMANDA_CON_DATA = "cosa risultava sul canone al 1 giugno 2024"


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """Tre canoni in catena. `Memory()` SENZA path: e' l'unico modo di aprire
    lo STESSO file che aprira' la porta MCP, che lo prende dalle variabili
    d'ambiente. Un path esplicito ne apre un secondo, e la porta sembrerebbe
    muta perche' non ha i fatti — errore misurato oggi su un altro banco."""
    for nome in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(nome, str(tmp_path))
    m = Memory()
    for fid, quando, testo in (
            ("A", _B, "Il canone e' 2400 euro."),
            ("B", _B + 100 * _GIORNO, "Il canone e' 2900 euro."),
            ("C", _B + 500 * _GIORNO, "Il canone e' 3400 euro.")):
        m.semantic.store(Fact(id=fid, proposition=testo, topic="t",
                              asserted_at=quando), embed="sync")
    m.semantic.supersede("A", "B", principal="test:suite",
                         reason="same-source evolution")
    m.semantic.supersede("B", "C", principal="test:suite",
                         reason="same-source evolution")
    return m


async def _invoke(name: str, arguments: dict) -> str:
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(method="tools/call",
                          params=CallToolRequestParams(name=name,
                                                       arguments=arguments))
    r = await handler(req)
    payload = r.root if hasattr(r, "root") else r
    return " ".join(c.text for c in payload.content if hasattr(c, "text"))


def _valore(testo: str) -> str:
    """Il valore che compare PER PRIMO, non il primo di una lista mia."""
    trovati = [(testo.find(v), v) for v in ("2400", "2900", "3400")
               if testo.find(v) >= 0]
    return min(trovati)[1] if trovati else "NESSUNO"


def _porta(query: str, **kw) -> str:
    return _valore(asyncio.run(_invoke("hippo_facts_recall",
                                       {"query": query, "k": 5, **kw})))


def test_CONTROLLO_la_porta_SA_viaggiare_se_glielo_dici(store):
    """Il controllo che rende leggibile il rosso qui sotto.

    Con `as_of` esplicito la porta risponde con il corrente di ALLORA. Quindi il
    difetto non e' «MCP non sa fare il passato»: e' solo la deduzione dalla
    domanda. Se questo cade, il rosso accanto parla di un'altra cosa.
    """
    assert _porta("quanto e' il canone") == "3400", (
        "senza data la porta non serve nemmeno il presente: il banco non regge")
    assert _porta("quanto e' il canone", as_of=_T) == "2900", (
        "con `as_of` esplicito la porta NON viaggia: allora il difetto e' piu' "
        "in basso della deduzione, e questo file misura la cosa sbagliata")


def test_CONTROLLO_l_SDK_deduce_la_data_dalla_domanda(store):
    """L'altra meta': la deduzione ESISTE nel prodotto, sull'SDK.

    Senza, un «MCP non deduce» sarebbe indistinguibile da «il prodotto non
    deduce», cioe' da una capacita' che non c'e'.
    """
    ris = store.search(DOMANDA_CON_DATA, k=5)
    assert _valore(" ".join(str(h) for h in ris)) == "2900", (
        "l'SDK non deduce la data da questa domanda: allora non c'e' nessuna "
        "capacita' che la porta MCP stia mancando, e il ticket va riscritto")


@pytest.mark.xfail(strict=True, reason=(
    "la porta degli agenti non deduce `as_of` dalla domanda e serve il valore "
    "di OGGI: l'handler chiama a.semantic.recall(...) diretto e non passa da "
    "Memory.search, dove vive il default as_of='auto'. Quando qualcuno la cura "
    "questo diventa XPASS: togli il marcatore."))
def test_la_porta_deduce_la_data_dalla_domanda_come_le_altre(store):
    assert _porta(DOMANDA_CON_DATA) == "2900", (
        "la porta ha servito il canone di OGGI a una domanda che nomina il "
        "1 giugno 2024. Non e' un avviso mancante: e' una risposta sbagliata "
        "con la confidenza di una giusta, sul canale dove il prodotto scrive "
        "«abstention over hallucination»")
