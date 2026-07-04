"""/events page + /api/events/recent + /api/events/stream (Server-Sent Events)."""
from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from ..observability import BUS
from .layout import page


def register(app: FastAPI, templates: Jinja2Templates) -> None:  # noqa: ARG001
    @app.get("/events")
    def events_page() -> HTMLResponse:
        body = """
        <h1>Events <span id="evt-status" style="color:var(--ok);font-size:13px;
          font-weight:400;border:1px solid var(--ok);padding:2px 8px;border-radius:10px;">
          ● live</span></h1>
        <div class="card">
          <p style="color:var(--dim);font-size:13px;margin:0 0 8px 0;">
            Live event stream. Newest at the top. Streamed via Server-Sent Events.
          </p>
          <div style="display:flex;gap:8px;margin-bottom:8px;align-items:center;">
            <input id="evt-filter" placeholder="filter by name/payload…"
              style="flex:1;background:#0a0d12;color:var(--text);border:1px solid #30363d;
                     border-radius:4px;padding:6px 10px;">
            <button id="evt-clear" style="background:#21262d;color:var(--text);
              border:1px solid #30363d;padding:6px 14px;border-radius:4px;cursor:pointer;">
              Clear</button>
            <button id="evt-pause" style="background:#21262d;color:var(--text);
              border:1px solid #30363d;padding:6px 14px;border-radius:4px;cursor:pointer;">
              Pause</button>
          </div>
          <table>
            <thead><tr><th>time</th><th>event</th><th>payload</th></tr></thead>
            <tbody id="evt-tbody"></tbody>
          </table>
        </div>
        <script src="/static/events.js" defer></script>
        """
        return page("Events", body)

    @app.get("/api/events/recent")
    def events_recent(limit: int = 100) -> JSONResponse:
        items = BUS.history(limit=limit)
        return JSONResponse({
            "events": [{"name": e.name, "payload": e.payload, "ts": e.ts} for e in items],
        })

    @app.get("/api/events/stream")
    def events_stream(max_seconds: float = 3600.0) -> Any:
        """Server-Sent Events: pushes new events as they're emitted on the bus.

        audit#3-r3 R0: this endpoint previously (a) LEAKED its wildcard
        subscriber — ``BUS.subscribe("*", listener)`` with no finally/unsubscribe
        — so every connect (and every forced browser reconnect) appended a
        closure to ``BUS._wildcards`` that ``emit()`` iterates process-wide:
        emit latency + RAM grew linearly with every dashboard open/refresh
        (unauthenticated -> trivial slow-burn DoS); and (b) drove the stream
        with a SYNCHRONOUS ``q.get(timeout=15)`` inside the async generator,
        which blocks the whole asyncio event loop for up to 15s per idle
        connection and never self-terminates (no ``max_seconds`` cap).

        Rewritten to mirror the proven memory_map.py SSE endpoint:
          * bounded non-blocking drain (``get_nowait`` + ``await asyncio.sleep``)
            keeps the event loop free and gives Starlette a checkpoint to deliver
            ``CancelledError`` on client disconnect;
          * a server-side ``max_seconds`` hard cap so the generator ALWAYS
            self-terminates (forces a clean browser reconnect; also lets the SSE
            test drain to a natural end instead of hanging);
          * a try/finally that ALWAYS unsubscribes the wildcard listener.
        """
        import asyncio as _a
        import queue as _q
        import time as _t

        from fastapi.responses import StreamingResponse

        # Bounded queue: a stalled SSE client cannot grow RAM without limit
        # (put_nowait drops once full).
        q: _q.Queue = _q.Queue(maxsize=2048)

        def listener(evt):
            try:
                q.put_nowait(evt)
            except _q.Full:
                pass

        BUS.subscribe("*", listener)

        async def gen():
            try:
                yield ": connected\n\n"
                start_ts = _t.time()
                ping_counter = 0
                while _t.time() - start_ts < max(0.1, float(max_seconds)):
                    # Non-blocking, bounded burst drain of the in-process bus.
                    for _ in range(50):
                        try:
                            evt = q.get_nowait()
                        except _q.Empty:
                            break
                        payload = json.dumps(
                            {
                                "name": evt.name,
                                "payload": evt.payload,
                                "ts": evt.ts,
                            },
                            default=str,
                        )
                        yield f"data: {payload}\n\n"

                    # Keep-alive ping ~ every 15s (150 iters x 0.1s).
                    ping_counter += 1
                    if ping_counter >= 150:
                        yield ": ping\n\n"
                        ping_counter = 0

                    # Cancellation check-point: Starlette raises CancelledError
                    # here as soon as the httpx client closes the connection.
                    await _a.sleep(0.1)
            except _a.CancelledError:
                # Client disconnected: clean exit, cleanup guaranteed in finally.
                return
            finally:
                # ALWAYS remove the wildcard subscriber — on the max_seconds
                # timeout, on CancelledError (client disconnect), and on any
                # other exception. This is the leak fix.
                BUS.unsubscribe("*", listener)

        return StreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )
