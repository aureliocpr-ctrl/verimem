"""Memory-map live dashboard — RED contract test.

Verifica i 4 entry-point richiesti dal brief feature/memory-map-live:

  • GET /memory-map                       (HTML page con mount Cytoscape)
  • GET /api/memory-map/graph             (JSON envelope multi-layer)
  • GET /api/memory-map/events            (SSE stream cross-process)
  • emit() → ~/.engram/events.jsonl       (file-based event log)

I test NON dipendono da un agent reale: monkey-patch su dashboard._ag
returna un MagicMock con liste vuote. Il graph endpoint deve sopravvivere
a store vuoti senza eccezioni.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from verimem import settings as user_settings


@pytest.fixture
def isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(
        user_settings,
        "SETTINGS_FILE",
        tmp_path / "user_settings.json",
    )
    return tmp_path


@pytest.fixture
def fake_dashboard_agent(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace dashboard._ag with a stub returning empty collections."""
    from verimem import dashboard as dash

    fake = MagicMock()

    # Skills layer
    fake.skills.all.return_value = []
    fake.skills.count.return_value = 0

    # Episodes layer
    fake.memory.all.return_value = []
    fake.memory.count.return_value = 0

    # Semantic facts layer
    fake.semantic.all.return_value = []
    fake.semantic.count.return_value = 0

    # Entity KG (cycle #70) — may not be present on minimal stubs
    fake.entity_kg = None

    monkeypatch.setattr(dash, "_ag", lambda: fake)
    monkeypatch.setattr(dash, "_agent", fake, raising=False)
    return fake


@pytest.fixture
def client(isolated_settings: Path, fake_dashboard_agent: MagicMock) -> TestClient:
    # Mark user as onboarded to avoid redirect on /.
    user_settings.save(user_settings.UserSettings(onboarded=True))
    from verimem.dashboard import app

    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. HTML page contract — Sigma.js mount point present
# ---------------------------------------------------------------------------


def test_route_memory_map_renders_html_with_grafo_div(client: TestClient) -> None:
    resp = client.get("/memory-map")
    assert resp.status_code == 200, resp.text[:400]
    assert "text/html" in resp.headers["content-type"]
    body = resp.text
    # Mount point: il renderer è stato migrato Cytoscape -> Sigma.js (2026-06);
    # il template DEVE esporre #sigma-container come target di mount.
    assert 'id="sigma-container"' in body, (
        "Manca il <div id=\"sigma-container\"> dove Sigma monta il grafo"
    )
    # Riferimento al renderer (CDN o local) — verifica copertura asset.
    assert "sigma" in body.lower(), (
        "Atteso riferimento a sigma (CDN script o asset) nell'HTML"
    )


# ---------------------------------------------------------------------------
# 2. Graph endpoint contract — multi-layer JSON envelope
# ---------------------------------------------------------------------------


def test_route_api_memory_graph_returns_3layer_json_envelope(
    client: TestClient,
) -> None:
    resp = client.get("/api/memory-map/graph")
    assert resp.status_code == 200, resp.text[:400]
    assert resp.headers["content-type"].startswith("application/json")
    data = resp.json()
    # Envelope canonico: nodes[] + edges[] + layers{} summary per UI sidebar.
    assert "nodes" in data, "envelope manca 'nodes'"
    assert "edges" in data, "envelope manca 'edges'"
    assert "layers" in data, "envelope manca 'layers' (summary per-layer)"
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)
    assert isinstance(data["layers"], dict)
    # I 3 layer core devono comparire come chiave (anche con count 0 su store vuoto).
    required = {"episode", "fact", "skill"}
    missing = required - set(data["layers"].keys())
    assert not missing, f"Layer mancanti nel summary: {missing}"


# ---------------------------------------------------------------------------
# 3. SSE endpoint contract — stream content-type + status 200
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_route_api_memory_events_returns_sse_stream(
    isolated_settings: Path, fake_dashboard_agent: MagicMock
) -> None:
    """SSE endpoint: status 200 + content-type + Cache-Control header.

    Usa ``httpx.AsyncClient + ASGITransport`` invece del ``TestClient``
    sync perché TestClient con BlockingPortal non propaga sempre il
    disconnect ASGI al server, lasciando il generator SSE appeso.
    Async + ASGITransport gestisce nativamente CancelledError on close.
    """
    user_settings.save(user_settings.UserSettings(onboarded=True))
    from verimem.dashboard import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # max_seconds=0.5 → il server chiude il generator dopo 0.5s
        # invece di restare nel loop default 1h. Il test verifica solo
        # gli header SSE — quelli vengono inviati al primo yield.
        async with ac.stream(
            "GET",
            "/api/memory-map/events",
            params={"max_seconds": 0.5},
            timeout=5.0,
        ) as resp:
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith(
                "text/event-stream"
            ), f"Content-type inatteso: {resp.headers['content-type']}"
            # Cache-Control no-cache obbligatorio per evitare buffering proxy.
            assert "no-cache" in resp.headers.get("cache-control", "").lower()


# ---------------------------------------------------------------------------
# 4. Cross-process event log: emit() deve scrivere su file JSONL
# ---------------------------------------------------------------------------


def test_emit_writes_event_to_jsonl_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from verimem import event_jsonl_log
    from verimem.observability import emit

    log_path = tmp_path / "events.jsonl"
    monkeypatch.setattr(event_jsonl_log, "EVENT_LOG_PATH", log_path)

    emit("test_event_for_jsonl", foo=1, bar="abc")

    assert log_path.exists(), (
        f"Atteso file di log a {log_path} dopo emit()"
    )
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert lines, "Il log dovrebbe contenere almeno una riga"
    rec = json.loads(lines[-1])
    assert rec["name"] == "test_event_for_jsonl"
    assert rec["payload"]["foo"] == 1
    assert rec["payload"]["bar"] == "abc"
    assert "ts" in rec and isinstance(rec["ts"], (int, float))
