"""Backup/restore del gateway (datacenter design, Fase 1).

Nessun deploy enterprise senza backup: snapshot CONSISTENTE della directory
gateway (keys db + tutti gli store tenant) usando l'online backup API di
SQLite — corretto anche con connessioni WAL aperte, senza fermare il server.
Il restore ricrea la struttura per-tenant; un manifest dichiara cosa
contiene lo snapshot (verificabilità = brand).
"""
from __future__ import annotations

import json
import sqlite3

from engram.gateway import GatewayKeys, create_app
from engram.gateway_backup import backup_gateway, restore_gateway

try:
    from fastapi.testclient import TestClient
    _HAVE_FASTAPI = True
except ImportError:  # pragma: no cover
    _HAVE_FASTAPI = False

import pytest

pytestmark = pytest.mark.skipif(not _HAVE_FASTAPI, reason="fastapi extra")


def _gateway_with_data(tmp_path):
    data = tmp_path / "gw"
    keys = GatewayKeys(data / "gateway_keys.db")
    key = keys.create(tenant_id="acme", name="ci")
    app = create_app(data_dir=data, keys=keys)
    client = TestClient(app)
    r = client.post("/v1/memories", headers={"Authorization": f"Bearer {key}"},
                    json={"content": "the deploy pipeline is green",
                          "verified_by": ["ci:main:green"]})
    assert r.status_code == 200 and r.json()["stored"] is True
    return data, keys, key, client


def test_backup_snapshots_keys_and_tenant_stores(tmp_path):
    data, *_ = _gateway_with_data(tmp_path)
    dest = tmp_path / "snap"
    manifest = backup_gateway(data, dest)
    assert (dest / "gateway_keys.db").exists()
    assert (dest / "tenants" / "acme" / "memory.db").exists()
    assert manifest["n_tenants"] == 1 and "acme" in manifest["tenants"]
    # il manifest è anche persistito nello snapshot
    on_disk = json.loads((dest / "backup_manifest.json").read_text("utf-8"))
    assert on_disk["n_tenants"] == 1


def test_backup_is_consistent_while_connections_are_open(tmp_path):
    """Il backup gira MENTRE il gateway ha connessioni aperte (WAL): lo
    snapshot deve contenere il fatto appena scritto — online backup API,
    non copia file cieca (che con -wal separato perde le ultime scritture)."""
    data, keys, key, client = _gateway_with_data(tmp_path)
    dest = tmp_path / "snap"
    backup_gateway(data, dest)
    conn = sqlite3.connect(dest / "tenants" / "acme" / "memory.db")
    rows = conn.execute(
        "select count(*) from facts where proposition like '%deploy pipeline%'"
    ).fetchone()[0]
    conn.close()
    assert rows == 1, "lo snapshot deve includere le scritture già committate"


def test_restore_recreates_a_working_gateway(tmp_path):
    data, keys, key, _ = _gateway_with_data(tmp_path)
    dest = tmp_path / "snap"
    backup_gateway(data, dest)

    target = tmp_path / "restored"
    restore_gateway(dest, target)
    keys2 = GatewayKeys(target / "gateway_keys.db")
    app2 = create_app(data_dir=target, keys=keys2)
    client2 = TestClient(app2)
    r = client2.get("/v1/search", params={"q": "deploy pipeline"},
                    headers={"Authorization": f"Bearer {key}"})
    assert r.status_code == 200
    assert any("deploy pipeline" in h["text"] for h in r.json()["hits"]), (
        "la STESSA chiave e gli stessi dati funzionano sul restore"
    )


def test_restore_refuses_nonempty_target(tmp_path):
    data, *_ = _gateway_with_data(tmp_path)
    dest = tmp_path / "snap"
    backup_gateway(data, dest)
    target = tmp_path / "busy"
    target.mkdir()
    (target / "existing.txt").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="not empty"):
        restore_gateway(dest, target)
