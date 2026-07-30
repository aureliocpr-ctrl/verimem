"""Si puo' chiedere al CORPUS come sta messo, non solo a un fatto per volta.

`epistemic_health` (audit_one / audit_corpus / health_report) e' completo, ha i
suoi test, ed era irraggiungibile da ogni superficie: si potevano mettere le
etichette e i verdetti, e non si poteva chiedere l'aggregato.

Il motivo per cui era rimasto staccato si vede leggendolo: `_source_of` cerca
gli attributi `source` / `provenance` / `grounding_span`, e il dataclass `Fact`
non ne ha nessuno — e' scritto per una forma di fatto diversa da quella del
prodotto. Collegarlo cosi' com'e' avrebbe dato un report VUOTO (has_source
sempre falso, grounded sempre None), che e' peggio di non collegarlo: sembra
funzionare.

Percio' l'adattamento sta nel chiamante e il modulo non si tocca (ha i suoi
test): la source in chiaro non viene conservata — verificato il 30/07 sui
quarantinati — ma la sua IMPRONTA si', in `source_signature`, e il verdetto sta
in `grounding_score`. Quindi:

    has_source   <-  il fatto e' passato dal moat (impronta + verdetto)
    grounded     <-  il verdetto persistito, non un giudizio rifatto

Costo zero e nessun modello caricato: aggrega cio' che il write-path ha gia'
misurato. E' il cerchio che si chiude — il moat scrive il punteggio, la salute
lo somma.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def mem(tmp_path, monkeypatch):
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    from verimem.client import Memory
    return Memory(path=tmp_path / "semantic" / "semantic.db")


def _con_verdetto(mem, quanti: int, punteggio: float | None) -> None:
    import sqlite3
    for i in range(quanti):
        mem.add(f"Il servizio {i} ascolta sulla porta {8000 + i}.", topic="t")
    con = sqlite3.connect(str(mem.semantic.db_path))
    con.execute("UPDATE facts SET grounding_score = ?, source_signature = ? "
                "WHERE grounding_score IS NULL",
                (punteggio, "sig" if punteggio is not None else None))
    con.commit()
    con.close()


def test_un_corpus_vuoto_non_inventa_un_voto(mem):
    r = mem.epistemic_health()
    assert r["n"] == 0 and r["composite"] is None


def test_dice_quanta_parte_del_corpus_e_auditabile(mem):
    """`provenance_coverage` e' il numero che limita tutto il resto: su un
    corpus che il moat non ha mai giudicato non si puo' affermare nulla sulla
    sua salute, e il report deve dirlo invece di dare un bel voto."""
    _con_verdetto(mem, 3, None)
    r = mem.epistemic_health()
    assert r["n"] == 3
    assert r["provenance_coverage"] == 0.0
    assert r["grounded_fraction"] is None, (
        "senza un solo fatto giudicato la frazione non esiste: 0.0 direbbe "
        "«tutti bocciati», che e' un'altra cosa")


def test_un_corpus_giudicato_bene_prende_un_voto_alto(mem):
    _con_verdetto(mem, 4, 99.0)
    r = mem.epistemic_health()
    assert r["provenance_coverage"] == 1.0
    assert r["grounded_fraction"] == 1.0
    assert r["composite"] and r["composite"] > 0.9


def test_un_corpus_giudicato_male_lo_dice(mem):
    _con_verdetto(mem, 4, 10.0)
    r = mem.epistemic_health()
    assert r["grounded_fraction"] == 0.0, r
    assert r["composite"] < 0.7, r


def test_anche_il_tool_mcp_lo_espone(mem):
    """Una lettura su un canale solo e' il difetto che questi commit hanno
    passato due giorni a chiudere."""
    import asyncio
    import json

    from mcp.types import CallToolRequest, CallToolRequestParams

    from verimem import mcp_server
    _con_verdetto(mem, 2, 95.0)

    class _A:
        def __init__(s):
            s.semantic = mem.semantic
    mcp_server._ag = lambda: _A()
    h = mcp_server.server.request_handlers[CallToolRequest]
    res = asyncio.run(h(CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name="hippo_epistemic_health",
                                     arguments={}))))
    p = res.root if hasattr(res, "root") else res
    d = json.loads(next(c.text for c in p.content if hasattr(c, "text")))
    assert d.get("n") == 2 and d.get("grounded_fraction") == 1.0, d


def test_lo_schema_del_tool_e_scopribile():
    import asyncio

    from verimem import mcp_server
    tools = asyncio.run(mcp_server._list_tools_unfiltered())
    assert any(t.name == "hippo_epistemic_health" for t in tools), (
        "il tool non e' nell'elenco: nessun client puo' scoprirlo")
