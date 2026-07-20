"""Tests for the shared embedding-encode service (verimem.encode_service).

Uses an injected fake encode_fn so no real model loads — these test the
socket protocol, batching, discovery file, and error handling.
"""
from __future__ import annotations

import json
import socket
import threading

import pytest

from verimem import embedding, encode_service


def _fake_encode(text):
    # Deterministic 3-dim "vector" derived from the text length.
    return [float(len(text)), 1.5, -2.0]


@pytest.fixture
def server(tmp_path):
    srv = encode_service.EncodeServer(
        encode_fn=_fake_encode,
        idle_timeout_s=30,
        discovery_path=tmp_path / "encode_service.json",
        model_name="test-model",
    )
    srv.start()
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.stop()
    thread.join(timeout=2)


def _request(port, obj, token=None):
    # audit F9: data requests now need the per-boot token. Tests pass the
    # server's real token (they hold the server object); ping/discovery do not.
    if token is not None and "ping" not in obj:
        obj = {**obj, "token": token}
    sock = socket.create_connection(("127.0.0.1", port), timeout=5)
    try:
        encode_service.send_msg(sock, obj)
        return encode_service.recv_msg(sock)
    finally:
        sock.close()


def test_ping(server):
    resp = _request(server.port, {"ping": True})
    assert resp["ok"] is True
    assert resp["model"] == "test-model"
    assert isinstance(resp["pid"], int)


def test_encode_single(server):
    resp = _request(server.port, {"text": "abcd"}, token=server._token)
    assert resp["ok"] is True
    assert resp["vec"] == [4.0, 1.5, -2.0]


def test_encode_batch(server):
    resp = _request(server.port, {"texts": ["a", "bbb"]}, token=server._token)
    assert resp["ok"] is True
    assert resp["vecs"] == [[1.0, 1.5, -2.0], [3.0, 1.5, -2.0]]


def test_bad_request_reports_error(server):
    resp = _request(server.port, {"nonsense": 1}, token=server._token)
    assert resp["ok"] is False
    assert "text" in resp["error"]


def test_discovery_file_written(server, tmp_path):
    disco = tmp_path / "encode_service.json"
    assert disco.exists()
    data = json.loads(disco.read_text(encoding="utf-8"))
    assert data["port"] == server.port
    assert data["model"] == "test-model"
    assert isinstance(data["pid"], int)


def test_multiple_requests_one_connection(server):
    sock = socket.create_connection(("127.0.0.1", server.port), timeout=5)
    try:
        encode_service.send_msg(sock, {"text": "x", "token": server._token})
        r1 = encode_service.recv_msg(sock)
        encode_service.send_msg(sock, {"text": "yy", "token": server._token})
        r2 = encode_service.recv_msg(sock)
    finally:
        sock.close()
    assert r1["vec"] == [1.0, 1.5, -2.0]
    assert r2["vec"] == [2.0, 1.5, -2.0]


# --- embedding.encode integration with the service ------------------------


def test_embedding_uses_service_when_available(monkeypatch, tmp_path):
    srv = encode_service.EncodeServer(
        encode_fn=lambda t: [9.0, 8.0, 7.0],
        discovery_path=tmp_path / "d.json",
        model_name="t",
    )
    srv.start()
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setattr(
            encode_service, "read_discovery",
            # scan68b: il client ora usa il daemon SOLO se annuncia lo stesso
            # modello di CONFIG (anti corpus-poisoning) -> il discovery realistico
            # deve riportare quel modello.
            lambda *a, **k: {"host": "127.0.0.1", "port": srv.port,
                             "model": embedding.CONFIG.embedding_model,
                             "token": srv._token},
        )
        monkeypatch.delenv("ENGRAM_ENCODE_SERVICE", raising=False)
        embedding._reset_model_for_tests()  # clear the single-text encode cache
        vec = embedding.encode("svc-unique-query-1")
        assert vec.tolist() == [9.0, 8.0, 7.0]
    finally:
        srv.stop()
        thread.join(timeout=2)


def test_embedding_falls_back_when_no_service(monkeypatch):
    monkeypatch.setattr(encode_service, "read_discovery", lambda *a, **k: None)
    embedding._reset_model_for_tests()
    vec = embedding.encode("svc-unique-query-2")
    # conftest's autouse stub model returns a 384-dim deterministic vector.
    assert vec.shape[0] == 384


def test_encode_via_service_none_on_unreachable_port(monkeypatch):
    monkeypatch.delenv("ENGRAM_ENCODE_SERVICE", raising=False)
    monkeypatch.setattr(
        encode_service, "read_discovery",
        lambda *a, **k: {"host": "127.0.0.1", "port": 1},  # connect fails fast
    )
    assert embedding._encode_via_service("x") is None


