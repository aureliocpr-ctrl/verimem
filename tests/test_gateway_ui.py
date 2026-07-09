"""Il VOLTO del prodotto — la UI web dove l'utente VEDE la fiducia.

Gap prodotto #1 (mandato Aurelio 2026-07-09): tutto il motore è API/CLI/JSON,
nessuna superficie visibile. Questa suite copre i tre pezzi che rendono
Verimem dimostrabile a occhio nudo, serviti dal gateway multi-tenant:

  1. ``GET /v1/quarantine``      — il log delle confabulazioni FERMATE
  2. ``GET /v1/graph``           — il grafo entità+edge con fonte per salto
  3. ``GET /v1/graph/dossier``   — la derivazione multi-hop citata (o astensione)
  4. ``GET /ui`` (+ asset)       — la pagina: odometro + grafo + log

Stesse proprietà di sicurezza della dashboard: pagina statica by-construction
(nessun dato interpolato server-side), dati SOLO via fetch autenticato bearer.
"""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from engram.entity_kg import Entity, EntityStore  # noqa: E402
from engram.entity_populate import entity_kg_path_for  # noqa: E402
from engram.gateway import GatewayKeys, create_app  # noqa: E402

# frase che il gate L1 storico declassa a quarantined (nessuna evidenza)
_UNSUPPORTED = "the deployment works and is verified in production"


@pytest.fixture()
def gw(tmp_path):
    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    client = TestClient(create_app(data_dir=tmp_path, keys=keys))
    api_key = keys.create(tenant_id="acme")
    hdr = {"Authorization": f"Bearer {api_key}"}
    return client, hdr, tmp_path


def _tenant_kg(tmp_path, tenant="acme") -> EntityStore:
    """L'EntityStore ESATTO che il gateway risolve per quel tenant."""
    db = tmp_path / "tenants" / tenant / "memory.db"
    return EntityStore(db_path=entity_kg_path_for(db))


# ---- 1. log confabulazioni -------------------------------------------------

def test_quarantine_requires_auth(gw):
    client, _, _ = gw
    assert client.get("/v1/quarantine").status_code == 401


def test_quarantine_lists_blocked_claims_not_admitted_facts(gw):
    client, hdr, _ = gw
    r = client.post("/v1/memories", headers=hdr, json={
        "content": _UNSUPPORTED, "topic": "deploy"})
    assert r.json()["status"] == "quarantined"
    client.post("/v1/memories", headers=hdr, json={
        "content": "the office is in Milan", "topic": "hq",
        "verified_by": ["hr-doc"]})

    items = client.get("/v1/quarantine", headers=hdr).json()["items"]
    props = [i["proposition"] for i in items]
    assert _UNSUPPORTED in props, "la confabulazione fermata SI VEDE"
    assert "the office is in Milan" not in props, "il fatto ammesso NO"
    got = next(i for i in items if i["proposition"] == _UNSUPPORTED)
    assert got["topic"] == "deploy"
    assert got["status"] == "quarantined"
    assert got["created_at"] > 0


def test_quarantine_is_tenant_isolated(gw):
    client, hdr, tmp_path = gw
    client.post("/v1/memories", headers=hdr, json={"content": _UNSUPPORTED})
    keys2 = GatewayKeys(tmp_path / "gateway_keys.db")
    other = {"Authorization": f"Bearer {keys2.create(tenant_id='rival')}"}
    assert client.get("/v1/quarantine", headers=other).json()["items"] == []


# ---- 2. grafo --------------------------------------------------------------

def test_graph_empty_when_tenant_has_no_kg(gw):
    client, hdr, _ = gw
    body = client.get("/v1/graph", headers=hdr).json()
    assert body == {"nodes": [], "edges": []}


def test_graph_returns_nodes_and_edges_with_provenance(gw):
    client, hdr, tmp_path = gw
    kg = _tenant_kg(tmp_path)
    kg.store(Entity(canonical_name="Alice", type="person", id="e_alice"))
    kg.store(Entity(canonical_name="Acme", type="org", id="e_acme"))
    kg.add_edge("e_alice", "e_acme", "works_at", weight=0.8,
                source_fact_id="f_job")
    kg.add_edge("e_acme", "e_alice", "employs", weight=0.5,
                source_fact_id=None)  # edge NON fondato

    body = client.get("/v1/graph", headers=hdr).json()
    names = {n["name"] for n in body["nodes"]}
    assert {"Alice", "Acme"} <= names
    by_pred = {e["predicate"]: e for e in body["edges"]}
    assert by_pred["works_at"]["source_fact_id"] == "f_job"
    assert by_pred["works_at"]["grounded"] is True
    assert by_pred["employs"]["grounded"] is False, (
        "l'edge senza fonte è dichiarato, non nascosto")


