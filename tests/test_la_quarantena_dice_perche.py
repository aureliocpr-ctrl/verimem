"""La quarantena dice QUALI fatti ha fermato, e ora anche PERCHE'.

Il docstring di `/v1/quarantine` lo dichiarava: «L'odometro dice QUANTI, questo
dice QUALI». Manca il pezzo che serve a fare qualcosa: sul corpus vivo ci sono
513 fatti trattenuti, e chi li guarda non sa quale schermo li abbia fermati —
quindi non puo' correggerli. Il motivo non e' persistito in nessuna colonna: il
gate lo calcola e lo mette nella ricevuta al momento della scrittura, e li'
finisce.

Si ricalcola: i detector lessicali (L1.x) sono deterministici e non chiamano
nessun modello, quindi rieseguirli su una proposizione trattenuta dice quale si
e' acceso. E' lo stesso metodo con cui il 29/07 ho contato i 122 che restano
fermi anche spostando l'evidenza in verified_by (L1.13 53, L1.15 35, L1.10 22).

Costa, quindi e' opt-in: `explain=True`. Chi vuole solo l'elenco continua ad
avere l'elenco.
"""
from __future__ import annotations

import pytest

CLAIM = "The authentication module is fully tested and works in production."


@pytest.fixture
def mem(tmp_path, monkeypatch):
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    from verimem.client import Memory
    m = Memory(path=tmp_path / "semantic" / "semantic.db")
    r = m.add(CLAIM, topic="prova")
    assert r.get("status") == "quarantined", r
    return m


def test_l_elenco_resta_quello_di_prima(mem):
    """Chi non chiede il perche' non paga il ricalcolo e vede l'elenco."""
    voci = mem.quarantine_log(limit=10)
    assert voci and voci[0]["proposition"].startswith("The authentication")
    assert "why" not in voci[0]


def test_col_perche_dice_quale_schermo_ha_fermato_il_fatto(mem):
    voci = mem.quarantine_log(limit=10, explain=True)
    assert voci, "nessuna voce in quarantena"
    why = voci[0].get("why")
    assert why, f"la voce non porta il motivo: {voci[0]}"
    testo = str(why).lower()
    assert "l1" in testo or "claim" in testo or "evidence" in testo, (
        f"il motivo non nomina lo schermo che ha fermato il fatto: {why}")


def test_il_perche_e_azionabile(mem):
    """Un motivo che non dice cosa fare e' una diagnosi senza cura: il gate
    l'advice ce l'ha, e va riportato."""
    voci = mem.quarantine_log(limit=10, explain=True)
    why = str(voci[0].get("why") or "")
    assert any(k in why for k in ("verified_by", "pytest:", "task:", "add ")), (
        f"il motivo non dice come sbloccare il fatto: {why}")


def test_un_fatto_pulito_non_finisce_qui(mem, tmp_path):
    """Guardia sul denominatore: se tutto finisse in quarantena, i test sopra
    passerebbero senza dire niente."""
    from verimem.client import Memory
    m = Memory(path=tmp_path / "semantic" / "semantic.db")
    r = m.add("Il servizio di fatturazione ascolta sulla porta 8443.",
              topic="prova",
              source="Runbook: il servizio di fatturazione ascolta sulla porta 8443.")
    assert r.get("status") != "quarantined", r


def test_quando_non_si_puo_ricostruire_lo_dice(mem, tmp_path):
    """Un fatto fermato da L4 — il confronto con la SUA fonte — non e'
    spiegabile a posteriori: la fonte non viene conservata. Provato sul corpus
    vivo: i tre quarantinati piu' recenti sono tutti cosi', e prima davano
    `why: None`.

    `None` si legge «nessun motivo». Non e' la stessa cosa di «non lo so
    piu'», ed e' la stessa distinzione che il prodotto difende fra un verdetto
    assente e uno negativo.
    """
    voci = [{"id": "x", "proposition": "Il canone e 900 euro al mese.",
             "topic": "prova", "reason": None}]
    from verimem.client import Memory
    Memory._spiega_le_quarantene(voci)
    why = str(voci[0].get("why") or "")
    assert "non e' piu' ricostruibile" in why, why
    assert "--source" in why, "non dice come rimediare la prossima volta"


def test_anche_il_tool_mcp_sa_spiegare(tmp_path, monkeypatch):
    """Una capacita' su un canale solo e' il difetto che questa serie di
    commit ha passato la giornata a chiudere: se `explain` vive solo
    sull'SDK, l'ho appena rifatto."""
    import asyncio
    import json as _json
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    from verimem.client import Memory
    m = Memory(path=tmp_path / "semantic" / "semantic.db")
    assert m.add(CLAIM, topic="prova").get("status") == "quarantined"

    from mcp.types import CallToolRequest, CallToolRequestParams

    from verimem import mcp_server

    class _A:
        def __init__(s):
            s.semantic = m.semantic
            # E ANCHE `.memory`, come l'agente vero: `VerimemAgent` espone
            # entrambi e `mcp_server` usa `a.memory` in 83 punti. Un doppio
            # che ne dichiara uno solo tiene verde un handler finche' quello
            # basta, e nasconde il giorno in cui smette di bastare — e' la
            # stessa distanza doppio/vero gia' pagata su `test_recall_chain`,
            # dove il doppio prometteva PIU' del vero invece di meno.
            s.memory = m
    # monkeypatch, non assegnazione diretta: senza ripristino `_ag` resta
    # sostituita per tutta la sessione pytest e ogni test successivo che passa
    # dal server MCP riceve questo doppio (5 rossi misurati il 2026-07-30).
    monkeypatch.setattr(mcp_server, "_ag", lambda: _A())
    h = mcp_server.server.request_handlers[CallToolRequest]

    def _call(args):
        res = asyncio.run(h(CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(name="hippo_quarantine_log",
                                         arguments=args))))
        p = res.root if hasattr(res, "root") else res
        return _json.loads(next(c.text for c in p.content if hasattr(c, "text")))

    nudo = _call({"limit": 5})
    assert nudo["quarantined"], nudo
    assert "why" not in nudo["quarantined"][0]

    spiegato = _call({"limit": 5, "explain": True})
    assert spiegato["quarantined"][0].get("why"), spiegato["quarantined"][0]


def test_lo_schema_del_tool_dichiara_explain():
    """Un parametro che il client non puo' scoprire non esiste."""
    import asyncio

    from verimem import mcp_server
    tools = asyncio.run(mcp_server._list_tools_unfiltered())
    t = next(x for x in tools if x.name == "hippo_quarantine_log")
    assert "explain" in ((t.inputSchema or {}).get("properties") or {})
