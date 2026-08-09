"""La ricevuta HTTP è lo SPECCHIO di quella dell'SDK, campo per campo.

ws4 ha misurato il 2026-08-05 che il campo ``moat`` — «il giudice è girato
o no» — esiste sull'SDK come enum (``not_run:no_source``) e su MCP come
frase, e che **su HTTP non c'è**: cercando «moat» in ``gateway.py`` si
trovano tre commenti e nessun campo di risposta. La conclusione era «chi
scrive dal gateway non può sapere se il moat è girato: questo è il buco
vero».

Misurato qui in diretta, e la localizzazione era sbagliata: il gateway
**non filtra niente**. ``POST /v1/memories`` fa ``return res``
(``gateway.py:1176``), dove ``res`` è la ricevuta dell'SDK verbatim.
Su questo ramo le chiavi coincidono::

    HTTP : ['adjudication','advice','grounding_score','id','status','stored','warnings']
    SDK  : ['adjudication','advice','grounding_score','id','status','stored','warnings']

Nessuna delle due ha ``moat``, per la stessa ragione: la ricevuta della
base di merge non ce l'ha. Sul ramo ``ws3/gate-precision`` il campo viene
posato in ``client.py:761`` — e da lì esce su HTTP **senza una riga di
lavoro sul gateway**. Non c'era un buco da tappare; c'era da fissare la
proprietà, che finora era un fatto accidentale del codice e non una
garanzia: basta che qualcuno introduca una whitelist di risposta perché
il buco che ws4 descriveva diventi vero davvero.

⚠️ Lo specchio è TOTALE e va detto: una chiave aggiunta alla ricevuta
esce su HTTP senza che nessuno la riveda. È la stessa proprietà che
rende gratis il campo di ws3, letta dall'altro lato.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory

pytest.importorskip("fastapi")

_MILAN = "The head office of the company is in Milan."


def _client(tmp_path):
    from fastapi.testclient import TestClient

    from verimem.gateway import GatewayKeys, create_app

    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    key = keys.create(tenant_id="t1", name="ci")
    return (TestClient(create_app(data_dir=tmp_path, keys=keys)),
            {"Authorization": f"Bearer {key}"})


def test_la_risposta_http_e_la_ricevuta_dell_sdk_verbatim(tmp_path, monkeypatch):
    """Non «le stesse chiavi che mi aspetto»: LA STESSA ricevuta. Il
    confronto è con l'oggetto che l'SDK ha davvero restituito in quella
    chiamata, catturato al volo — così il test non invecchia quando la
    ricevuta cresce."""
    client, hdr = _client(tmp_path)
    visto: list[dict] = []
    originale = Memory.add

    def _cattura(self, *a, **kw):
        r = originale(self, *a, **kw)
        visto.append(dict(r))
        return r

    monkeypatch.setattr(Memory, "add", _cattura)
    resp = client.post("/v1/memories",
                       json={"content": _MILAN, "topic": "hq"}, headers=hdr)

    assert resp.status_code == 200
    assert len(visto) == 1, "il gateway deve passare dall'SDK, non scrivere a mano"
    assert resp.json() == visto[0]


def test_un_campo_nuovo_della_ricevuta_esce_su_http_senza_toccare_il_gateway(
        tmp_path, monkeypatch):
    """IL CASO DI ws4, in forma falsificabile: si inietta il campo su UNA
    porta (l'SDK) e si legge sull'ALTRA (HTTP). Se il gateway filtrasse la
    risposta — cioè se il buco descritto esistesse — questo fallirebbe.

    Iniettare invece nella sorgente condivisa avrebbe fatto muovere tutte
    le porte insieme e il test sarebbe passato per costruzione: è la
    falsificazione tautologica già pagata su questo ramo il 2026-08-05."""
    client, hdr = _client(tmp_path)
    originale = Memory.add

    def _con_moat(self, *a, **kw):
        r = originale(self, *a, **kw)
        r["moat"] = "not_run:no_source"
        return r

    monkeypatch.setattr(Memory, "add", _con_moat)
    resp = client.post("/v1/memories",
                       json={"content": _MILAN, "topic": "hq"}, headers=hdr)

    assert resp.status_code == 200
    assert resp.json().get("moat") == "not_run:no_source", (
        "il gateway ha filtrato la ricevuta: il campo che l'SDK posa non "
        "arriva al client HTTP")


def test_lo_specchio_vale_anche_quando_la_scrittura_e_respinta(tmp_path):
    """Una risposta di rifiuto è il momento in cui uno legge la ricevuta
    per capire PERCHÉ: se lo specchio si rompesse lì, si romperebbe dove
    serve di più. Il claim non supportato viene fermato dallo screen L1,
    che è sempre acceso e non chiede giudice."""
    client, hdr = _client(tmp_path)
    resp = client.post(
        "/v1/memories",
        json={"content": "The migration is complete and fully verified.",
              "topic": "hq"}, headers=hdr)

    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") == "quarantined", body
    # gli stessi campi diagnostici della ricevuta SDK, non un sottoinsieme
    for k in ("stored", "status", "warnings", "advice", "grounding_score"):
        assert k in body, f"manca {k} nella risposta di rifiuto: {body}"
