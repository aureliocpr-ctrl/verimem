"""Session-token auth for state-changing dashboard routes (CVE-009).

The dashboard ships with auth DISABLED by default (loopback-only deployment
context). Operators harden by setting `HIPPO_DASHBOARD_AUTH_DISABLED=0`
when binding to non-loopback or running in multi-user contexts.

Token lifecycle:
  • generated lazily on first call to `get_session_token()` (also at app
    startup via `bootstrap_token()` so the token file appears before the
    operator issues any request);
  • persisted to `~/.hippoagent/session.token` mode 0600 on POSIX;
  • can be overridden explicitly via `HIPPO_DASHBOARD_TOKEN`;
  • compared in constant time via `secrets.compare_digest`.

Usage on a route:

    from .auth import verify_session_token

    @app.post("/api/...", dependencies=[Depends(verify_session_token)])
    def my_route(...): ...
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from fastapi import Header, HTTPException

from ..observability import emit

_SESSION_TOKEN: str | None = None


def session_token_path() -> Path:
    # Cycle #41: prefer ~/.engram, fallback to legacy ~/.hippoagent. Honors
    # ENGRAM_DATA_DIR / HIPPO_DATA_DIR overrides via engram._compat.data_dir.
    from engram._compat import data_dir
    return data_dir() / "session.token"


def _generate_session_token() -> str:
    explicit = os.environ.get("HIPPO_DASHBOARD_TOKEN", "").strip()
    if explicit:
        return explicit
    token = secrets.token_urlsafe(32)
    try:
        path = session_token_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        # Cycle #139 (2026-05-18): atomic secure write.
        # The legacy two-step path.write_text() + os.chmod(0o600) had a
        # POSIX TOCTOU race: between the write (default umask, typically
        # 0o644) and the chmod tightening, a local attacker could open
        # the file and read the dashboard session token. Severity LOW
        # (microsecond window, local-only) but trivially preventable —
        # open with mode=0o600 from the start so the broader permission
        # never exists. Windows: ACLs inherit from the private user
        # profile dir, so the legacy path stays.
        if os.name != "nt":
            # Remove a stale file with potentially-wrong mode first so
            # os.open does not silently honour the older permission bits
            # (open(O_CREAT) on an existing file does NOT re-apply mode).
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                pass
            fd = os.open(
                str(path),
                os.O_CREAT | os.O_WRONLY | os.O_TRUNC,
                0o600,
            )
            try:
                os.write(fd, token.encode("utf-8"))
            finally:
                os.close(fd)
        else:
            path.write_text(token, encoding="utf-8")
    except OSError as exc:
        emit("session_token_persist_failed", error=str(exc))
    return token


def get_session_token() -> str:
    """Lazily issue and cache the per-process session token."""
    global _SESSION_TOKEN
    if _SESSION_TOKEN is None:
        _SESSION_TOKEN = _generate_session_token()
    return _SESSION_TOKEN


def reset_session_token() -> None:
    """Test helper — clear the cached token so envs can pick up overrides."""
    global _SESSION_TOKEN
    _SESSION_TOKEN = None


def auth_disabled() -> bool:
    """Cycle #124 (2026-05-17): secure-by-default flip.

    Lab subagent #3 (Security Architect) HIGH risk: previously default
    was "1" (insecure-by-default), so a fresh deployment that bound
    to 0.0.0.0 exposed write endpoints with no auth. Fixed by flipping
    the default to "0" — auth is REQUIRED unless the operator
    explicitly opts out via env var ``HIPPO_DASHBOARD_AUTH_DISABLED=1``.

    Backward compat: explicit "1"/"true"/"yes"/"on" still disables auth
    (dev/local convenience). The warning event below is emitted on every
    bypassed verify so the operator sees it in observability.
    """
    disabled = os.environ.get(
        "HIPPO_DASHBOARD_AUTH_DISABLED", "0",
    ).strip().lower() in ("1", "true", "yes", "on")
    if disabled:
        # Emit a quiet warning so the operator sees that auth is off,
        # even though the bypass was explicit.
        try:
            emit("dashboard_auth_disabled_runtime")
        except Exception:  # noqa: BLE001 — observability must never raise
            pass
    return disabled


def verify_session_token(
    x_hippo_token: str | None = Header(default=None, alias="X-Hippo-Token"),
) -> None:
    """FastAPI dependency: refuse state-changing calls without a valid token."""
    if auth_disabled():
        return
    expected = get_session_token()
    if not x_hippo_token or not secrets.compare_digest(
        str(x_hippo_token), expected,
    ):
        emit("dashboard_auth_rejected", provided=bool(x_hippo_token))
        raise HTTPException(
            status_code=401,
            detail="missing or invalid X-Hippo-Token",
        )


def bootstrap_token() -> str:
    """Force token generation at app startup. Returns the token (never logs it)."""
    return get_session_token()
