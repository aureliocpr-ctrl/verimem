"""Write idempotency under CONCURRENCY and under flood (Kimi audit F6).

The Idempotency-Key feature exists to stop a retried write from storing a twin.
As first shipped it checked the cache, executed, then stored the receipt — three
separate steps with no mutual exclusion. Two retries of the SAME key that arrive
together therefore both miss the cache and both execute: the twin write the
feature was built to prevent, reproduced by the feature's own race.

The cache was also pruned only by TTL, so a flood of unique keys grew the
process memory unbounded for the whole TTL window (rate limiting is off by
default) — a cheap memory DoS.
"""
from __future__ import annotations

import threading

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from verimem.gateway import GatewayKeys, create_app  # noqa: E402


@pytest.fixture()
def gw(tmp_path):
    keys = GatewayKeys(tmp_path / "keys.db")
    api_key = keys.create(tenant_id="tenant-race")
    app = create_app(data_dir=tmp_path / "gwdata", keys=keys)
    return TestClient(app), api_key, app


def test_concurrent_same_key_stores_once(gw):
    """Two simultaneous retries of one key -> ONE receipt, ONE stored fact."""
    client, api_key, _app = gw
    h = {"Authorization": f"Bearer {api_key}", "Idempotency-Key": "race-1"}
    body = {"content": "The turbine holds 750 liters.", "topic": "race/t"}
    out: list[dict] = []
    err: list[BaseException] = []

    def _go():
        try:
            out.append(client.post("/v1/memories", json=body, headers=h).json())
        except BaseException as exc:  # noqa: BLE001 - surface in the assert
            err.append(exc)

    threads = [threading.Thread(target=_go) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=180)

    assert not err, f"request raised: {err!r}"
    assert len(out) == 2
    ids = {r.get("id") for r in out}
    assert len(ids) == 1, f"twin write: two different ids {ids}"

    hits = client.get("/v1/search", params={"q": "turbine holds", "k": 10},
                      headers={"Authorization": f"Bearer {api_key}"}).json()["hits"]
    assert len([x for x in hits if "750" in str(x.get("text", ""))]) == 1


def test_idempotency_cache_is_bounded(tmp_path, monkeypatch):
    """A flood of unique keys must not grow the cache without limit."""
    monkeypatch.setenv("VERIMEM_IDEM_MAX", "2")
    keys = GatewayKeys(tmp_path / "keys.db")
    api_key = keys.create(tenant_id="tenant-flood")
    app = create_app(data_dir=tmp_path / "gwdata", keys=keys)
    client = TestClient(app)
    for i in range(5):
        client.post("/v1/memories",
                    json={"content": f"Pump number {i} holds {100 + i} liters.",
                          "topic": "flood/t"},
                    headers={"Authorization": f"Bearer {api_key}",
                             "Idempotency-Key": f"flood-{i}"})
    assert len(app.state.idem_cache) <= 2
