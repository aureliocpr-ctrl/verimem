"""SSRF DNS-rebind — END-TO-END proof with a REAL loopback socket.

The monkeypatch tests prove the logic; these prove the wiring against an actual
internal HTTP server. We stand up a real server on 127.0.0.1, point a
"public-looking" hostname at it via a rebinding resolver, and assert the
internal server receives ZERO bytes when the fix is active — i.e. a real SSRF
attack is stopped at the socket, not just in theory.
"""
from __future__ import annotations

import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from verimem import tools_extra

INTERNAL_BODY = b"INTERNAL_SECRET_DO_NOT_LEAK"


@pytest.fixture()
def internal_server():
    """A real HTTP server on 127.0.0.1:<ephemeral> that records every hit."""
    hits = {"n": 0}

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            hits["n"] += 1
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(INTERNAL_BODY)))
            self.end_headers()
            self.wfile.write(INTERNAL_BODY)

        def log_message(self, *a):  # silence
            pass

    server = HTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        yield server, hits
    finally:
        server.shutdown()
        server.server_close()
        t.join(timeout=2)


def _rebind_getaddrinfo(monkeypatch, hostname: str):
    """getaddrinfo: 1st lookup (validation) -> public 1.2.3.4;
    later lookups (connect) -> 127.0.0.1 (the internal server)."""
    real = socket.getaddrinfo
    state = {"n": 0}

    def fake(host, port=None, *a, **k):
        if host == hostname:
            state["n"] += 1
            ip = "1.2.3.4" if state["n"] == 1 else "127.0.0.1"
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port or 0))]
        return real(host, port, *a, **k)

    monkeypatch.setattr(socket, "getaddrinfo", fake)
    return state


def test_real_attack_is_blocked_before_reaching_internal_server(
    monkeypatch, internal_server,
):
    server, hits = internal_server
    port = server.server_address[1]
    monkeypatch.setenv("HIPPO_ENABLE_WEB", "1")
    monkeypatch.delenv("HIPPO_DISABLE_WEB", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    _rebind_getaddrinfo(monkeypatch, "rebind.test")

    res = tools_extra.web_fetch(f"http://rebind.test:{port}/secret")

    assert res.ok is False
    err = (res.error or "").lower()
    assert "ssrf" in err or "blocked" in err, f"not blocked as SSRF: {res.error!r}"
    assert INTERNAL_BODY.decode() not in (res.output or "")
    # The decisive assertion: not one byte reached the internal server.
    assert hits["n"] == 0, "SSRF NOT stopped — the internal server was hit!"


def test_real_attack_via_image_fetch_is_blocked(monkeypatch, internal_server):
    server, hits = internal_server
    port = server.server_address[1]
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    _rebind_getaddrinfo(monkeypatch, "rebind-img.test")

    with pytest.raises(Exception) as ei:
        tools_extra._read_image_to_b64_and_media_type(
            f"http://rebind-img.test:{port}/x.png"
        )
    msg = str(ei.value).lower()
    assert "ssrf" in msg or "blocked" in msg, f"not blocked: {ei.value!r}"
    assert hits["n"] == 0, "SSRF NOT stopped — the internal server was hit!"


def test_legitimate_connection_still_works_through_guard(
    monkeypatch, internal_server,
):
    """The guard backend is really in the connection path AND does not break a
    legitimate fetch: an OLLAMA_HOST-allowlisted loopback host connects for real
    and returns the body."""
    server, hits = internal_server
    port = server.server_address[1]
    monkeypatch.setenv("HIPPO_ENABLE_WEB", "1")
    monkeypatch.setenv("OLLAMA_HOST", f"http://127.0.0.1:{port}")

    res = tools_extra.web_fetch(f"http://127.0.0.1:{port}/ok")

    assert res.ok is True, res.error
    assert INTERNAL_BODY.decode() in res.output
    assert hits["n"] >= 1
