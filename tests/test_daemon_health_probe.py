"""Reachability is not health — the arbitration layer must ask the daemon,
not the port.

KNOWN LIMIT declared in ``encode_service._should_idle_exit`` (26/07): "a
daemon wedged behind an accepting socket still looks like a winner", because
``is_reachable`` does connect+close and nothing else. The republish loop
honours such a claimant forever (step-aside), ``daemon_usable`` blesses it for
encode, and after a port reuse an UNRELATED process that accepts connections
keeps the discovery file claimed while nobody serves.

The cure asks the daemon itself: ``ping_healthy`` sends a real ping with a
NONCE over the service framing and requires a well-formed answer within the
timeout — ``ok`` plus the nonce reflected (current builds) or ``ok`` plus a
``model`` field with no nonce echoed (a legacy in-flight daemon that ignores
unknown fields — accepted so one upgrade does not force a model reload; an
impostor speaks neither). ``daemon_usable`` now also trusts the MODEL IN THE
RESPONSE, not the discovery file: the file is written once and can lie in
both directions.

Out of scope, declared: a healthy claimant serving a DIFFERENT model is still
honoured by the republish loop (model-blind arbitration is its own defect
with its own measurement), and the reachability-flapping case from the same
KNOWN LIMIT note stays open.
"""
from __future__ import annotations

import json
import os
import socket
import threading

import pytest

from verimem import encode_service as svc


@pytest.fixture()
def porta_nuda():
    """A socket that ACCEPTS and never answers — the wedged daemon."""
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(8)
    stop = threading.Event()
    tenute = []

    def loop():
        srv.settimeout(0.1)
        while not stop.is_set():
            try:
                c, _ = srv.accept()
                tenute.append(c)          # keep it open, answer nothing
            except OSError:
                continue

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    yield srv.getsockname()[1]
    stop.set()
    for c in tenute:
        c.close()
    srv.close()


def _server_che_risponde(risposta_fn):
    """A fake daemon speaking the real framing; answers via risposta_fn(req)."""
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(8)
    stop = threading.Event()

    def loop():
        srv.settimeout(0.1)
        while not stop.is_set():
            try:
                c, _ = srv.accept()
            except OSError:
                continue
            try:
                req = svc.recv_msg(c)
                svc.send_msg(c, risposta_fn(req))
            except OSError:
                pass
            finally:
                c.close()

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return srv, stop, srv.getsockname()[1]


def test_a_wedged_socket_is_not_healthy(porta_nuda):
    info = {"host": "127.0.0.1", "port": porta_nuda, "pid": 1}
    assert svc.is_reachable(info, timeout=0.4), "sanity: the port DOES accept"
    assert not svc.ping_healthy(info, timeout=0.6), (
        "an accepting socket that never answers the ping is not a daemon")


def test_a_daemon_that_reflects_the_nonce_is_healthy():
    def rispondi(req):
        assert req.get("ping") is True
        return {"ok": True, "model": "m-x", "dim": 3, "pid": os.getpid(),
                "nonce": req.get("nonce")}

    srv, stop, porta = _server_che_risponde(rispondi)
    try:
        assert svc.ping_healthy({"host": "127.0.0.1", "port": porta},
                                timeout=1.0)
    finally:
        stop.set(); srv.close()


def test_an_impostor_that_answers_ok_without_model_is_not_healthy():
    srv, stop, porta = _server_che_risponde(lambda req: {"ok": True})
    try:
        assert not svc.ping_healthy({"host": "127.0.0.1", "port": porta},
                                    timeout=1.0), (
            "ok alone proves nothing: no nonce echo AND no model field")
    finally:
        stop.set(); srv.close()


def test_a_legacy_daemon_without_nonce_reflection_is_healthy():
    """A daemon of the previous build answers the ping with ok+model+pid and
    ignores unknown request fields. Accepted — otherwise the first deploy of
    this probe would evict a healthy resident model for nothing."""
    def legacy(req):
        return {"ok": True, "model": "m-x", "dim": 3, "pid": 1234}

    srv, stop, porta = _server_che_risponde(legacy)
    try:
        assert svc.ping_healthy({"host": "127.0.0.1", "port": porta},
                                timeout=1.0)
    finally:
        stop.set(); srv.close()


def test_daemon_usable_trusts_the_response_not_the_file(monkeypatch):
    """The discovery file says CONFIG's model; the daemon ANSWERS with another
    one. The file is written once — the answer is the truth."""
    from verimem.config import CONFIG

    def bugiardo(req):
        return {"ok": True, "model": "not-the-config-model", "dim": 3,
                "pid": 1, "nonce": req.get("nonce")}

    srv, stop, porta = _server_che_risponde(bugiardo)
    try:
        info = {"host": "127.0.0.1", "port": porta,
                "model": CONFIG.embedding_model}   # the file lies
        assert not svc.daemon_usable(info, timeout=1.0), (
            "usable must compare CONFIG against the RESPONSE's model")
    finally:
        stop.set(); srv.close()


def test_republish_takes_over_a_wedged_claimant(tmp_path, monkeypatch, porta_nuda):
    """Gate-level (the breaker lesson: test the call site, not the helper).
    The discovery file names a claimant whose socket accepts and never
    answers. Today the republish loop steps aside forever; with the health
    probe it must take the file over on the second look."""
    monkeypatch.setattr(svc, "DISCOVERY_PATH", tmp_path / "d.json",
                        raising=False)
    server = svc.EncodeServer(model_name="m-t", encode_fn=lambda t: [1.0],
                              host="127.0.0.1", port=0)
    server._discovery_path = tmp_path / "d.json"
    (tmp_path / "d.json").write_text(json.dumps(
        {"host": "127.0.0.1", "port": porta_nuda, "pid": 999999,
         "model": "m-t"}), encoding="utf-8")
    server._republish_discovery_if_unclaimed()   # 1st look: present-unreadable
    server._republish_discovery_if_unclaimed()   # 2nd look: take it over
    data = json.loads((tmp_path / "d.json").read_text(encoding="utf-8"))
    assert data.get("pid") == os.getpid(), (
        "a wedged claimant (accepts, never answers) kept the file: the "
        "republish loop is still asking the port instead of the daemon")
