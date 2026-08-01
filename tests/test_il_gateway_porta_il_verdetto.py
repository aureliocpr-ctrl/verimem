"""L'ultimo canale: quello che un TEAM usa per leggere la memoria.

Il censimento delle superfici di lettura MCP e' chiuso (14 su 15) e la CLI e'
stata curata dove serviva. Restava il gateway HTTP, che e' il modo in cui
qualcuno che non sta su questa macchina interroga il corpus — e per un team e'
IL canale, non uno dei tanti.

Dichiararlo a posto perche' gli altri due lo sono sarebbe la forma esatta del
difetto di questi giorni: «funziona sul percorso che ho guardato». Qui si
guarda anche questo.
"""
from __future__ import annotations

import sqlite3

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from verimem.gateway import GatewayKeys, create_app  # noqa: E402

FATTO = "Il servizio di fatturazione ascolta sulla porta 8443."
SOURCE = "Runbook: il servizio di fatturazione ascolta sulla porta 8443."
QUERY = "su quale porta ascolta il servizio di fatturazione"
VERDETTO = 88.5


@pytest.fixture()
def gw(tmp_path):
    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    key = keys.create(tenant_id="team-alpha", name="ci")
    app = create_app(data_dir=tmp_path, keys=keys)
    client = TestClient(app)
    r = client.post("/v1/memories",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"content": FATTO, "topic": "prova",
                          "source": SOURCE})
    assert r.status_code in (200, 201), r.text
    # verdetto deterministico, per non misurare la presenza del giudice
    for db in tmp_path.rglob("semantic.db"):
        con = sqlite3.connect(str(db))
        con.execute("UPDATE facts SET grounding_score = ?", (VERDETTO,))
        con.commit()
        con.close()
    return client, key


def _get(gw, path: str, **params) -> dict:
    client, key = gw
    r = client.get(path, headers={"Authorization": f"Bearer {key}"},
                   params=params or None)
    assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"
    return r.json()


@pytest.mark.parametrize("path,params", [
    ("/v1/search", {"q": QUERY}),
    ("/v1/explain", {"q": QUERY}),
])
def test_una_lettura_dal_gateway_porta_il_verdetto(gw, path, params):
    corpo = str(_get(gw, path, **params))
    assert "8443" in corpo, f"{path} non ha restituito il fatto: {corpo[:300]}"
    assert "grounding_score" in corpo or str(VERDETTO) in corpo, (
        f"{path} restituisce il fatto SENZA il verdetto — un team che legge di "
        f"qui non distingue un fatto verificato da uno mai giudicato:\n"
        f"{corpo[:400]}")


def test_il_fatto_singolo_porta_il_verdetto(gw):
    """`GET /v1/memories/{id}`: il re-fetch per id e' dove un consumatore
    torna a prendere il fatto che ha gia' visto passare."""
    elenco = _get(gw, "/v1/search", q=QUERY)
    hits = elenco.get("hits") or []
    assert hits and "8443" in str(hits), elenco
    # L'id si prende dalla STRUTTURA. La prima versione lo cercava con
    # re.search(r"[0-9a-f]{12}") sulla risposta serializzata e catturava dodici
    # cifre del timestamp — poi 404, e il rosso sembrava dell'endpoint.
    fid = hits[0]["id"]
    corpo = str(_get(gw, f"/v1/memories/{fid}"))
    assert "grounding_score" in corpo or str(VERDETTO) in corpo, corpo[:400]
