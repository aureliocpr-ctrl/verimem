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
    """Un registro dove su S-007 una misura e' stata RITIRATA da una seconda.

    ⚠️ CORRETTA il 2026-08-13, e la vecchia fixture non era sbagliata: era
    INDIRETTA. Diceva «dodici schede distinte, il write path le incatena e ne
    lascia servibile una sola», e da li' si aspettava che qualcosa restasse
    nascosto. Misurato: le dodici restano DODICI SERVIBILI — zero incatenate,
    zero quarantinate — perche' l'incatenamento automatico e' stato chiuso
    apposta questa settimana (la memoria si mangiava i fatti veri).

    🔑 E «nascosto» ha una definizione precisa, in `hidden_records._why`: un
    record e' nascosto SOLO se e' `retired` (ha un `superseded_by`) o
    `quarantined`. Un fatto vivo che semplicemente non entra nel top-k NON e'
    nascosto — e infatti aggiungere una seconda misura viva su S-007 non
    bastava: `hidden_records_for` restituiva ancora zero, perche' `_why` le
    scartava entrambe.

    ⇒ Il caso ora e' COSTRUITO invece che sperato: due misure sullo stesso
    codice e la prima RITIRATA dalla seconda. Cosi' il banco misura cio' che
    dichiara — «la garanzia esce dalla porta HTTP» — senza dipendere dalla
    politica di scrittura, che puo' cambiare ancora, ne' da quanto e' bravo il
    retrieval (in origine il caso nasceva da un retrieval che SBAGLIAVA:
    «risponde S-025 a una domanda su S-007, sbagliata e confidente»).
    """
    mem = Memory(tmp_path / "registro.db")
    vecchia = None
    for i in range(1, 13):
        r = mem.add(f"Il campione S-{i:03d} contiene {ANALITI[i % 5]} "
                    f"a {10 + i} milligrammi per litro.", topic="lab/registro")
        if i == 7:
            vecchia = r["id"]
    nuova = mem.add("Il campione S-007 contiene zinco a 42 milligrammi per "
                    "litro secondo la controanalisi.",
                    topic="lab/registro")["id"]
    mem.semantic.supersede(vecchia, nuova, principal="test",
                           reason="controanalisi")
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
