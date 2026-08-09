"""La garanzia dei record nascosti esce anche dalla porta HTTP?

«Una garanzia che esiste in un posto solo» e' la classe che questa casa ha
mappato piu' volte: astensione su `explain` e non su `recall`, onesta' su
`search-docs` e non su `recall`, versioning sui documenti e non sui fatti,
undo su `forget` e non su `supersede`. La cura dei record nascosti e' nata su
`Memory.recall` e rischiava di restare la settima voce di quell'elenco.

Questo test la INCHIODA sull'HTTP — la superficie che un cliente vero usa —
perche' `gateway.search` restituisce i dizionari interi (`return {"hits":
hits}`) e quindi il campo passa GRATIS: e' esattamente il genere di cosa che
smette di passare il giorno in cui qualcuno seleziona i campi da serializzare,
in buona fede, per snellire la risposta.

⚠️ NON verifica il contenuto della dichiarazione (per quello ci sono i test
del modulo): verifica che ESCA. La classe che uccide non e' il campo
sbagliato, e' il campo che sparisce da una porta sola.
"""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from verimem.client import Memory  # noqa: E402
from verimem.gateway import GatewayKeys, create_app  # noqa: E402

ANALITI = ["zinco", "piombo", "cadmio", "rame", "nichel"]
DOMANDA = "Quanto zinco contiene il campione S-007?"


@pytest.fixture()
def porta(tmp_path):
    """Un registro di dodici schede distinte: il write path le incatena e ne
    lascia servibile una sola — e' il caso che la cura esiste per dichiarare."""
    mem = Memory(tmp_path / "registro.db")
    for i in range(1, 13):
        mem.add(f"Il campione S-{i:03d} contiene {ANALITI[i % 5]} "
                f"a {10 + i} milligrammi per litro.", topic="lab/registro")
    app = create_app(data_dir=tmp_path / "gw",
                     keys=GatewayKeys(tmp_path / "gw" / "keys.db"),
                     local_tenant="local", local_memory=mem)
    return TestClient(app, base_url="http://127.0.0.1")


def test_il_campo_esce_dalla_porta_http(porta):
    r = porta.get("/v1/search", params={"q": DOMANDA, "k": 1})
    assert r.status_code == 200, r.text
    hits = (r.json() or {}).get("hits") or []
    assert hits, "nessun risultato dalla porta HTTP"
    assert "hidden_records" in hits[0], (
        "la dichiarazione dei record nascosti non esce dall'HTTP: "
        f"campi presenti = {sorted(hits[0])}")


def test_la_dichiarazione_nomina_il_record_chiesto(porta):
    r = porta.get("/v1/search", params={"q": DOMANDA, "k": 1})
    nascosti = ((r.json() or {}).get("hits") or [{}])[0].get("hidden_records")
    assert nascosti, "campo presente ma vuoto"
    assert any(n.get("code") == "S-007" for n in nascosti), nascosti


def test_una_domanda_senza_codici_non_porta_il_campo(porta):
    """IL PRESIDIO, anche qui: la risposta ordinaria resta quella di prima."""
    r = porta.get("/v1/search", params={"q": "Come procede il lavoro?", "k": 1})
    assert r.status_code == 200, r.text
    for h in (r.json() or {}).get("hits") or []:
        assert "hidden_records" not in h
