"""Trust dashboard del gateway: l'odometro che si VEDE.

Il trust ledger (task 8) espone i numeri via API/CLI; questa è la vetrina:
``GET /dashboard`` serve UNA pagina HTML self-contained (zero CDN, zero
template engine, zero dipendenze nuove) che chiede al tenant la sua bearer
key nel browser e fetcha ``/v1/stats``. Proprietà di sicurezza: la pagina è
STATICA e PUBBLICA perché non contiene alcun dato — i numeri viaggiano solo
nel fetch autenticato; la chiave vive in sessionStorage (muore con la tab),
mai in un URL, mai al server fuori dall'header Authorization.
"""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from verimem.gateway import GatewayKeys, create_app  # noqa: E402


@pytest.fixture()
def gw(tmp_path):
    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    return TestClient(create_app(data_dir=tmp_path, keys=keys)), keys


def test_dashboard_page_served_without_auth(gw):
    client, _ = gw
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    # la pagina parla al data plane autenticato, non incorpora dati
    assert "/v1/stats" in r.text
    assert "Authorization" in r.text, "il fetch usa la bearer key, non query param"


def test_dashboard_page_is_static_and_data_free(gw):
    """Nessun dato server-side nella pagina: niente chiavi (prefisso vm_),
    niente tenant id, niente numeri di store. Due tenant diversi ricevono
    BYTE-IDENTICO: la pagina non può leakare nulla perché non contiene nulla."""
    client, keys = gw
    keys.create(tenant_id="acme", name="a")
    first = client.get("/dashboard").text
    keys.create(tenant_id="globex", name="b")
    second = client.get("/dashboard").text
    assert first == second
    assert "vm_" not in first.replace("vm_ prefix", "")  # nessuna chiave reale
    assert "acme" not in first and "globex" not in first


def test_dashboard_key_never_in_url(gw):
    """La pagina non deve MAI mettere la chiave in un URL (query string =
    access log = leak). Il fetch la passa solo come header."""
    client, _ = gw
    page = client.get("/dashboard").text
    assert "key=" not in page.lower().replace("keydown", ""), (
        "nessun pattern ?key= / &key= nella pagina"
    )
    assert "sessionStorage" in page, "la chiave vive in sessionStorage, non in URL"
