"""Chi scrive due fatti e ne rilegge uno deve poter sapere dov'è finito l'altro.

Un fatto SOSTITUITO esce dal totale: non è come un quarantinato, che resta
contato e ha già la sua riga. Sul corpus di riferimento del 2026-08-16 i
sostituiti erano **1890, due terzi della perdita complessiva**, e nessuna
superficie di lettura li nominava.

Il difetto è stato trovato quattro volte in un giorno, su quattro superfici
diverse, ognuna onesta per conto suo e insieme ingannevoli:

    epistemic_health()   n = 2000 (il PARAMETRO, non il corpus: i vivi erano 9534)
    verimem status       semantic facts: 1   dopo DUE scritture
    verimem stats        "facts": 1          nessuna chiave sui sostituiti
    hippo_status         "facts": 1          idem, e trovata ESEGUENDO il tool

⇒ Questo banco è la **superficie unica** di quella domanda: invece di quattro
asserzioni sparse per quattro file, una sola che le percorre tutte. Se domani
nasce una quinta porta di lettura, il posto dove aggiungerla è qui.

⚠️ LIMITE DICHIARATO, ed è un debito: si verifica che la CHIAVE ci sia, non che
il numero sia giusto. Il numero non è verificabile sotto pytest — la
supersessione decide con un coseno e qui l'embedder è uno stub su SHA-256 dei
token, quindi non scatta affatto (`conftest._stub_embedding_model`). I numeri
sono verificati FUORI da pytest, e il referto è nel canale del 2026-08-17:
`semantic facts: 1` + `superseded: 1` su un database di due righe.
"""
from __future__ import annotations

import json
import re

import pytest
from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


@pytest.fixture
def store(tmp_path, monkeypatch):
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    r = runner.invoke(app, ["facts", "add", "-p", "Il contatore vale quattro.",
                            "-t", "test/s", "--validate", "off"])
    assert r.exit_code == 0, r.output
    return tmp_path


def test_lo_sdk_lo_dichiara(store):
    from verimem.client import Memory
    m = Memory()
    assert "superseded" in m.trust_stats(), sorted(m.trust_stats())
    r = m.epistemic_health(limit=10)
    for chiave in ("n_written", "n_superseded", "n_not_examined"):
        assert chiave in r, sorted(r)


def test_la_cli_lo_dichiara(store):
    testo = _ANSI.sub("", runner.invoke(app, ["status"]).output)
    assert re.search(r"superseded:\s+\d+", testo), testo
    grezzo = _ANSI.sub("", runner.invoke(app, ["stats", "--json"]).output)
    payload = json.loads(grezzo[grezzo.index("{"):grezzo.rindex("}") + 1])
    assert "superseded" in payload, sorted(payload)


def test_la_porta_mcp_lo_dichiara(store, monkeypatch):
    """Trovata ESEGUENDO i tool, non leggendo il codice: `hippo_status` e
    `hippo_stats` rispondevano `facts: 1` su due scritture senza una chiave che
    nominasse il sostituito."""
    import asyncio

    from mcp.types import CallToolRequest, CallToolRequestParams

    from verimem import mcp_server
    from verimem.client import Memory

    mem = Memory()

    # `Memory` espone `semantic` e basta: un doppio che chiedesse `episodic` o
    # `skills` alza AttributeError, il gestore risponde con un errore di testo
    # e il test muore su un JSONDecodeError che non dice niente. I due tool
    # qui chiedono solo dei CONTEGGI a quelle due superfici, e il soggetto del
    # banco sono i FATTI: stand-in a zero, senza fingere di piu'.
    class _Vuoto:
        def count(self, *a, **k):
            return 0

        def token_usage_stats(self):
            return {"total": 0.0, "mean": 0.0, "max": 0.0, "n_with_tokens": 0.0}

    class _A:
        def __init__(s):
            s.semantic = mem.semantic
            s.memory = _Vuoto()
            s.skills = _Vuoto()
    # monkeypatch e non assegnazione: senza ripristino `_ag` resta sostituita
    # per tutta la sessione e ogni test successivo che passa dal server MCP
    # riceve questo doppio.
    monkeypatch.setattr(mcp_server, "_ag", lambda: _A())
    h = mcp_server.server.request_handlers[CallToolRequest]
    for nome in ("hippo_status", "hippo_stats"):
        res = asyncio.run(h(CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(name=nome, arguments={}))))
        p = res.root if hasattr(res, "root") else res
        d = json.loads(next(c.text for c in p.content if hasattr(c, "text")))
        assert "superseded" in d, f"{nome} non lo dichiara: {sorted(d)}"


