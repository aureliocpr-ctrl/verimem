"""tools_extra.web_fetch behaviour with mocked HTTP via respx.

Covers:
  • 200 OK with HTML stripping
  • 200 OK with non-HTML content (text/plain, JSON) returned verbatim
  • 404 → ok=False
  • 5xx → ok=False
  • Redirect to a normal public host → followed
  • Redirect to a blocked private host → refused
  • max_chars truncation
"""
from __future__ import annotations

import socket as _sock

import pytest
import respx
from httpx import Response

from verimem import tools_extra


@pytest.fixture(autouse=True)
def _enable_web(monkeypatch: pytest.MonkeyPatch):
    """Force-enable web capability for the whole module."""
    monkeypatch.setenv("HIPPO_ENABLE_WEB", "1")
    monkeypatch.delenv("HIPPO_DISABLE_WEB", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)


@pytest.fixture(autouse=True)
def _stub_dns(monkeypatch: pytest.MonkeyPatch):
    """Make 'public-looking' hostnames resolve to a public IP (1.2.3.4) so
    _is_blocked_host doesn't reject them. Real DNS is never hit."""
    public_ip_hosts = {
        "example.com", "www.example.com",
        "anthropic.com", "api.anthropic.com",
        "redirect.example.com", "second.example.com",
    }
    real = _sock.getaddrinfo

    def _fake(host, port, *args, **kwargs):  # noqa: ARG001
        if host in public_ip_hosts:
            return [(_sock.AF_INET, _sock.SOCK_STREAM, 6, "", ("1.2.3.4", 0))]
        return real(host, port, *args, **kwargs)

    monkeypatch.setattr(_sock, "getaddrinfo", _fake)


# ---------------------------------------------------------------------------
# 200 OK
# ---------------------------------------------------------------------------


def test_web_fetch_200_html_strips_tags() -> None:
    html = "<html><body><h1>Title</h1><p>hello world</p></body></html>"
    with respx.mock(assert_all_called=True) as m:
        m.get("https://example.com/").mock(
            return_value=Response(200, text=html,
                                  headers={"content-type": "text/html"}),
        )
        r = tools_extra.web_fetch("https://example.com/")
    assert r.ok is True
    assert "Title" in r.output
    assert "hello world" in r.output
    # Tags must be stripped.
    assert "<h1>" not in r.output
    assert "<p>" not in r.output


def test_web_fetch_200_plain_text_returned_verbatim() -> None:
    body = "no tags here, just plain text\nline 2"
    with respx.mock(assert_all_called=True) as m:
        m.get("https://example.com/raw.txt").mock(
            return_value=Response(200, text=body,
                                  headers={"content-type": "text/plain"}),
        )
        r = tools_extra.web_fetch("https://example.com/raw.txt")
    assert r.ok is True
    assert r.output == body


def test_web_fetch_truncates_to_max_chars() -> None:
    body = "X" * 5000
    with respx.mock(assert_all_called=True) as m:
        m.get("https://example.com/big").mock(
            return_value=Response(200, text=body,
                                  headers={"content-type": "text/plain"}),
        )
        r = tools_extra.web_fetch("https://example.com/big", max_chars=200)
    assert r.ok is True
    assert len(r.output) == 200


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


def test_web_fetch_404_returns_error() -> None:
    with respx.mock() as m:
        m.get("https://example.com/missing").mock(
            return_value=Response(404, text="not found"),
        )
        r = tools_extra.web_fetch("https://example.com/missing")
    assert r.ok is False


def test_web_fetch_5xx_returns_error() -> None:
    with respx.mock() as m:
        m.get("https://example.com/boom").mock(
            return_value=Response(503, text="upstream down"),
        )
        r = tools_extra.web_fetch("https://example.com/boom")
    assert r.ok is False


# ---------------------------------------------------------------------------
# Redirects
# ---------------------------------------------------------------------------


def test_web_fetch_follows_one_safe_redirect() -> None:
    """301 → another public host → fetched."""
    with respx.mock(assert_all_called=True) as m:
        m.get("https://redirect.example.com/").mock(
            return_value=Response(
                301,
                headers={"location": "https://second.example.com/landing",
                         "content-type": "text/html"},
            ),
        )
        m.get("https://second.example.com/landing").mock(
            return_value=Response(200, text="redirected here",
                                  headers={"content-type": "text/plain"}),
        )
        r = tools_extra.web_fetch("https://redirect.example.com/")
    assert r.ok is True
    assert "redirected here" in r.output


def test_web_fetch_refuses_redirect_to_blocked_host() -> None:
    """301 → 169.254.169.254/metadata is the classic AWS SSRF pivot.

    The redirect destination must be re-validated against the SSRF blocker.
    """
    with respx.mock() as m:
        m.get("https://redirect.example.com/").mock(
            return_value=Response(
                302,
                headers={"location": "http://169.254.169.254/latest/meta-data/",
                         "content-type": "text/html"},
            ),
        )
        # The metadata URL must NEVER be requested. We intentionally do not
        # register a mock for it — if the code attempts the request, respx
        # will raise.
        r = tools_extra.web_fetch("https://redirect.example.com/")
    assert r.ok is False
    assert "blocked" in (r.error or "").lower() or "ssrf" in (r.error or "").lower()


def test_web_fetch_user_agent_is_set() -> None:
    """Sanity: we send a custom UA so target servers can identify us."""
    captured = {}
    with respx.mock() as m:
        def _capture(req):
            captured["ua"] = req.headers.get("user-agent", "")
            return Response(200, text="ok",
                            headers={"content-type": "text/plain"})
        m.get("https://example.com/ua").mock(side_effect=_capture)
        tools_extra.web_fetch("https://example.com/ua")
    assert "verimem" in captured["ua"]
