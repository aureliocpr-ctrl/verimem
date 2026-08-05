"""Gli eventi di governo non attraversano i tenant.

Il feed filtra per tenant (`_parse_flow_line`): un evento con un tenant
diverso viene scartato, e uno SENZA tenant passa solo in personal mode. Ma
il filtro protegge soltanto ciò che il tenant lo PORTA — e le rotte di
governo aggiunte il 2026-08-05 (restore di un quarantinato, undo di un
ritiro) non aprivano il contesto flow, quindi i loro eventi uscivano con
`surface="unknown"` e senza tenant:

    flow.write   ... surface=gateway tenant=alfa      <- le rotte storiche
    flow.restore ... surface=unknown                  <- le mie, prima della cura

Un'azione di governo senza tenant non è solo mal attribuita: nessuno può
ricondurla al cliente che l'ha chiesta, e in personal mode diventa visibile
a chi guarda il feed della macchina.

Il banco NON usa lo stream SSE (resta aperto per definizione: il primo
tentativo è andato in timeout). Verifica la proprietà dove vive: l'evento
scritto sul log porta il tenant, e la funzione di filtro lo nega agli altri.
"""
from __future__ import annotations

import json

import pytest

_UNSUPPORTED = "everything works perfectly and is fully verified"


@pytest.fixture()
def gw(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from verimem import event_jsonl_log
    from verimem.gateway import GatewayKeys, create_app

    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    monkeypatch.setenv("ENGRAM_L1_STRICT", "1")
    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    k_a = keys.create(tenant_id="alfa", name="ci")
    client = TestClient(create_app(data_dir=tmp_path, keys=keys))
    return client, {"Authorization": f"Bearer {k_a}"}, tmp_path


def _eventi(tmp_path, name):
    p = tmp_path / "events.jsonl"
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(ln)
        except ValueError:
            continue
        if rec.get("name") == name:
            out.append(rec)
    return out


def test_il_restore_via_http_porta_il_tenant(gw):
    client, hdr, tmp = gw
    r = client.post("/v1/memories", json={"content": _UNSUPPORTED,
                                          "topic": "hype"}, headers=hdr)
    assert r.status_code == 200, r.text
    body = r.json()
    if body.get("status") != "quarantined":
        pytest.skip("il gate non ha quarantinato in questo ambiente")
    assert client.post(f"/v1/memories/{body['id']}/restore",
                       headers=hdr).status_code == 200

    evts = _eventi(tmp, "flow.restore")
    assert evts, "il rilascio deve emettere"
    p = evts[-1]["payload"]
    assert p.get("tenant") == "alfa", (
        f"un'azione di governo senza tenant non e' riconducibile a chi "
        f"l'ha chiesta: {p}")
    assert p.get("surface") == "gateway", p


def test_il_filtro_nega_l_evento_agli_altri_tenant(gw):
    """La proprietà che protegge il cliente: preso l'evento vero, la
    funzione di filtro lo consegna ad alfa e lo nega a beta."""
    from verimem.gateway import _parse_flow_line

    client, hdr, tmp = gw
    r = client.post("/v1/memories", json={"content": _UNSUPPORTED,
                                          "topic": "hype"}, headers=hdr)
    if r.json().get("status") != "quarantined":
        pytest.skip("il gate non ha quarantinato in questo ambiente")
    client.post(f"/v1/memories/{r.json()['id']}/restore", headers=hdr)

    riga = json.dumps(_eventi(tmp, "flow.restore")[-1])
    assert _parse_flow_line(riga, "alfa", False) is not None
    assert _parse_flow_line(riga, "beta", False) is None, (
        "il feed di beta non deve vedere il governo di alfa")
    assert _parse_flow_line(riga, "beta", True) is None, (
        "e nemmeno in personal mode, ora che l'evento DICHIARA il suo tenant")


def test_l_undo_via_http_porta_il_tenant(gw):
    client, hdr, tmp = gw
    # topic DISTINTI di proposito: sullo stesso topic la seconda scrittura
    # supersede da sola, e il supersede esplicito cade nel ramo idempotente
    # senza handle (sbagliato due volte stanotte — l'handle, in quel caso,
    # sta nella ricevuta dell'add: `superseded_undo_ops`).
    a = client.post("/v1/memories", json={"content": "the office is in Milan",
                                          "topic": "hq/a"}, headers=hdr).json()
    b = client.post("/v1/memories", json={"content": "the warehouse is in Rome",
                                          "topic": "wh/b"}, headers=hdr).json()
    if not (a.get("stored") and b.get("stored")):
        pytest.skip("scritture non ammesse in questo ambiente")
    from verimem.semantic import SemanticMemory
    sm = SemanticMemory(db_path=tmp / "tenants" / "alfa" / "memory.db")
    res = sm.supersede(a["id"], b["id"], principal="test", reason="t")
    assert client.post(f"/v1/undo/{res['undo_op_id']}",
                       headers=hdr).status_code == 200

    evts = _eventi(tmp, "flow.undo")
    assert evts and evts[-1]["payload"].get("tenant") == "alfa", evts[-1:]
