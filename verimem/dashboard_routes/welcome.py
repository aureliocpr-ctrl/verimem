"""/, /welcome, /metrics — onboarding splash + main overview + raw metrics page."""
from __future__ import annotations

import json
import time

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .. import settings as user_settings
from ..corpus_health_metrics import corpus_health_metrics
from ..observability import BUS, METRICS
from .layout import get_agent


def _format_event(e) -> dict:
    payload = json.dumps(e.payload, default=str)[:120]
    return {
        "time": time.strftime("%H:%M:%S", time.localtime(e.ts)),
        "name": e.name,
        "payload_short": payload,
    }


def register(app: FastAPI, templates: Jinja2Templates) -> None:
    @app.get("/welcome", response_class=HTMLResponse)
    def welcome_page(request: Request):
        return templates.TemplateResponse(
            request, "welcome.html", {"page_title": "Welcome"},
        )

    @app.get("/", response_class=HTMLResponse)
    def overview(request: Request):
        s = user_settings.load()
        if not s.onboarded:
            return RedirectResponse(url="/welcome", status_code=302)
        return _overview_render(request, templates)

    @app.get("/metrics", response_class=HTMLResponse)
    def metrics_page(request: Request):
        snap = METRICS.snapshot()
        return templates.TemplateResponse(
            request, "metrics.html",
            {
                "page_title": "Metrics",
                "metrics_json": json.dumps(snap, indent=2, default=str),
            },
        )


def _overview_render(request: Request, templates: Jinja2Templates) -> HTMLResponse:
    a = get_agent()
    s = user_settings.load()
    n_eps = a.memory.count()
    n_skills_total = a.skills.count()
    n_skills_promoted = a.skills.count(status="promoted")
    n_skills_candidate = a.skills.count(status="candidate")
    n_facts = a.semantic.count()
    snap = METRICS.snapshot()
    recent = BUS.history(limit=20)

    kpi = {
        "episodes": n_eps,
        "skills_promoted": n_skills_promoted,
        "skills_total": n_skills_total,
        "skills_candidate": n_skills_candidate,
        "facts": n_facts,
        "mode": "sandbox" if s.sandbox_enabled else "open",
        "sandbox_on": s.sandbox_enabled,
        "provider": s.provider,
    }
    try:
        health = corpus_health_metrics(a.semantic)
    except Exception:
        health = {}

    events = [_format_event(e) for e in reversed(recent)]
    return templates.TemplateResponse(
        request, "overview.html",
        {
            "page_title": "Overview",
            "kpi": kpi,
            "health": health,
            "events": events,
            "metrics_json": json.dumps(snap, indent=2, default=str),
        },
    )
