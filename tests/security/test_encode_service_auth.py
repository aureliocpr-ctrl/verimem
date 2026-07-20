"""The local encode service had no request auth (audit F9, LOW→hardening).

The service listens on a loopback socket and encodes whatever text it is sent —
with no token. Any local process could send text to it (a mild CPU-DoS) and,
more to the point, the DISCOVERY file it advertises itself through was unsigned:
a local process could publish its own discovery file first and have clients hand
it their queries and texts in cleartext (model-name matching narrows this, but
does not close it).

Fix: the server mints a per-boot token, writes it into the discovery file at
0600, and requires it on every non-ping request. A client reads the token from
the same file it already trusts for host/port and presents it. Loopback + a
file only this user can read is the trust anchor — a peer without read access to
the discovery file cannot obtain the token.
"""
from __future__ import annotations

import json
import socket
import stat
import threading
import time

import pytest

from verimem import encode_service as svc


@pytest.fixture()
def server(tmp_path):
    disc = tmp_path / "encode_service.json"
    s = svc.EncodeServer(encode_fn=lambda t: [0.1, 0.2, 0.3],
                         host="127.0.0.1", port=0,
                         discovery_path=disc, model_name="test-model",
                         model_dim=3)
    th = threading.Thread(target=s.serve_forever, daemon=True)
    th.start()
    for _ in range(200):
        if disc.exists() and svc.read_discovery(disc):
            break
        time.sleep(0.02)
    yield s, disc
    s.stop()


def _send(disc_info, payload):
    conn = socket.create_connection((disc_info["host"], disc_info["port"]),
                                    timeout=5)
    try:
        svc.send_msg(conn, payload)
        return svc.recv_msg(conn)
    finally:
        conn.close()


def test_discovery_file_carries_a_token(server):
    _s, disc = server
    info = svc.read_discovery(disc)
    assert info.get("token"), "discovery file has no auth token"


def test_discovery_file_is_owner_only(server):
    _s, disc = server
    mode = stat.S_IMODE(disc.stat().st_mode)
    # No group/other bits (POSIX). On Windows st_mode perms are advisory; the
    # assert is a no-op there, and the ACL model is covered by the loopback
    # trust boundary — this pins the POSIX contract.
    import os
    if os.name == "posix":
        assert mode & 0o077 == 0, f"discovery file is group/world readable: {mode:o}"


def test_request_without_token_is_refused(server):
    _s, disc = server
    info = svc.read_discovery(disc)
    resp = _send(info, {"text": "hello"})       # no token
    assert not resp.get("ok"), f"unauthenticated encode succeeded: {resp}"


def test_request_with_wrong_token_is_refused(server):
    _s, disc = server
    info = svc.read_discovery(disc)
    resp = _send(info, {"text": "hello", "token": "wrong"})
    assert not resp.get("ok"), f"bad token accepted: {resp}"


def test_request_with_the_right_token_works(server):
    _s, disc = server
    info = svc.read_discovery(disc)
    resp = _send(info, {"text": "hello", "token": info["token"]})
    assert resp.get("ok") and "vec" in resp, resp


def test_ping_stays_unauthenticated(server):
    """Liveness must not need the token — it reveals nothing sensitive."""
    _s, disc = server
    info = svc.read_discovery(disc)
    resp = _send(info, {"ping": True})
    assert resp.get("ok"), resp
