"""Defensive HTTP security headers on the gateway (2026-07-13, cybersec pass).

A memory gateway an enterprise EXPOSES must not be clickjackable, MIME-sniffable,
or leak referrers by default. The passive recon of the product surface found the
data plane had a body-limit anti-DoS middleware but NO security-header middleware
(the marketing site scored a C for the same reason). These tests assert the
headers land on EVERY response class — unauthenticated liveness, an authenticated
JSON body, an error (401), the served HTML console, and even the 413 from the
body-limit guard — because a header that only shows on the happy path is not a
control.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from verimem.gateway import GatewayKeys, create_app

_EXPECTED = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
    "cross-origin-opener-policy": "same-origin",
}


def _auth(k: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {k}"}


def _app(tmp_path, **kw):
    keys = GatewayKeys(tmp_path / "k.db")
    k = keys.create(tenant_id="alpha", name="a", plan="free")
    return TestClient(create_app(data_dir=tmp_path, keys=keys, **kw)), k


def _assert_headers(resp) -> None:
    for name, value in _EXPECTED.items():
        assert resp.headers.get(name) == value, (
            f"{name!r} missing/wrong on {resp.request.method} "
            f"{resp.request.url.path} -> {resp.status_code}: "
            f"got {resp.headers.get(name)!r}")
    # a CSP is always present; a Permissions-Policy denies powerful features
    assert "frame-ancestors 'none'" in resp.headers.get("content-security-policy", "")
    pp = resp.headers.get("permissions-policy", "")
    assert "camera=()" in pp and "microphone=()" in pp, pp


def test_headers_on_unauthenticated_health(tmp_path):
    client, _ = _app(tmp_path)
    r = client.get("/v1/health")
    assert r.status_code == 200
    _assert_headers(r)


def test_headers_on_authenticated_json(tmp_path):
    client, k = _app(tmp_path)
    r = client.get("/v1/stats", headers=_auth(k))
    assert r.status_code == 200
    _assert_headers(r)


def test_headers_on_error_response(tmp_path):
    """A 401 must still carry the headers — the middleware wraps errors too."""
    client, _ = _app(tmp_path)
    r = client.get("/v1/quota")            # no key -> 401
    assert r.status_code == 401
    _assert_headers(r)


def test_headers_on_html_console(tmp_path):
    client, _ = _app(tmp_path)
    r = client.get("/ui")
    assert r.status_code == 200 and "text/html" in r.headers.get("content-type", "")
    _assert_headers(r)


def test_html_console_gets_the_locked_down_csp(tmp_path):
    """Defense-in-depth against stored-XSS: the HTML console gets a resource-
    restricting CSP (script-src 'self' forbids any injected inline <script>), while
    JSON/API responses get only the anti-clickjacking frame-ancestors."""
    client, k = _app(tmp_path)
    csp_ui = client.get("/ui").headers.get("content-security-policy", "")
    assert "script-src 'self'" in csp_ui and "default-src 'none'" in csp_ui
    csp_json = client.get("/v1/stats", headers=_auth(k)).headers.get(
        "content-security-policy", "")
    assert csp_json == "frame-ancestors 'none'"       # API is not resource-locked
    # the console's own assets must still be loadable under that policy
    assert client.get("/ui/app.js").status_code == 200
    assert client.get("/ui/style.css").status_code == 200


def test_headers_on_body_limit_rejection(tmp_path):
    """The 413 emitted by the anti-DoS body-limit guard (which short-circuits the
    app) must ALSO carry the headers — proves the security middleware is outermost."""
    client, k = _app(tmp_path, max_body_bytes=64)
    r = client.post("/v1/memories", headers=_auth(k),
                    json={"content": "x" * 500, "topic": "t",
                          "verified_by": ["source-doc:d:1"]})
    assert r.status_code == 413
    _assert_headers(r)


def test_middleware_does_not_override_a_stricter_app_header(tmp_path):
    """Additive, not authoritative: if a route sets its own value the middleware
    must not clobber it (future-proofs a route that wants a stricter CSP)."""
    from starlette.responses import PlainTextResponse

    from verimem import gateway as gw
    app = gw.create_app(data_dir=tmp_path)

    @app.get("/_probe_strict")
    def _probe():                     # noqa: ANN202
        return PlainTextResponse(
            "ok", headers={"X-Frame-Options": "SAMEORIGIN"})

    r = TestClient(app).get("/_probe_strict")
    assert r.headers.get("x-frame-options") == "SAMEORIGIN"     # app's value wins
    assert r.headers.get("x-content-type-options") == "nosniff"  # still added
