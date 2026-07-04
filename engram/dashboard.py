"""FastAPI Engram dashboard — thin entry-point.

This module is intentionally short. The 2,338-LOC monolith was split into
the `dashboard_routes/` package (one file per feature) plus static JS files
under `static/`. This file:

- builds the FastAPI app,
- mounts the IDE router and the `/static` and `/assets` directories,
- serves `chat.js`, `settings.js`, `events.js` from `static/` for backward
  compatibility with the original `/static/<x>.js` URLs,
- delegates every other route to `dashboard_routes.register_all(app, templates)`.

Backward compatibility:
- `from engram.dashboard import app` — still works (tests rely on it).
- `from engram.dashboard import PRESETS` — re-exported (tui.py relies on it).

Security (CVE-009):
- Locked CORS allowlist (loopback origins only).
- `dashboard_routes.auth.bootstrap_token()` runs at startup so the session
  token file appears at `~/.hippoagent/session.token` before any request.
"""
from __future__ import annotations

import sys as _sys
import types as _types
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .dashboard_routes import auth as _dash_auth
from .dashboard_routes import layout as _dash_layout
from .dashboard_routes import register_all
from .dashboard_routes.settings import PRESETS  # re-export for tui.py
from .ide import ide_html, ide_js
from .ide import router as ide_router

__all__ = ["app", "PRESETS", "_ag", "_agent",
           "verify_session_token", "get_session_token",
           "_session_token_path", "_auth_disabled"]


# ---- Backward-compat shims (tests / tui rely on these symbols) ----------
# Pre-split the singleton was `dashboard._ag()` returning `dashboard._agent`.
# Tests monkey-patch both names; we forward to the new layout module.
_agent = None  # tests monkey-patch this attribute


def _ag():
    """Legacy accessor for the FastAPI singleton agent.

    Kept so tests that do `monkeypatch.setattr(dash, "_ag", lambda: fake)`
    keep working. Internal route code uses `layout.get_agent()` directly.
    """
    return _dash_layout.get_agent()


# Re-export auth helpers so existing tests / monkeypatches continue to work.
verify_session_token = _dash_auth.verify_session_token
get_session_token = _dash_auth.get_session_token
_session_token_path = _dash_auth.session_token_path
_auth_disabled = _dash_auth.auth_disabled


# `_SESSION_TOKEN` lived as a module attribute *and* as a never-installed
# descriptor class — the descriptor pattern doesn't work on module-level
# names, so the previous shim was dead code. We expose the canonical token
# location (`dashboard_routes.auth._SESSION_TOKEN`) via PEP-562 module-level
# `__getattr__` and `__setattr__` so legacy `monkeypatch.setattr(dash,
# "_SESSION_TOKEN", v)` calls actually flip the real binding instead of
# silently writing to a dead module attribute.

_SESSION_TOKEN_ATTR = "_SESSION_TOKEN"


def __getattr__(name: str):
    if name == _SESSION_TOKEN_ATTR:
        return _dash_auth._SESSION_TOKEN
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Note: monkeypatch.setattr operates via setattr(module, name, value), which
# bypasses __setattr__ on module objects in CPython. To make the legacy test
# pattern work we also re-route it through the auth module by registering a
# property on the ModuleType subclass.
class _DashboardModule(_types.ModuleType):
    """Module class that mirrors `_SESSION_TOKEN` access onto auth module.

    Subclassing ModuleType is the *correct* way to give a module attribute
    a descriptor. Setting `__class__` on the module instance installs it.
    """

    def __getattribute__(self, name: str):
        if name == _SESSION_TOKEN_ATTR:
            return _dash_auth._SESSION_TOKEN
        return super().__getattribute__(name)

    def __setattr__(self, name: str, value: object) -> None:
        if name == _SESSION_TOKEN_ATTR:
            _dash_auth._SESSION_TOKEN = value  # type: ignore[assignment]
            return
        super().__setattr__(name, value)


_sys.modules[__name__].__class__ = _DashboardModule


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    _dash_auth.bootstrap_token()
    yield


app = FastAPI(title="Engram Dashboard", lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8765",
        "http://localhost:8765",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Hippo-Token"],
)
app.include_router(ide_router)


@app.get("/api/auth/info", include_in_schema=False)
def auth_info() -> JSONResponse:
    """Diagnostic: surfaces whether auth is enforced and where the token lives.

    Never returns the token itself — operators read it from the on-disk file.
    """
    return JSONResponse({
        "auth_required": not _dash_auth.auth_disabled(),
        "token_file": str(_dash_auth.session_token_path()),
    })

# --- Static + templates ---------------------------------------------------
# Mounted under /assets (NOT /static) so the legacy `@app.get("/static/*.js")`
# routes — chat.js, settings.js, events.js, ide.js — keep working untouched.
_PKG_DIR = Path(__file__).resolve().parent
_STATIC_DIR = _PKG_DIR / "static"
app.mount(
    "/assets",
    StaticFiles(directory=str(_STATIC_DIR)),
    name="assets",
)
templates = Jinja2Templates(directory=str(_PKG_DIR / "templates"))


def _read_static(name: str) -> str:
    return (_STATIC_DIR / name).read_text(encoding="utf-8")


@app.get("/ide", response_class=HTMLResponse)
def ide_page() -> HTMLResponse:
    return HTMLResponse(ide_html())


@app.get("/static/ide.js")
def ide_js_route() -> Response:
    return Response(content=ide_js(), media_type="application/javascript")


@app.get("/static/chat.js")
def chat_js() -> Response:
    return Response(content=_read_static("chat.js"), media_type="application/javascript")


@app.get("/static/settings.js")
def settings_js() -> Response:
    return Response(content=_read_static("settings.js"), media_type="application/javascript")


@app.get("/static/events.js")
def events_js() -> Response:
    return Response(content=_read_static("events.js"), media_type="application/javascript")


# Wire every feature route module onto the app.
register_all(app, templates)
