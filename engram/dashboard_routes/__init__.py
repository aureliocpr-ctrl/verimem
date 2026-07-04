"""Per-feature FastAPI route modules for the Engram dashboard.

The legacy `dashboard.py` was a 2,338-LOC monolith mixing HTML, JS, FastAPI
routes, settings logic, and skill mutation. It is now a thin entry-point that
constructs a FastAPI app and delegates to the route packs in this directory.

Public API:
    register_all(app, templates) — wire every route module onto the given app.

Adding a new feature:
    1. create `dashboard_routes/<feature>.py` with a `register(app, templates)`.
    2. add `from . import <feature>` and `<feature>.register(app, templates)`
       inside `register_all`.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

from . import (
    active_memory,
    chat,
    episodes,
    events,
    health,
    lineage,
    memory_map,
    skills,
    welcome,
)
from . import (
    settings as settings_routes,
)


def register_all(app: FastAPI, templates: Jinja2Templates) -> None:
    """Wire every dashboard sub-module onto the given FastAPI app.

    Order matters only for route precedence (FastAPI matches in registration
    order). We register `health` first so /healthz is never shadowed.
    """
    health.register(app, templates)
    welcome.register(app, templates)
    chat.register(app, templates)
    episodes.register(app, templates)
    skills.register(app, templates)
    lineage.register(app, templates)
    active_memory.register(app, templates)
    events.register(app, templates)
    memory_map.register(app, templates)
    settings_routes.register(app, templates)


__all__ = ["register_all"]