def test_graph_caps_are_respected(gw):
    client, hdr, tmp_path = gw
    kg = _tenant_kg(tmp_path)
    for i in range(15):
        kg.store(Entity(canonical_name=f"N{i}", type="x", id=f"e_{i}"))
    for i in range(14):
        kg.add_edge(f"e_{i}", f"e_{i+1}", "rel", source_fact_id=f"f_{i}")
    body = client.get("/v1/graph?max_nodes=5&max_edges=3",
                      headers=hdr).json()
    assert len(body["edges"]) == 3
    assert len(body["nodes"]) <= 5
    # ogni endpoint degli edge ritornati È nel set nodi (grafo renderizzabile)
    ids = {n["id"] for n in body["nodes"]}
    for e in body["edges"]:
        assert e["src"] in ids and e["dst"] in ids


# ---- 3. dossier multi-hop via HTTP ------------------------------------------

def _seed_two_hop(client, hdr, tmp_path):
    """Alice—sposa→Bob—lavora→Acme con fatti REALI nello store del tenant.

    NB: ``add()`` popola GIÀ il KG del tenant (extraction lite) con id
    auto-generati, e ``EntityStore.store`` dedupa su name_norm — quindi gli
    id delle entità vanno presi dal ritorno di ``store()``, non inventati:
    è la pipeline vera, non un mondo di stub."""
    f1 = client.post("/v1/memories", headers=hdr, json={
        "content": "Alice is married to Bob", "topic": "family",
        "verified_by": ["conv#3"]}).json()["id"]
    f2 = client.post("/v1/memories", headers=hdr, json={
        "content": "Bob works at Acme", "topic": "work",
        "verified_by": ["doc#7"]}).json()["id"]
    kg = _tenant_kg(tmp_path)
    ids = {name: kg.store(Entity(canonical_name=name, type="x"))
           for name in ("Alice", "Bob", "Acme")}
    kg.add_edge(ids["Alice"], ids["Bob"], "married_to", 0.9, f1)
    kg.add_edge(ids["Bob"], ids["Acme"], "works_at", 0.7, f2)
    return f1, f2, ids


def test_dossier_two_hop_cites_real_propositions(gw):
    client, hdr, tmp_path = gw
    f1, f2, ids = _seed_two_hop(client, hdr, tmp_path)
    d = client.get(
        f"/v1/graph/dossier?src={ids['Alice']}&target={ids['Acme']}"
        f"&max_hops=2", headers=hdr).json()
    assert d["grounded"] is True and d["abstained"] is False
    assert d["answer"] == "Acme"
    assert [s["source_fact_id"] for s in d["derivation"]] == [f1, f2]
    assert "Alice is married to Bob" in d["chain"]


def test_dossier_without_target_lists_reachable(gw):
    client, hdr, tmp_path = gw
    _, _, ids = _seed_two_hop(client, hdr, tmp_path)
    ds = client.get(f"/v1/graph/dossier?src={ids['Alice']}&max_hops=2",
                    headers=hdr).json()["dossiers"]
    assert any(d.get("answer") == "Acme" for d in ds)


def test_dossier_requires_auth(gw):
    client, _, _ = gw
    assert client.get("/v1/graph/dossier?src=e_x").status_code == 401


# ---- 4. la pagina ------------------------------------------------------------

def test_ui_page_served_without_auth_and_static(gw):
    client, _, _ = gw
    r = client.get("/ui")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    # statica by-construction: nessun dato, nessuna chiave, nessun tenant
    assert "vm_" not in r.text and "acme" not in r.text


def test_ui_assets_served(gw):
    client, _, _ = gw
    js = client.get("/ui/app.js")
    css = client.get("/ui/style.css")
    assert js.status_code == 200 and "javascript" in js.headers["content-type"]
    assert css.status_code == 200 and "css" in css.headers["content-type"]


def test_ui_page_mentions_the_three_views(gw):
    """Il volto ha le tre viste del mandato: odometro, grafo, blocchi."""
    client, _, _ = gw
    page = client.get("/ui").text.lower()
    for marker in ("odometer", "graph", "blocked"):
        assert marker in page
