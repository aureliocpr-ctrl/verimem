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


def _molti_fatti(mem, quanti: int) -> None:
    """Fatti che non si mangiano a vicenda: un topic per ciascuno.

    Su un topic solo il write path li tratta come «same-source evolution» e ne
    resta uno — e' il difetto che tiene rossi i due test qui sopra. Qui serve
    un corpus di dimensione NOTA, quindi lo si evita.
    """
    for i in range(quanti):
        mem.add(f"Il servizio {i} ascolta sulla porta {8000 + i}.",
                topic=f"t{i}")


def test_il_referto_dice_su_quanti_fatti_e_stato_calcolato(mem):
    """Il voto vale su cio' che il referto ha GUARDATO, e `n` da solo non
    distingue «il corpus ha n fatti» da «ne ho letti n dei molti che ci sono».

    Misurato sul corpus vivo il 2026-08-16 (11424 righe): il referto diceva
    `n = 2000` e `composite = 0.97`, e 2000 e' il valore predefinito del
    parametro `limit`, non una proprieta' del corpus — i fatti non superseduti
    erano 9534. Nessuna chiave diceva che 7534 non erano stati aperti.
    """
    _molti_fatti(mem, 5)
    r = mem.epistemic_health(limit=2)
    assert r["n"] == 2, r
    assert r["n_written"] == 5, (
        "il referto non dice quanti fatti sono stati SCRITTI: chi legge n=2 "
        "non ha modo di sapere che ce ne sono cinque")
    assert r["n"] + r["n_superseded"] + r["n_not_examined"] == r["n_written"], (
        f"la scomposizione non torna: {r}")


def test_dice_quanti_ne_ha_lasciati_fuori_il_limite(mem):
    _molti_fatti(mem, 5)
    r = mem.epistemic_health(limit=2)
    vivi = r["n_written"] - r["n_superseded"]
    assert vivi == 5, (
        "precondizione di questo banco: cinque topic distinti non si "
        f"superano tra loro. Se cade, il difetto e' nel write path: {r}")
    assert r["n_not_examined"] == 3, r
    largo = mem.epistemic_health(limit=100)
    assert largo["n"] == 5 and largo["n_not_examined"] == 0, (
        "con un limite che copre tutto il corpus non resta niente fuori, e il "
        f"referto deve dirlo con uno zero invece che tacendo: {largo}")


def test_anche_quando_non_guarda_niente_dice_quanti_ce_ne_sono(mem):
    """Il caso in cui tacere inganna di piu'."""
    _molti_fatti(mem, 3)
    r = mem.epistemic_health(limit=0)
    assert r["n"] == 0 and r["composite"] is None
    assert r["n_written"] == 3 and r["n_not_examined"] == 3, (
        "`n=0, composite=None` si legge come «corpus vuoto» mentre i fatti "
        f"ci sono: e' il ramo che deve dichiarare di piu', non di meno. {r}")


def test_anche_il_tool_mcp_lo_espone(mem, monkeypatch):
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
    # monkeypatch, non assegnazione diretta: senza ripristino `_ag` resta
    # sostituita per tutta la sessione pytest e ogni test successivo che passa
    # dal server MCP riceve questo doppio (5 rossi misurati il 2026-07-30).
    monkeypatch.setattr(mcp_server, "_ag", lambda: _A())
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
