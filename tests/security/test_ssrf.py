"""SSRF defense tests for tools_extra.web_fetch / _is_blocked_host.

Covers Sprint 1 hardening (CVE-006 / SEC V10):

  • _is_blocked_host returns True for loopback / RFC1918 / link-local /
    AWS metadata addresses
  • _is_blocked_host returns False for normal public domains (we mock DNS
    so the test stays offline)
  • web_fetch refuses blocked hosts before issuing any HTTP request
  • OLLAMA_HOST allowlist is honoured (loopback is OK iff the user has
    explicitly pointed OLLAMA_HOST at it)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem import tools_extra

# ---------------------------------------------------------------------------
# _is_blocked_host — direct host-name / IP literal checks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("host", [
    "127.0.0.1", "::1",                 # loopback
    "10.0.0.1", "10.255.255.255",       # RFC1918 10/8
    "192.168.1.1", "192.168.0.42",      # RFC1918 192.168/16
    "172.16.0.1", "172.20.5.5",         # RFC1918 172.16/12
    "169.254.169.254",                  # AWS / GCP / Azure metadata
    "169.254.0.1",                      # IPv4 link-local
    "fe80::1",                          # IPv6 link-local
    "0.0.0.0",                          # unspecified
    "224.0.0.1",                        # multicast
])
def test_is_blocked_host_blocks_internal_ips(host: str) -> None:
    assert tools_extra._is_blocked_host(host) is True, f"expected blocked: {host}"


def test_is_blocked_host_blocks_empty_host() -> None:
    """Empty hostname is treated as blocked (defensive default)."""
    assert tools_extra._is_blocked_host("") is True


def test_is_blocked_host_allows_public_ip() -> None:
    """A public, non-special IP literal must pass."""
    # 8.8.8.8 is Google DNS — public, not in any blocked range.
    assert tools_extra._is_blocked_host("8.8.8.8") is False


def test_is_blocked_host_allows_public_hostname(monkeypatch: pytest.MonkeyPatch) -> None:
    """Public hostnames (mocked DNS) must pass.

    We mock `socket.getaddrinfo` so the test runs offline. The mock returns
    a public IP (1.2.3.4) for `example.com`.
    """
    import socket as _sock

    def _fake_getaddrinfo(host, port, *args, **kwargs):  # noqa: ARG001
        if host in ("google.com", "anthropic.com", "example.com"):
            return [(_sock.AF_INET, _sock.SOCK_STREAM, 6, "",
                     ("1.2.3.4", 0))]
        return _sock.getaddrinfo(host, port, *args, **kwargs)

    monkeypatch.setattr(_sock, "getaddrinfo", _fake_getaddrinfo)
    assert tools_extra._is_blocked_host("google.com") is False
    assert tools_extra._is_blocked_host("anthropic.com") is False
    assert tools_extra._is_blocked_host("example.com") is False


def test_is_blocked_host_blocks_dns_rebind(monkeypatch: pytest.MonkeyPatch) -> None:
    """If DNS resolves a 'public-looking' hostname to a private IP,
    the blocker must catch it (DNS rebinding defense)."""
    import socket as _sock

    def _evil_getaddrinfo(host, port, *args, **kwargs):  # noqa: ARG001
        return [(_sock.AF_INET, _sock.SOCK_STREAM, 6, "", ("127.0.0.1", 0))]

    monkeypatch.setattr(_sock, "getaddrinfo", _evil_getaddrinfo)
    assert tools_extra._is_blocked_host("definitely-not-loopback.example") is True


# ---------------------------------------------------------------------------
# OLLAMA_HOST allowlist
# ---------------------------------------------------------------------------


def test_ollama_host_allowlist_permits_explicit_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    """If OLLAMA_HOST is set to a loopback URL, that exact hostname is allowed.

    Rationale: the user has *explicitly* pointed Ollama at a loopback
    address, so a single-host carve-out is acceptable.
    """
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    # localhost is normally blocked, but allowlist via OLLAMA_HOST permits it.
    assert tools_extra._is_blocked_host("localhost") is False


def test_ollama_host_allowlist_does_not_open_other_loopbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OLLAMA_HOST=http://localhost:... must NOT also unblock 127.0.0.1.

    Allowlist matches by exact hostname only. Defence-in-depth.
    """
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    assert tools_extra._is_blocked_host("127.0.0.1") is True


# ---------------------------------------------------------------------------
# web_fetch — refuses blocked destinations BEFORE issuing HTTP
# ---------------------------------------------------------------------------


def test_web_fetch_refuses_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    """web_fetch on a loopback URL must short-circuit with an SSRF error."""
    monkeypatch.setenv("HIPPO_ENABLE_WEB", "1")
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    result = tools_extra.web_fetch("http://127.0.0.1:8080/admin")
    assert result.ok is False
    assert "ssrf" in (result.error or "").lower() or "blocked" in (result.error or "").lower()


def test_web_fetch_refuses_aws_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    """The AWS / GCP / Azure metadata service URL must be hard-blocked."""
    monkeypatch.setenv("HIPPO_ENABLE_WEB", "1")
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    result = tools_extra.web_fetch("http://169.254.169.254/latest/meta-data/")
    assert result.ok is False
    assert "ssrf" in (result.error or "").lower() or "blocked" in (result.error or "").lower()


def test_web_fetch_refuses_rfc1918(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HIPPO_ENABLE_WEB", "1")
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    result = tools_extra.web_fetch("http://192.168.1.1/")
    assert result.ok is False
    assert "ssrf" in (result.error or "").lower() or "blocked" in (result.error or "").lower()


def test_web_fetch_refuses_non_http_scheme(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HIPPO_ENABLE_WEB", "1")
    result = tools_extra.web_fetch("file:///etc/passwd")
    assert result.ok is False


def test_web_fetch_refuses_when_capability_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """When HIPPO_ENABLE_WEB is explicitly off, web_fetch is disabled
    regardless of host."""
    monkeypatch.setenv("HIPPO_ENABLE_WEB", "0")
    monkeypatch.setenv("HIPPO_DISABLE_WEB", "1")
    result = tools_extra.web_fetch("https://anthropic.com")
    assert result.ok is False
    assert "disabled" in (result.error or "").lower()
