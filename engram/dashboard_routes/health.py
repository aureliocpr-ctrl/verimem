"""/healthz — liveness probe."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates


def register(app: FastAPI, templates: Jinja2Templates) -> None:  # noqa: ARG001
    @app.get("/healthz", include_in_schema=False)
    def healthz() -> JSONResponse:
        return JSONResponse({"status": "ok"})
