"""`hippo_ignorance_map` esplodeva: `'_Vista' object has no attribute
'_fact_view'`. Ed è una regressione MIA.

Trovata da ws4 il 2026-08-03, riprodotta con store vuoto e con dati:

    {"error": "ignorance_map failed: '_Vista' object has no attribute
               '_fact_view'"}

LA CAUSA È IRONICA e vale più del difetto. Il doppio `_Vista` in
`mcp_server.py` porta scritto:

    `Memory.search` usa SOLO `self.semantic` (verificato sull'AST, non a
    occhio), quindi la vista basta

La verifica era GIUSTA quando è stata scritta. Poi il 2026-08-02 `search` è
stato rifattorizzato per passare da `_fact_view` — *la cura contro le copie del
contratto di uscita* — e il doppio non è stato aggiornato. Una cura contro la
duplicazione ha rotto un doppio: la verifica non era sbagliata, era
**invecchiata**.

E il 2026-08-03 `_fact_view` è cresciuto ancora (epistemic, confidence,
confidence_tier, writer_principal), quindi il doppio si sarebbe rotto comunque
una seconda volta.

LA CURA È QUELLA GIÀ APPLICATA A `quarantine_log` (`7d7fa932`, 02/08): il
canale MCP **delega all'SDK vero** invece di tenere una vista finta. Il commento
del doppio dice che serviva a non aprire «un secondo handle sullo stesso
SQLite» — ma `Memory(path=...)` è esattamente ciò che `hippo_quarantine_log`
fa da quel giorno, e lì non ha creato problemi.

Un doppio che promette MENO del vero è la stessa classe già pagata il 02/08 con
i due `_FakeAgent` che dichiaravano solo `.semantic` mentre il vero ha anche
`.memory` (83 punti d'uso).
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import tempfile

import pytest

from verimem import Memory


@pytest.fixture()
def mcp(monkeypatch):
    from verimem import mcp_server as srv

    m = Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "s.db"))

    class _Ag:
        semantic = m.semantic
        memory = m
    monkeypatch.setattr(srv, "_ag", lambda: _Ag())

    def _call(tool: str, args: dict) -> dict:
        res = asyncio.run(srv.call_tool(tool, args))
        return json.loads(res[0].text)
    _call.store = m
    return _call


def test_la_mappa_dell_ignoranza_risponde_su_MCP(mcp):
    got = mcp("hippo_ignorance_map",
              {"queries": ["quale database usa il cluster di produzione"]})
    assert "error" not in got, (
        f"il tool esplode invece di rispondere: {got.get('error')}")
    assert got.get("queries"), got


def test_risponde_anche_con_lo_store_VUOTO(mcp):
    """Il primo contatto: uno store appena creato e una domanda qualunque."""
    got = mcp("hippo_ignorance_map", {"queries": ["qualsiasi cosa"]})
    assert "error" not in got, got.get("error")
    assert got["queries"][0]["class"] == "no_evidence", got


def test_e_con_dei_FATTI_dentro(mcp):
    """Con dei fatti dentro risponde, e ogni query torna con la sua classe.

    ⚠️ NON verifica QUALE classe: la prima stesura pretendeva `answerable` per
    «quanto costa il piano annuale» e falliva sotto pytest con `below_floor`.
    Il motivo non era la cura — fuori da pytest due `Memory` sullo stesso DB
    danno lo stesso score (0.8913 entrambi), dentro pytest il conftest
    sostituisce l'embedder e lo score diventa 0.7303. Il test misurava
    l'AMBIENTE, che è lo stesso errore già pagato il 2026-08-02 con i due
    presidi che leggevano `--help` renderizzato e un conteggio esatto.

    Quello che questo file deve provare è che la vista finta non c'è più,
    cioè che il tool RISPONDE: la taratura del floor è un altro test."""
    m = mcp.store
    for t in ["Il piano annuale costa 100 euro.",
              "La prova gratuita dura 14 giorni."]:
        m.add(t, topic="listino")
    got = mcp("hippo_ignorance_map",
              {"queries": ["quanto costa il piano annuale",
                           "quale database usa il cluster"]})
    assert "error" not in got, got.get("error")
    assert len(got["queries"]) == 2, got
    for q in got["queries"]:
        assert q.get("class"), q
        assert q.get("top_score") is not None, q


def test_il_canale_MCP_non_tiene_piu_una_vista_finta():
    """IL CRICCHETTO. Un doppio della `Memory` invecchia in silenzio: la
    verifica «usa SOLO self.semantic» era giusta quando fu scritta e si è
    rotta quando `search` è passato da `_fact_view`.

    Se un domani ne rinasce uno, questo lo dice — e nomina il perché."""
    import inspect

    from verimem import mcp_server as srv

    # Le righe di CODICE, non i commenti: la prima stesura cercava la stringa
    # nel sorgente intero e si accendeva sul commento che spiega perché la
    # vista è stata tolta. Un cricchetto che legge il testo invece della
    # struttura — la stessa lezione pagata oggi sui pattern con l'accento.
    src = "\n".join(r for r in inspect.getsource(srv).splitlines()
                    if not r.lstrip().startswith("#"))
    assert "class _Vista" not in src, (
        "è tornata una vista finta della Memory nel canale MCP: delega "
        "all'SDK vero (`Memory(path=a.semantic.db_path)`) come fa "
        "`hippo_quarantine_log` dal 2026-08-02. Un doppio che riproduce a "
        "mano l'interfaccia si rompe alla prossima cura sul contratto di "
        "uscita, e si rompe in silenzio fino alla prima chiamata.")
