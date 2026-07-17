"""Trust ledger: il contatore di ciò che il gate ha FATTO — l'odometro della fiducia.

Ogni memory layer vanta accuracy; nessuno mostra all'utente quante claim non
supportate ha quarantenato, quante contraddizioni ha rifiutato, quante volte ha
risposto "non lo so" invece di inventare. Questi numeri esistono già dentro
Verimem (gate + trust report) ma evaporano a fine chiamata. Il ledger li
persiste nello stesso DB dello store (i backup lo coprono gratis) SENZA il
testo delle proposizioni (niente PII nel contatore) e li espone come
``Memory.trust_stats()`` + ``GET /v1/stats`` per tenant sul gateway.

Naming onesto (A4): non "hallucinations stopped" — contiamo azioni osservabili
del gate: admitted / quarantined / rejected / abstained.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory

_UNSUPPORTED = "the deployment works and is verified in production"


class _LowScoreJudge:
    """Stub L4: qualsiasi (source, fact) → 'SCORE: 5' = bocciato (sotto soglia)."""

    def complete(self, system, messages, **kw):
        class R:
            text = "SCORE: 5"
            total_tokens = 1
        return R()


def test_clean_add_counts_admitted(tmp_path):
    m = Memory(tmp_path / "m.db")
    r = m.add("deploy pipeline is green", verified_by=["ci:main:green"])
    assert r["stored"] is True
    s = m.trust_stats()
    assert s["ledger"]["admitted"] == 1
    assert s["ledger"]["quarantined"] == 0
    assert s["ledger"]["rejected"] == 0


def test_unsupported_selfclaim_counts_quarantined(tmp_path):
    m = Memory(tmp_path / "m.db")
    r = m.add(_UNSUPPORTED)  # nessuna evidenza → L1 downgrade storico
    assert r["status"] == "quarantined"
    s = m.trust_stats()
    assert s["ledger"]["quarantined"] == 1
    assert any(layer.startswith("L1") for layer in s["by_layer"]), (
        "il breakdown dice QUALE layer ha agito (sub-layer L1.x)"
    )


def test_reject_counts_rejected(tmp_path):
    m = Memory(tmp_path / "m.db", preset="strict", grounding_llm=_LowScoreJudge())
    r = m.add("the contract was signed by both parties",
              source="meeting notes: we discussed the weather")
    assert r["stored"] is False
    s = m.trust_stats()
    assert s["ledger"]["rejected"] == 1


def test_abstention_counts(tmp_path):
    m = Memory(tmp_path / "m.db")
    report = m.explain("what is the capital of atlantis?")  # store vuoto
    assert report["abstained"] is True
    s = m.trust_stats()
    assert s["ledger"]["abstained"] == 1


def test_ledger_is_fail_open(tmp_path, monkeypatch):
    """Il contatore non deve MAI rompere una scrittura: se il ledger esplode,
    add funziona identico (il ledger è osservabilità, non data-path)."""
    from verimem import trust_ledger

    m = Memory(tmp_path / "m.db")

    def boom(self, *a, **kw):
        raise RuntimeError("ledger db is broken")

    monkeypatch.setattr(trust_ledger.TrustLedger, "record", boom)
    r = m.add("fact survives ledger failure", verified_by=["doc:1"])
    assert r["stored"] is True


def test_ledger_persists_across_reopen(tmp_path):
    db = tmp_path / "m.db"
    m1 = Memory(db)
    m1.add(_UNSUPPORTED)
    del m1
    m2 = Memory(db)
    s = m2.trust_stats()
    assert s["ledger"]["quarantined"] == 1, "il ledger vive nel DB, non in RAM"


def test_store_breakdown_reflects_live_facts(tmp_path):
    m = Memory(tmp_path / "m.db")
    m.add("verified fact", verified_by=["ci:x:green"])
    m.add(_UNSUPPORTED)
    s = m.trust_stats()
    assert sum(s["store"].values()) == 2, "breakdown per status dei fatti vivi"
    assert s["store"].get("quarantined", 0) == 1


def test_no_proposition_text_in_ledger(tmp_path):
    """Privacy: il ledger conta, non ricopia — mai il testo del fatto."""
    import sqlite3

    m = Memory(tmp_path / "m.db")
    m.add("SECRET-TOKEN-XYZ is the admin password")  # L1 lo quarantena o ammette
    with sqlite3.connect(tmp_path / "m.db") as con:
        rows = con.execute("SELECT * FROM trust_ledger").fetchall()
    assert rows, "un evento registrato"
    assert not any("SECRET-TOKEN-XYZ" in str(cell) for row in rows for cell in row)


def test_gateway_tenant_stats_endpoint(tmp_path):
    """GET /v1/stats: il tenant vede il SUO odometro (trust + usage) con la
    sola bearer key — è la pagina 'perché fidarti' del servizio online."""
    fastapi = pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from verimem.gateway import GatewayKeys, create_app

    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    api_key = keys.create(tenant_id="acme", name="t")
    client = TestClient(create_app(data_dir=tmp_path, keys=keys))
    h = {"Authorization": f"Bearer {api_key}"}

    client.post("/v1/memories", headers=h,
                json={"content": "green build", "verified_by": ["ci:1"]})
    client.get("/v1/search", headers=h, params={"q": "build"})

    assert client.get("/v1/stats").status_code == 401, "senza chiave: 401"
    r = client.get("/v1/stats", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["trust"]["ledger"]["admitted"] >= 1
    assert body["usage"]["requests"] >= 2


# ---- serie giornaliera (la console v2 disegna sparkline VERE) ---------------

def test_daily_series_buckets_by_day(tmp_path):
    """Gli eventi hanno già ts: la serie per-giorno è un GROUP BY, non una
    nuova tabella. Oggi deve contenere ciò che è appena successo."""
    m = Memory(tmp_path / "m.db")
    m.add("the office is in Milan", topic="hq", verified_by=["hr-doc"])
    m.add(_UNSUPPORTED)
    s = m.trust_stats()
    daily = s["daily"]
    assert isinstance(daily, list) and daily, "almeno il giorno corrente"
    today = daily[-1]
    assert today["admitted"] == 1
    assert today["quarantined"] == 1
    assert set(today) == {"day", "admitted", "quarantined",
                          "rejected", "abstained"}
    import time as _t
    assert today["day"] == _t.strftime("%Y-%m-%d", _t.gmtime())


def test_daily_series_is_capped_and_fail_open(tmp_path):
    from verimem.trust_ledger import TrustLedger
    led = TrustLedger(tmp_path / "x.db")
    for _ in range(3):
        led.record("admitted")
    d = led.stats(daily_days=1)["daily"]
    assert len(d) == 1 and d[0]["admitted"] == 3
    # fail-open: db illeggibile → daily assente ma stats non esplode
    bad = TrustLedger(tmp_path)  # directory, non file
    out = bad.stats()
    assert out["ledger"]["admitted"] == 0