def test_encode_service_disabled_by_env(monkeypatch, tmp_path):
    srv = encode_service.EncodeServer(
        encode_fn=lambda t: [1.0, 2.0, 3.0],
        discovery_path=tmp_path / "d.json", model_name="t",
    )
    srv.start()
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setattr(
            encode_service, "read_discovery",
            lambda *a, **k: {"host": "127.0.0.1", "port": srv.port},
        )
        monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "0")
        assert embedding._encode_via_service("x") is None  # disabled → no connect
    finally:
        srv.stop()
        thread.join(timeout=2)


# --- auto-spawn (ensure_running) ------------------------------------------


def test_ensure_running_true_when_reachable(monkeypatch):
    from verimem.config import CONFIG
    monkeypatch.delenv("ENGRAM_ENCODE_SERVICE", raising=False)
    # A CORRECT-MODEL reachable daemon → ensure_running is a no-op (daemon_usable True).
    monkeypatch.setattr(
        encode_service, "read_discovery",
        lambda *a, **k: {"model": CONFIG.embedding_model, "host": "127.0.0.1", "port": 1},
    )
    monkeypatch.setattr(encode_service, "is_reachable", lambda *a, **k: True)
    spawned = []
    monkeypatch.setattr(encode_service, "_spawn_detached", lambda: spawned.append(1))
    assert encode_service.ensure_running() is True
    assert spawned == []  # correct-model daemon up → never spawn


def test_ensure_running_spawns_when_daemon_is_wrong_model(monkeypatch, tmp_path):
    """Bug fix (review 2026-06-20): a stale WRONG-MODEL daemon is reachable but useless
    (_encode_via_service rejects it). ensure_running must spawn the correct daemon, not
    treat the wrong-model one as 'already up' (model-blind is_reachable did the latter)."""
    monkeypatch.delenv("ENGRAM_ENCODE_SERVICE", raising=False)
    monkeypatch.setattr(
        encode_service, "read_discovery",
        lambda *a, **k: {"model": "stale-wrong-model", "host": "127.0.0.1", "port": 1},
    )
    monkeypatch.setattr(encode_service, "is_reachable", lambda *a, **k: True)  # reachable, wrong model
    monkeypatch.setattr(encode_service, "_SPAWN_LOCK_PATH", tmp_path / "spawn.lock")
    monkeypatch.setattr(encode_service, "DISCOVERY_PATH", tmp_path / "disco.json")
    spawned = []
    monkeypatch.setattr(encode_service, "_spawn_detached", lambda: spawned.append(1))
    assert encode_service.ensure_running() is False  # wrong-model ≠ up → spawn the correct one
    assert spawned == [1]


def test_ensure_running_spawns_when_unreachable(monkeypatch, tmp_path):
    monkeypatch.delenv("ENGRAM_ENCODE_SERVICE", raising=False)
    monkeypatch.setattr(encode_service, "is_reachable", lambda *a, **k: False)
    monkeypatch.setattr(encode_service, "_SPAWN_LOCK_PATH", tmp_path / "spawn.lock")
    spawned = []
    monkeypatch.setattr(encode_service, "_spawn_detached", lambda: spawned.append(1))
    assert encode_service.ensure_running() is False  # spawned, not yet warm
    assert spawned == [1]


def test_ensure_running_cooldown_blocks_double_spawn(monkeypatch, tmp_path):
    monkeypatch.delenv("ENGRAM_ENCODE_SERVICE", raising=False)
    monkeypatch.setattr(encode_service, "is_reachable", lambda *a, **k: False)
    monkeypatch.setattr(encode_service, "_SPAWN_LOCK_PATH", tmp_path / "spawn.lock")
    spawned = []
    monkeypatch.setattr(encode_service, "_spawn_detached", lambda: spawned.append(1))
    encode_service.ensure_running()  # first → spawns
    encode_service.ensure_running()  # within cooldown → no spawn
    assert spawned == [1]


def test_ensure_running_disabled_by_env(monkeypatch):
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "0")
    spawned = []
    monkeypatch.setattr(encode_service, "_spawn_detached", lambda: spawned.append(1))
    assert encode_service.ensure_running() is False
    assert spawned == []


def test_ensure_running_clears_stale_discovery(monkeypatch, tmp_path):
    monkeypatch.delenv("ENGRAM_ENCODE_SERVICE", raising=False)
    disco = tmp_path / "encode_service.json"
    disco.write_text('{"pid": 1, "port": 1, "host": "127.0.0.1"}', encoding="utf-8")
    monkeypatch.setattr(encode_service, "DISCOVERY_PATH", disco)
    monkeypatch.setattr(encode_service, "_SPAWN_LOCK_PATH", tmp_path / "spawn.lock")
    monkeypatch.setattr(encode_service, "is_reachable", lambda *a, **k: False)
    monkeypatch.setattr(encode_service, "_spawn_detached", lambda: None)
    encode_service.ensure_running()
    assert not disco.exists()  # stale discovery (dead daemon) removed
