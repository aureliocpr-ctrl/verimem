"""/episodes, /episodes/{id} — list + detail with full trajectory."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .layout import get_agent


def register(app: FastAPI, templates: Jinja2Templates) -> None:
    @app.get("/episodes", response_class=HTMLResponse)
    def episodes_page(request: Request):
        a = get_agent()
        eps = a.memory.all(limit=200)
        return templates.TemplateResponse(
            request, "episodes.html",
            {"page_title": "Episodes", "episodes": eps},
        )

    @app.get("/episodes/{episode_id}", response_class=HTMLResponse)
    def episode_detail(request: Request, episode_id: str):
        a = get_agent()
        e = a.memory.get(episode_id)
        if not e:
            for cand in a.memory.all():
                if cand.id.startswith(episode_id):
                    e = cand
                    break
        if not e:
            return HTMLResponse(
                "<!doctype html><html><body><h1>Not found</h1></body></html>",
                status_code=404,
            )
        return templates.TemplateResponse(
            request, "episode_detail.html",
            {
                "page_title": f"Episode {e.id[:8]}",
                "episode": e,
                "trajectory_text": e.trajectory_text(),
            },
        )
