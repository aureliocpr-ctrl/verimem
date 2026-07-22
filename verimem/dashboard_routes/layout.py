"""Shared HTML layout helpers + agent-singleton accessor for dashboard routes.

The split dashboard previously lived as one 2,338-LOC `dashboard.py`. Each
route module under `dashboard_routes/` now owns a coherent slice of the API
and renders pages through the helpers in this module so the chrome (CSS,
nav-bar, page wrapper) stays consistent.
"""
from __future__ import annotations

import html as _html

from fastapi.responses import HTMLResponse

from ..agent import VerimemAgent

# ----- Singleton agent ----------------------------------------------------

_agent: VerimemAgent | None = None


def _build_default_agent() -> VerimemAgent:
    """Default factory; isolated for testability."""
    global _agent
    if _agent is None:
        _agent = VerimemAgent.build()
    return _agent


def get_agent() -> VerimemAgent:
    """Return the in-process VerimemAgent singleton.

    Resolution order:
      1. If `verimem.dashboard._ag` is a callable that does NOT recurse
         back into us, call it. Tests monkey-patch this name to inject a
         MagicMock, so we honour that override at call-time.
      2. Otherwise, lazily build via `VerimemAgent.build()`.

    The redirection allows the legacy `monkeypatch.setattr(dash, "_ag", ...)`
    test fixture to keep working unchanged after the dashboard split.
    """
    try:
        from .. import dashboard as _dash
    except Exception:
        return _build_default_agent()
    fn = getattr(_dash, "_ag", None)
    if callable(fn) and getattr(fn, "__module__", "") not in (__name__, "verimem.dashboard"):
        # The patched _ag must not be our own forwarding stub or this would loop.
        # Tests install lambdas (module = test) or wrap a fake — both are safe.
        try:
            return fn()
        except RecursionError:
            return _build_default_agent()
    return _build_default_agent()


def reset_agent() -> None:
    """Drop the cached singleton (used by tests that monkey-patch _ag)."""
    global _agent
    _agent = None


# ----- HTML helpers -------------------------------------------------------

BASE_CSS = """
<link rel="stylesheet" href="/assets/dashboard.css">
"""

NAV = """
<aside class="app-sidebar" aria-label="Primary">
  <a href="/" class="brand" aria-label="Engram home">
    <span class="logo">E</span>
    Engram Console
  </a>
  <nav class="nav-links">
    <a class="nav-link" href="/">Overview</a>
    <a class="nav-link" href="/facts">Facts</a>
    <a class="nav-link active" href="/memory-map">Graph Map</a>
    <a class="nav-link" href="/episodes">Episodes</a>
    <a class="nav-link" href="/skills">Skills</a>
    <a class="nav-link" href="/lineage">Lineage</a>
    <a class="nav-link" href="/metrics">Metrics</a>
  </nav>
  <div class="sidebar-footer">
    <span class="text-xs" style="color: var(--c-success); font-weight: 500; letter-spacing: 0.5px; text-transform: uppercase;">● LIVE</span>
    <a class="btn btn--ghost btn--sm" href="/settings" aria-label="Settings" style="width: 28px; height: 28px; padding: 0; display: grid; place-items: center; border-radius: 4px;">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="3"></circle>
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
      </svg>
    </a>
  </div>
</aside>
"""


def page(title: str, body: str, full_width: bool = False) -> HTMLResponse:
    """Wrap inner HTML body with the standard <html><head><nav><main> chrome."""
    wrapper = "app-main" if not full_width else "app-main--full"
    return HTMLResponse(
        f"<!doctype html><html lang='en' data-theme='dark'><head><meta charset='utf-8'><title>{title} — Engram</title>"
        + BASE_CSS
        + "</head><body>" + NAV + f"<main class='app-content' id='main'><div class='{wrapper}'>" + body + "</div></main></body></html>"
    )


def html_escape(s: str) -> str:
    """HTML-escape including quotes (CVE-007 / SEC V7 fix).

    The previous implementation did not escape quotes, which allowed
    breakout from HTML attribute contexts (e.g. `<td title="{user_text}">`).
    Now uses the stdlib `html.escape(s, quote=True)`.
    """
    if not s:
        return ""
    return _html.escape(s, quote=True)
