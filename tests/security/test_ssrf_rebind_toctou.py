"""TDD — SSRF DNS-rebinding / TOCTOU (scan-68 follow-up, CVE-006).

`_is_blocked_host()` resolves the hostname via socket.getaddrinfo and checks the
IPs, but httpx then performs a SECOND, independent DNS resolution at connect
time. Between the two lookups the record can change (DNS rebinding): a host that
resolves to a public IP at validation time can resolve to 127.0.0.1 /
169.254.169.254 / RFC1918 at fetch time -> the blocklist is bypassed.

The fix resolves the host ONCE inside the httpx network backend, validates every
resolved address, and connects to the validated IP (pinning) -- so the address
we validate is the address we connect to. This closes the window for both
web_fetch and the vision image fetch (_read_image_to_b64_and_media_type).

Tests are HERMETIC: socket.getaddrinfo is monkeypatched (no real DNS); the
"rebind" target is a closed loopback port so no external traffic occurs even on
the pre-fix code path.
"""
from __future__ import annotations

import socket

import pytest

from verimem import tools_extra
from verimem.tools_extra import _read_image_to_b64_and_media_type, web_fetch


def _rebind_resolver(safe: str = "1.2.3.4", internal: str = "127.0.0.1"):
    """getaddrinfo that returns a SAFE public IP on the first lookup (the
    validation) and an INTERNAL IP on every subsequent lookup (the connect) —
    i.e. the DNS record rebinds between TOCTOU."""
    state = {"n": 0}

    def fake(host, port=None, *args, **kwargs):  # noqa: ARG001
        state["n"] += 1
        ip = safe if state["n"] == 1 else internal
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port or 0))]

    return fake, state


# ---------------------------------------------------------------------------
# Network-backend primitive (hermetic, no sockets at all)
# ---------------------------------------------------------------------------


def test_guard_backend_pins_connection_to_validated_ip(monkeypatch):
    """The connection must target the IP we validated, not the hostname
    (which httpcore would otherwise re-resolve)."""
    seen = {}

    class _FakeInner:
        def connect_tcp(self, host, port, **kw):
            seen["host"] = host
            seen["port"] = port
            return "STREAM"

    def fake_gai(host, port=None, *a, **k):  # noqa: ARG001
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.2.3.4", port or 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_gai)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)

    backend = tools_extra._SSRFGuardBackend(_FakeInner())
    out = backend.connect_tcp("good.example", 443)

    assert out == "STREAM"
    assert seen["host"] == "1.2.3.4", "connection must be pinned to the validated IP"
    assert seen["port"] == 443


def test_guard_backend_blocks_internal_resolution(monkeypatch):
    """If the host resolves to an internal IP, the backend must refuse to
    connect (raise) and never reach the inner backend."""
    class _FakeInner:
        def connect_tcp(self, *a, **k):
            raise AssertionError("must not connect to a blocked address")

    def fake_gai(host, port=None, *a, **k):  # noqa: ARG001
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port or 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_gai)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)

    backend = tools_extra._SSRFGuardBackend(_FakeInner())
    with pytest.raises(Exception) as ei:
        backend.connect_tcp("evil.example", 80)
    msg = str(ei.value).lower()
    assert "ssrf" in msg or "blocked" in msg, f"unexpected error: {ei.value!r}"


def test_guard_backend_refuses_when_host_unresolvable(monkeypatch):
    """If our own resolution fails, the backend must NOT hand the hostname to
    the inner backend (which would re-resolve blindly = the TOCTOU we close).
    It must raise and never connect."""
    called = {"inner": False}

    class _FakeInner:
        def connect_tcp(self, *a, **k):
            called["inner"] = True
            return "STREAM"

    def boom_gai(host, port=None, *a, **k):  # noqa: ARG001
        raise socket.gaierror("name resolution failed")

    monkeypatch.setattr(socket, "getaddrinfo", boom_gai)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)

    backend = tools_extra._SSRFGuardBackend(_FakeInner())
    with pytest.raises(Exception):
        backend.connect_tcp("flaky.example", 443)
    assert called["inner"] is False, "must NOT delegate an unvalidated hostname"


def test_guard_backend_honours_ollama_allowlist(monkeypatch):
    """An OLLAMA_HOST-allowlisted host passes through unchanged (not pinned,
    not blocked) even though it points at loopback."""
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    seen = {}

    class _FakeInner:
        def connect_tcp(self, host, port, **kw):
            seen["host"] = host
            return "S"

    backend = tools_extra._SSRFGuardBackend(_FakeInner())
    backend.connect_tcp("localhost", 11434)
    assert seen["host"] == "localhost", "allowlisted host must pass through unchanged"


# ---------------------------------------------------------------------------
# End-to-end: web_fetch and the vision image fetch must block the rebind
# ---------------------------------------------------------------------------


def test_web_fetch_blocks_dns_rebind_at_connect(monkeypatch):
    """Validation sees a public IP; the connect-time lookup rebinds to
    loopback. web_fetch must still block it as SSRF."""
    monkeypatch.setenv("HIPPO_ENABLE_WEB", "1")
    monkeypatch.delenv("HIPPO_DISABLE_WEB", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    fake, _ = _rebind_resolver()
    monkeypatch.setattr(socket, "getaddrinfo", fake)

    # port 1 is a closed loopback port: even pre-fix code cannot leak data.
    res = web_fetch("http://rebind.example:1/secret")
    assert res.ok is False
    err = (res.error or "").lower()
    assert "ssrf" in err or "blocked" in err, f"rebind not blocked: {res.error!r}"


def test_read_image_blocks_dns_rebind_at_connect(monkeypatch):
    """Same rebind, via the vision image fetch path."""
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    fake, _ = _rebind_resolver()
    monkeypatch.setattr(socket, "getaddrinfo", fake)

    with pytest.raises(Exception) as ei:
        _read_image_to_b64_and_media_type("http://rebind.example:1/x.png")
    msg = str(ei.value).lower()
    assert "ssrf" in msg or "blocked" in msg, f"rebind not blocked: {ei.value!r}"
