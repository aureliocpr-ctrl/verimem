"""Access-audit log for the gateway (2026-07-13, enterprise compliance).

A memory service a company runs needs an append-only trail of WHO accessed WHAT
and WHEN — the substrate for SOC2 / ISO 27001 / GDPR accountability and for
incident forensics. This adds one structured JSONL record per HTTP request:

    {ts, request_id, method, path, status, latency_ms, tenant}

PII/secret-safe BY CONSTRUCTION: it never records the Authorization token, the
query string, request/response bodies, or arbitrary headers — only the fields
above. Records rotate by UTC day so the file never grows unbounded, and the audit
sink can never break a request (its failures are swallowed).

Wired as the OUTERMOST middleware so it captures the final status of every
response — successes, 401s, and the 413 short-circuited by the body-limit guard.
The tenant is read from ``scope['state']`` where the auth dependency stashes the
resolved tenant id (null for unauthenticated liveness).
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

__all__ = ["audit_enabled", "JsonlAuditSink", "AccessAuditMiddleware"]


def audit_enabled(default: bool = True) -> bool:
    """``ENGRAM_GATEWAY_AUDIT_LOG`` overrides the ``create_app`` default. A memory
    SERVICE audits by default (companies expect it); a caller can still opt out."""
    v = os.getenv("ENGRAM_GATEWAY_AUDIT_LOG")
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _utc_day() -> str:
    return time.strftime("%Y%m%d", time.gmtime())


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class JsonlAuditSink:
    """Thread-safe, append-only JSONL writer with per-UTC-day rotation. One line
    per record; opens in append mode so concurrent workers never clobber."""

    def __init__(self, directory: str | Path) -> None:
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def path_for_today(self) -> Path:
        return self.dir / f"access-{_utc_day()}.jsonl"

    def __call__(self, record: dict[str, Any]) -> None:
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        with self._lock:
            with open(self.path_for_today(), "a", encoding="utf-8") as f:
                f.write(line)


class AccessAuditMiddleware:
    """ASGI middleware: emit one access record per HTTP request via ``sink``.
    Never logs secrets; never lets an audit failure break the request."""

    def __init__(self, app: Any, *, sink: Callable[[dict[str, Any]], None]) -> None:
        self.app = app
        self.sink = sink

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        scope.setdefault("state", {})           # the auth dep stashes tenant here
        start = time.monotonic()
        req_id = uuid.uuid4().hex[:16]
        captured = {"status": 0}

        async def send_wrapper(message: Any) -> None:
            if message.get("type") == "http.response.start":
                captured["status"] = int(message.get("status", 0))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            record = {
                "ts": _iso_now(),
                "request_id": req_id,
                "method": scope.get("method"),
                "path": scope.get("path"),          # path only — never the query string
                "status": captured["status"],
                "latency_ms": round((time.monotonic() - start) * 1000.0, 1),
                "tenant": (scope.get("state") or {}).get("tenant"),
            }
            try:
                self.sink(record)
            except Exception:  # noqa: BLE001 — audit must never break the request
                pass
