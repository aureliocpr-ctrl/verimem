"""Static assets for the Verimem trust console (``GET /ui``).

The product's FACE: one self-contained page (odometer + navigable knowledge
graph with chain of custody + blocked-claims log) served by the gateway.
Plain files inside the wheel — no build step, no CDN, no template engine;
the same security property as ``/dashboard``: the page is static by
construction, every number arrives only via the browser's authenticated
fetch, the bearer key lives in sessionStorage.
"""
from __future__ import annotations

from functools import lru_cache
from importlib import resources

#: extension → content-type for the few asset kinds we ship.
MEDIA_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}


@lru_cache(maxsize=None)
def asset(name: str) -> str:
    """Read one packaged asset (cached — the files are immutable at runtime)."""
    return (resources.files(__name__) / name).read_text(encoding="utf-8")


def media_type(name: str) -> str:
    for ext, mt in MEDIA_TYPES.items():
        if name.endswith(ext):
            return mt
    return "application/octet-stream"


__all__ = ["asset", "media_type", "MEDIA_TYPES"]