def test_il_conteggio_ha_una_sola_casa(store):
    """La stessa domanda, un solo posto che risponde.

    Le prime versioni di queste quattro superfici ripetevano la stessa SQL
    (`superseded_by IS NOT NULL`) in quattro punti, mentre
    `SemanticMemory.count_superseded()` esisteva dal ciclo #78 ed era chiamato
    solo dal proprio test. Quattro copie divergono, una no.
    """
    from pathlib import Path
    radice = Path(__file__).resolve().parents[1]
    copie = []
    for nome in ("client.py", "cli.py", "mcp_server.py"):
        testo = (radice / "verimem" / nome).read_text(encoding="utf-8")
        # ⚠️ I COMMENTI NON SONO CODICE. La prima versione contava anche le
        # righe di commento e ha segnalato come «copia» proprio il commento che
        # spiega perché la copia è stata tolta: un presidio che non distingue
        # ciò che ESEGUE da ciò che RACCONTA accusa chi ha già curato.
        copie += [f"{nome}:{i}" for i, riga in enumerate(testo.splitlines(), 1)
                  if "superseded_by IS NOT NULL" in riga
                  and not riga.lstrip().startswith("#")]
    assert not copie, (
        "la query dei sostituiti è di nuovo scritta a mano invece di passare "
        f"da `SemanticMemory.count_superseded()`: {copie}")


# ═══ L'ODOMETRO AVEVA UNA PORTA IN MENO ══════════════════════════════════════
# Misurato il 2026-08-17: `trust_stats` — «what the gate DID on this store»,
# quello che il docstring della CLI chiama *«The numbers competitors don't
# show»* — compariva in `cli.py`, `client.py`, `gateway.py` e
# `trust_ledger.py`, e in nessuno dei 247 strumenti MCP.
#
# ⇒ Un agente poteva chiedere quanti fatti ci sono (`hippo_status`) e se una
#   singola risposta è sostenuta (`hippo_trust_report`, che è un'altra cosa: usa
#   `build_trust_report`), e NON poteva chiedere quante scritture il gate abbia
#   ammesso, trattenuto o respinto. Il differenziatore era irraggiungibile dalla
#   porta degli agenti — che per questo prodotto è quella che conta.
def test_l_odometro_del_gate_ha_una_porta_mcp(store, monkeypatch):
    import asyncio

    from mcp.types import CallToolRequest, CallToolRequestParams

    from verimem import mcp_server
    from verimem.client import Memory

    mem = Memory()

    class _A:
        def __init__(s):
            s.semantic = mem.semantic

    monkeypatch.setattr(mcp_server, "_ag", lambda: _A())
    h = mcp_server.server.request_handlers[CallToolRequest]
    res = asyncio.run(h(CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name="hippo_trust_stats", arguments={}))))
    p = res.root if hasattr(res, "root") else res
    d = json.loads(next(c.text for c in p.content if hasattr(c, "text")))
    for chiave in ("ledger", "store", "moat", "superseded"):
        assert chiave in d, (
            f"l'odometro non espone `{chiave}` dalla porta MCP: {sorted(d)}")


def test_l_odometro_e_SCOPRIBILE_non_solo_chiamabile():
    """Un tool che risponde ma non compare nell'elenco è irraggiungibile:
    nessun client sa di poterlo chiamare. È la metà che si dimentica."""
    import asyncio

    from verimem import mcp_server
    tools = asyncio.run(mcp_server._list_tools_unfiltered())
    assert any(t.name == "hippo_trust_stats" for t in tools), (
        "il tool non è nell'elenco: nessun client può scoprirlo")
