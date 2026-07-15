"""Il grafo INTERO, servibile: /v1/graph/full in formato compatto.

Mandato Aurelio 2026-07-15: "sto grafo reale con tutte le entità ed archi lo
facciamo? io vedo che tutti lo hanno ed è super performante". Sullo store
reale sono 7753 nodi e 78 725 archi: in formato verbose (oggetti con id
stringa ripetuti su ogni arco) sarebbero 5.71 MB, in formato compatto —
nodi in un array, archi per INDICE — sono 1.50 MB. Il DB li legge in 0.19s.

Contratto:
  {"n": [[id, name, type], ...],          # posizione = indice del nodo
   "e": [[srcIdx, dstIdx, grounded], ...],
   "truncated": false, "total_entities": N, "total_edges": M}

Nessun campione, nessun fossile: questo è TUTTO il grafo. Il cap esiste solo
come guardia di sanità (uno store mostruoso non deve far esplodere il
browser) e quando morde lo DICHIARA.
"""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from engram.client import Memory  # noqa: E402
from engram.entity_kg import Entity, EntityStore  # noqa: E402
from engram.entity_populate import entity_kg_path_for  # noqa: E402
from engram.gateway import GatewayKeys, create_app  # noqa: E402


@pytest.fixture()
def gw(tmp_path):
    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    client = TestClient(create_app(data_dir=tmp_path, keys=keys))
    api_key = keys.create(tenant_id="acme")
    return client, {"Authorization": f"Bearer {api_key}"}, tmp_path


def _kg(tmp_path, tenant="acme"):
    db = tmp_path / "tenants" / tenant / "memory.db"
    return EntityStore(db_path=entity_kg_path_for(db))


def _seed(kg, n_connected=6):
    ids = []
    for i in range(n_connected):
        ids.append(kg.store(Entity(canonical_name=f"node{i}", type="concept")))
    for i in range(len(ids) - 1):
        kg.add_edge(ids[i], ids[i + 1], "co_occurs", source_fact_id=f"f{i}")
    kg.store(Entity(canonical_name="hermit", type="concept"))   # isolata
    return ids


def test_full_graph_requires_auth(gw):
    client, _, _ = gw
    assert client.get("/v1/graph/full").status_code == 401


def test_returns_every_node_and_edge(gw):
    client, hdr, tmp = gw
    client.post("/v1/memories", headers=hdr,
                json={"content": "seed", "topic": "t"})   # crea lo store
    kg = _kg(tmp)
    _seed(kg)
    d = client.get("/v1/graph/full", headers=hdr).json()
    names = {row[1] for row in d["n"]}
    assert {"node0", "node5", "hermit"} <= names, "TUTTE le entità, isolate incluse"
    assert len(d["e"]) == 5
    assert d["truncated"] is False
    assert d["total_entities"] == len(d["n"])
    assert d["total_edges"] == len(d["e"])


def test_edges_reference_nodes_by_index(gw):
    """Il formato compatto: un arco punta a POSIZIONI nell'array nodi —
    è quello che porta 5.71 MB a 1.50 MB sullo store reale."""
    client, hdr, tmp = gw
    client.post("/v1/memories", headers=hdr, json={"content": "seed", "topic": "t"})
    kg = _kg(tmp)
    ids = _seed(kg)
    d = client.get("/v1/graph/full", headers=hdr).json()
    by_id = {row[0]: i for i, row in enumerate(d["n"])}
    pairs = {(e[0], e[1]) for e in d["e"]}
    assert (by_id[ids[0]], by_id[ids[1]]) in pairs
    for e in d["e"]:
        assert 0 <= e[0] < len(d["n"]) and 0 <= e[1] < len(d["n"])
        assert e[2] in (0, 1)          # grounded flag


def test_cap_is_declared_when_it_bites(gw):
    """Se il cap di sanità morde, il payload lo DICHIARA (mai un silenzio)."""
    client, hdr, tmp = gw
    client.post("/v1/memories", headers=hdr, json={"content": "seed", "topic": "t"})
    kg = _kg(tmp)
    _seed(kg, n_connected=6)
    d = client.get("/v1/graph/full?max_nodes=3", headers=hdr).json()
    assert d["truncated"] is True
    assert len(d["n"]) == 3
    assert d["total_entities"] == 7        # la verità resta dichiarata
    for e in d["e"]:                        # nessun arco verso il vuoto
        assert 0 <= e[0] < 3 and 0 <= e[1] < 3


def test_empty_store(gw):
    client, hdr, _ = gw
    client.post("/v1/memories", headers=hdr, json={"content": "seed", "topic": "t"})
    d = client.get("/v1/graph/full", headers=hdr).json()
    assert d["n"] == [] and d["e"] == []
    assert d["truncated"] is False


def test_tenant_isolation(gw):
    """Il grafo di un tenant non contiene MAI le entità di un altro."""
    client, hdr, tmp = gw
    client.post("/v1/memories", headers=hdr, json={"content": "seed", "topic": "t"})
    _seed(_kg(tmp))
    other = GatewayKeys(tmp / "gateway_keys.db").create(tenant_id="beta")
    ohdr = {"Authorization": f"Bearer {other}"}
    client.post("/v1/memories", headers=ohdr, json={"content": "seed", "topic": "t"})
    d = client.get("/v1/graph/full", headers=ohdr).json()
    assert {row[1] for row in d["n"]} & {"node0", "hermit"} == set()
