"""Le cure di questa notte arrivano fino alla porta HTTP — e ora c'è chi lo controlla.

LA DOMANDA che ha generato questo file: sette cure consegnate in una notte
aggiungono campi alla risposta. **Arrivano al cliente HTTP, o si fermano
all'SDK?** Era la domanda giusta da farsi, perché la classe che ha prodotto più
difetti stanotte è esattamente questa — «la cura nasce su una superficie e le
altre restano indietro», arrivata fino alla SETTIMA generazione.

LA RISPOSTA, misurata da cliente (TestClient, in-process)::

    POST /v1/memories  fatto lungo   -> warnings=['long_fact']
    POST /v1/memories  duplicato     -> warnings=['duplicate']
    POST /v1/memories  topic+spazio  -> warnings=['topic_spazi']
    GET  /v1/explain                 -> floor_applied_by · ungrounded_facts ·
                                        grounding_checked

Arrivano tutte. E il motivo è che stanno in `client.py`, cioè nel punto da cui
passano tutte le porte: la mappa costruita per inseguire le cure che restavano
indietro (`via SDK 21 · via a.semantic DIRETTO 14`) ha funzionato al contrario
— curare nel posto giusto propaga da solo.

⚠️ QUESTO FILE ESISTE PER TENERLE LÌ. Il giorno in cui il gateway costruirà una
sua risposta invece di inoltrare quella dell'SDK, questi test cadono — invece
di scoprirlo fra un mese da un cliente che non vede un avviso.

📌 E CHIUDE UN DUBBIO DI ws5: «trust_report su HTTP non c'è affatto, 0
occorrenze in gateway.py». Il NOME non c'è, il dossier sì: è `/v1/explain`, e
risponde 200 con tutti i campi.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from verimem.gateway import GatewayKeys, create_app  # noqa: E402

LUNGO = ("Il protocollo prevede che " + " ".join(
    f"il passo {i} sia eseguito dall'operatore registrando il valore"
    for i in range(1, 40)) + ". Il limite e' 0,2 mg/l.")


@pytest.fixture()
def cliente(tmp_path):
    keys = GatewayKeys(tmp_path / "keys.db")
    api_key = keys.create(tenant_id="t-http")
    c = TestClient(create_app(data_dir=tmp_path / "gw", keys=keys))
    return c, {"Authorization": f"Bearer {api_key}"}


def _layers(risposta) -> list[str]:
    return [w.get("layer") for w in (risposta.json().get("warnings") or [])]


def test_CONTROLLO_POSITIVO_una_scrittura_ordinaria_passa(cliente):
    """Se questa cade, è rotto il banco e non serve guardare il resto."""
    c, H = cliente
    r = c.post("/v1/memories", headers=H, json={
        "content": "Il magazzino centrale ha 4200 metri quadrati.",
        "topic": "az/mag"})
    assert r.status_code == 200, r.text
    assert r.json().get("stored") is True
    assert not _layers(r), "una scrittura ordinaria non deve portare avvisi"


def test_l_avviso_sul_fatto_lungo_arriva_al_cliente(cliente):
    c, H = cliente
    r = c.post("/v1/memories", headers=H,
               json={"content": LUNGO, "topic": "lab/p"})
    assert "long_fact" in _layers(r), r.json().get("warnings")


def test_l_avviso_sul_duplicato_arriva_al_cliente(cliente):
    c, H = cliente
    corpo = {"content": "Il piano annuale costa 1200 euro.", "topic": "az/l"}
    c.post("/v1/memories", headers=H, json=corpo)
    r = c.post("/v1/memories", headers=H, json=corpo)
    assert "duplicate" in _layers(r), r.json().get("warnings")


def test_l_avviso_sul_topic_con_spazi_arriva_al_cliente(cliente):
    c, H = cliente
    r = c.post("/v1/memories", headers=H, json={
        "content": "Il deposito B ha 300 metri quadrati.", "topic": "az/mag "})
    assert "topic_spazi" in _layers(r), r.json().get("warnings")


def test_il_dossier_esiste_su_HTTP_e_porta_i_campi_nuovi(cliente):
    """📌 ws5: «trust_report su HTTP non c'è affatto». Il NOME no, il dossier
    sì — e porta i tre campi aggiunti stanotte."""
    c, H = cliente
    c.post("/v1/memories", headers=H, json={
        "content": "Il magazzino centrale ha 4200 metri quadrati.",
        "topic": "az/mag"})
    r = c.get("/v1/explain", headers=H,
              params={"q": "Quanti metri quadrati ha il magazzino?"})
    assert r.status_code == 200, r.text
    chiavi = set(r.json())
    for campo in ("floor_applied_by", "ungrounded_facts", "grounding_checked"):
        assert campo in chiavi, f"«{campo}» non arriva su HTTP: {sorted(chiavi)}"


def test_la_ricerca_rende_i_fatti_scritti(cliente):
    """⚠️ E la chiave è `hits`, non `items` né `facts`. Il primo banco cercava
    `items` e concludeva che la ricerca fosse vuota: prima di contare un campo,
    stampa le chiavi — decima volta stanotte."""
    c, H = cliente
    c.post("/v1/memories", headers=H, json={
        "content": "Il magazzino centrale ha 4200 metri quadrati.",
        "topic": "az/mag"})
    r = c.get("/v1/search", headers=H, params={"q": "magazzino", "k": "3"})
    assert r.status_code == 200, r.text
    hits = r.json().get("hits")
    assert hits, f"chiavi della risposta: {sorted(r.json())}"
    assert "4200" in str(hits[0].get("text"))
