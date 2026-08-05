"""Dove vive ogni tier, e quante righe ha davvero.

Misurato il 2026-08-05 sul corpus di casa: ws4 ha contato le cinque
tabelle delle entità dentro `semantic.db` — tutte a zero — e ne ha
concluso «il tier entità è vuoto», ritirando una direzione di lavoro. Il
tier è altrove e non è vuoto:

    ~/.engram/semantic/semantic.db      entities 0      (guscio di migrazione)
    ~/.engram/entity_kg/entity_kg.db    entities 9078 · entity_edges 87387

E non è un caso isolato: nella radice della data dir c'è **un doppione
vuoto per quasi ogni tier**, con il nome più ovvio, accanto a quello vero
annidato — `episodes.db` 0.0 MB contro `episodes/episodes.db` 17.6 MB,
`semantic.db` 0.1 contro `semantic/semantic.db` 86.7. La stessa trappola
sta nella mia memoria da luglio con parole quasi identiche: *«il layout
nested è quello vero; quello flat è uno scheletro vuoto e leggerlo dà 0»*.

🔑 Un contenitore VUOTO e un contenitore ASSENTE danno lo stesso numero, e
solo il secondo si fa notare. Per questo l'inventario:
- risolve i percorsi con quelli del PRODOTTO (`CONFIG`), non con i propri;
- risponde `unavailable`, mai `0`, quando lo store non c'è;
- **nomina i doppioni** invece di limitarsi a evitarli.
"""
from __future__ import annotations

import json
import sqlite3

import pytest

from verimem.tier_inventory import tier_inventory


def _tier(out: dict, nome: str) -> dict:
    return next(t for t in out["tiers"] if t["tier"] == nome)


def test_ogni_tier_dice_il_suo_file_e_le_sue_righe(tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    from verimem.client import Memory

    Memory(tmp_path / "semantic" / "semantic.db").add(
        "the head office is in Milan", topic="hq")

    out = tier_inventory(data_dir=tmp_path)
    fatti = _tier(out, "facts")
    assert fatti["rows"] == 1, out
    assert fatti["store"].endswith("semantic.db")
    assert {"tier", "store", "rows"} <= set(fatti)


def test_uno_store_assente_dice_unavailable_e_non_zero(tmp_path):
    """La regola che questo ramo applica da due giorni: un conteggio che
    il prodotto non può fare si dichiara, non si finge zero. Qui vale
    doppio — zero è ESATTAMENTE la risposta sbagliata che ha fatto
    ritirare una direzione a ws4."""
    out = tier_inventory(data_dir=tmp_path / "vuota")
    for t in out["tiers"]:
        assert t["rows"] == "unavailable", t
        assert t["rows"] != 0


def test_nomina_i_doppioni_vuoti_invece_di_evitarli(tmp_path, monkeypatch):
    """Il pezzo che cura la trappola invece di schivarla: se accanto allo
    store vero c'è un file con il nome ovvio, l'inventario lo elenca con
    le sue righe, così nessuno lo conta credendo di contare il tier."""
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    from verimem.client import Memory

    Memory(tmp_path / "semantic" / "semantic.db").add(
        "the head office is in Milan", topic="hq")
    # il doppione: stesso nome, nella radice, con la tabella e zero righe
    esca = tmp_path / "semantic.db"
    with sqlite3.connect(esca) as con:
        con.execute("CREATE TABLE facts (id TEXT)")

    fatti = _tier(tier_inventory(data_dir=tmp_path), "facts")
    esche = fatti.get("decoys") or []
    assert any(str(esca) in d["path"] for d in esche), fatti
    assert all(d["rows"] == 0 for d in esche if str(esca) in d["path"])
    assert fatti["rows"] == 1, "e il conteggio vero non cambia"


def test_i_percorsi_sono_quelli_del_prodotto(tmp_path, monkeypatch):
    """Falsificabile: se l'inventario si costruisse i percorsi per conto
    suo, sarebbe solo un'altra ipotesi su dove stiano i dati — cioè la
    cosa che stiamo curando. Deve coincidere con quello che il prodotto
    apre davvero."""
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    import importlib

    from verimem import config as _cfg
    importlib.reload(_cfg)

    out = tier_inventory(data_dir=tmp_path)
    assert _tier(out, "facts")["store"] == str(_cfg.CONFIG.semantic_db)
    assert _tier(out, "episodes")["store"] == str(_cfg.CONFIG.episodes_db)
    assert _tier(out, "skills")["store"] == str(_cfg.CONFIG.skills_db)


def test_il_tier_entita_non_e_dentro_semantic_db(tmp_path):
    """Il caso che ha originato tutto: le entità NON stanno in
    semantic.db, e l'inventario deve puntare al file giusto."""
    ent = _tier(tier_inventory(data_dir=tmp_path), "entities")
    assert "entity_kg" in ent["store"], ent
    assert not ent["store"].endswith("semantic.db")


# ---- la stessa vista da ogni porta -------------------------------------------

def test_le_quattro_porte_danno_lo_stesso_inventario(tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    from typer.testing import CliRunner

    from verimem.cli import app
    from verimem.client import Memory

    m = Memory(tmp_path / "semantic" / "semantic.db")
    m.add("the head office is in Milan", topic="hq")

    sdk = m.tier_inventory()
    assert {t["tier"] for t in sdk["tiers"]} >= {
        "facts", "entities", "episodes", "skills", "documents"}

    res = CliRunner().invoke(app, ["tiers"])
    assert res.exit_code == 0, res.output
    assert "entity_kg" in res.output.replace("\n", "")


@pytest.mark.asyncio
async def test_mcp_espone_l_inventario(tmp_path, monkeypatch):
    from mcp.types import CallToolRequest, CallToolRequestParams

    from verimem import mcp_server
    from verimem.client import Memory

    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    m = Memory(tmp_path / "semantic" / "semantic.db")
    m.add("the head office is in Milan", topic="hq")

    class _FakeAgent:
        def __init__(self) -> None:
            self.semantic = m.semantic

    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent())
    handler = mcp_server.server.request_handlers[CallToolRequest]
    res = await handler(CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name="hippo_tier_inventory",
                                     arguments={})))
    payload = res.root if hasattr(res, "root") else res
    out = json.loads(next(c.text for c in payload.content
                          if hasattr(c, "text")))
    assert out.get("ok") is True, out
    assert {t["tier"] for t in out["tiers"]} >= {"facts", "entities"}


def test_http_espone_l_inventario(tmp_path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from verimem.gateway import GatewayKeys, create_app

    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    key = keys.create(tenant_id="t1", name="ci")
    client = TestClient(create_app(data_dir=tmp_path, keys=keys))
    r = client.get("/v1/tiers", headers={"Authorization": f"Bearer {key}"})

    assert r.status_code == 200, r.text
    assert {t["tier"] for t in r.json()["tiers"]} >= {"facts", "entities"}
