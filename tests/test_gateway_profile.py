"""Gateway process profile + GatewayKeys.resolve edges (Giro 1a, 2026-07-15).

Two concerns:

* ``verimem gateway serve`` is the MULTI-TENANT server entry point: it must
  default SQLite to per-commit durability (``synchronous=FULL``) — WAL+NORMAL
  can lose the last committed transaction on an OS crash, acceptable on a
  personal laptop, not on a store serving paying tenants. An explicit operator
  override always wins (setdefault semantics). The SDK / personal console keep
  NORMAL (their default is unchanged).

* ``GatewayKeys.resolve`` edge cases — a REGRESSION NET, declared as such:
  these tests pass on the pre-refactor fetchall+loop implementation too; they
  pin the behaviour the indexed-lookup refactor must preserve (valid key →
  tenant, unknown/empty/None → None, revoked → None, two keys per tenant).
"""
from __future__ import annotations

import os

import pytest

fastapi = pytest.importorskip("fastapi")  # gateway extra — same skip as test_gateway.py

from verimem.gateway import GatewayKeys  # noqa: E402

# ---- serve profile: synchronous=FULL by default -----------------------------

def _run_serve_without_uvicorn(monkeypatch, tmp_path):
    """Invoke the real ``gateway serve`` command body with uvicorn.run stubbed
    out — everything up to (and including) the env profile runs for real."""
    uvicorn = pytest.importorskip("uvicorn")
    monkeypatch.setattr(uvicorn, "run", lambda *a, **k: None)
    from verimem.cli import gateway_serve
    gateway_serve(host="127.0.0.1", port=0, data_dir=str(tmp_path), rate_limit=0)


def test_gateway_serve_defaults_sqlite_synchronous_full(monkeypatch, tmp_path):
    monkeypatch.delenv("ENGRAM_SQLITE_SYNCHRONOUS", raising=False)
    try:
        _run_serve_without_uvicorn(monkeypatch, tmp_path)
        from verimem._sqlite_pragma import synchronous_mode
        assert os.environ.get("ENGRAM_SQLITE_SYNCHRONOUS") == "FULL"
        assert synchronous_mode() == "FULL"
    finally:
        # gateway_serve writes os.environ directly (by design: process profile);
        # monkeypatch can't undo a set it didn't make — clean up explicitly.
        os.environ.pop("ENGRAM_SQLITE_SYNCHRONOUS", None)


def test_gateway_serve_respects_operator_override(monkeypatch, tmp_path):
    monkeypatch.setenv("ENGRAM_SQLITE_SYNCHRONOUS", "NORMAL")
    _run_serve_without_uvicorn(monkeypatch, tmp_path)
    from verimem._sqlite_pragma import synchronous_mode
    assert os.environ.get("ENGRAM_SQLITE_SYNCHRONOUS") == "NORMAL"
    assert synchronous_mode() == "NORMAL"


def test_sdk_default_stays_normal(monkeypatch):
    # The durability flip is a SERVER profile, not a global one: the bare SDK
    # (pip install verimem; Memory()) keeps the WAL+NORMAL default.
    monkeypatch.delenv("ENGRAM_SQLITE_SYNCHRONOUS", raising=False)
    from verimem._sqlite_pragma import synchronous_mode
    assert synchronous_mode() == "NORMAL"


# ---- GatewayKeys.resolve regression net -------------------------------------

def test_resolve_roundtrip_two_tenants_two_keys(tmp_path):
    keys = GatewayKeys(tmp_path / "keys.db")
    k1 = keys.create(tenant_id="acme", name="a")
    k2 = keys.create(tenant_id="acme", name="b")
    kb = keys.create(tenant_id="beta")
    assert keys.resolve(k1) == "acme"
    assert keys.resolve(k2) == "acme"
    assert keys.resolve(kb) == "beta"


def test_resolve_unknown_empty_and_none_are_none(tmp_path):
    keys = GatewayKeys(tmp_path / "keys.db")
    keys.create(tenant_id="acme")
    assert keys.resolve("vm_" + "0" * 40) is None
    assert keys.resolve("") is None
    assert keys.resolve(None) is None


def test_resolve_revoked_key_is_none(tmp_path):
    keys = GatewayKeys(tmp_path / "keys.db")
    k = keys.create(tenant_id="acme")
    assert keys.resolve(k) == "acme"
    key_id = keys.list()[0]["key_id"]
    assert keys.revoke(key_id) is True
    assert keys.resolve(k) is None
    assert keys.revoke(key_id) is False  # double-revoke: no-op, reported
