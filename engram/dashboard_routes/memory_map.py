"""Memory-map live dashboard route — feature/memory-map-live.

Tre endpoint:

  • ``GET /memory-map``
        HTML page con un singolo container ``<div id="cy">`` su cui
        ``static/memory_map.js`` monta un Cytoscape force-directed
        grafo dei layer episode ↔ fact ↔ skill.

  • ``GET /api/memory-map/graph``
        JSON envelope ``{nodes, edges, layers, limits, generated_at}``
        — usa ``knowledge_graph_export.export_graph`` per i 3 layer core
        e annota il summary ``layers`` (count per tipo) richiesto dalla UI
        per le checkbox di toggle.

  • ``GET /api/memory-map/events``
        SSE stream che fonde due sorgenti:
        (a) il bus in-process ``observability.BUS`` (eventi del processo
        dashboard stesso),
        (b) il tail del JSONL cross-process ``~/.engram/events.jsonl``
        scritto da ogni ``emit()`` di OGNI istanza HippoAgent (CLI,
        IDE, MCP server, daemon Auto-Dream).

Il design è read-only nella v1: la dashboard "naviga ad occhio" mentre
lo sviluppatore lavora. Mutations restano via MCP tool esistenti
(``hippo_fact_supersede``, ``hippo_fact_forget``, …).
"""
from __future__ import annotations

import asyncio as _a
import json
import queue as _q
import time
from collections import Counter
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from ..event_jsonl_log import tail_events
from ..knowledge_graph_export import export_graph
from ..observability import BUS
from .layout import get_agent, page

_PAGE_BODY = """
<style>
/* Sigma.js Obsidian-like Memory Map styles */
.mm-page-wrapper {
  position: relative;
  width: 100%;
  height: calc(100vh - 60px);
  background: radial-gradient(circle at center, #111114 0%, #000000 100%);
  overflow: hidden;
  margin: -24px -32px; /* Negate app-main padding for full bleed */
  width: calc(100% + 64px);
  height: calc(100vh + 24px); /* fill entire app-content */
}

#sigma-container {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  z-index: 1;
  outline: none;
}

/* Floating Toolbar */
.mm-floating-toolbar {
  position: absolute;
  top: 24px;
  left: 24px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 320px;
  background: rgba(10, 10, 12, 0.75);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.mm-header h1 {
  font-size: 1.3rem; font-weight: 700; margin: 0 0 12px 0;
  color: #fff;
  letter-spacing: -0.02em;
}
.mm-status-badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;
  background: rgba(63, 185, 80, 0.1); color: #3fb950;
  border: 1px solid rgba(63, 185, 80, 0.2);
}

.mm-search-wrap {
  position: relative;
}
.mm-search-wrap .input {
  width: 100%;
  background: rgba(0,0,0,0.5);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  padding: 10px 14px;
  color: #fff;
  font-size: 13px;
  transition: all 0.2s ease;
}
.mm-search-wrap .input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59,130,246,0.25);
  outline: none;
}

.mm-layer-toggles {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: rgba(255,255,255,0.03);
  padding: 12px;
  border-radius: 8px;
}
.mm-layer-toggle {
  display: flex; align-items: center; gap: 10px;
  font-size: 13px; color: #a1a1aa; cursor: pointer;
  transition: color 0.2s;
}
.mm-layer-toggle:hover { color: #fff; }
.mm-layer-toggle input { margin: 0; cursor: pointer; accent-color: #3b82f6; }
.mm-layer-dot {
  width: 10px; height: 10px; border-radius: 50%;
  display: inline-block;
}

.mm-actions {
  display: flex;
  gap: 8px;
}
.mm-actions .btn {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  color: #fff;
}
.mm-actions .btn:hover {
  background: rgba(255,255,255,0.1);
}

.mm-counts {
  font-family: var(--font-mono); font-size: 11px; color: #6b7280;
  margin-top: 4px; text-align: center;
}

/* Floating Detail Panel */
.mm-floating-detail {
  position: absolute;
  top: 24px;
  right: 24px;
  z-index: 10;
  width: 360px;
  max-height: calc(100vh - 48px);
  background: rgba(10, 10, 12, 0.75);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.1);
  overflow-y: auto;
  display: none;
  color: #fff;
}
.mm-floating-detail.visible {
  display: block;
  animation: slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slideIn {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}

/* Detail panel content styling overrides */
#mm-detail hr {
  border-color: rgba(255,255,255,0.1);
  margin: 16px 0;
}
.mm-detail-placeholder {
  color: #6b7280; font-size: 13px; text-align: center;
  padding: 20px 0; display: none;
}

/* Loading Overlay */
#mm-loading {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
  display: flex; flex-direction: column; align-items: center; gap: 16px;
  color: #a1a1aa; font-size: 14px; font-weight: 500; pointer-events: none;
  z-index: 20;
  background: rgba(10,10,12,0.8);
  padding: 32px 48px;
  border-radius: 24px;
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.1);
  box-shadow: 0 20px 40px rgba(0,0,0,0.5);
}
.mm-spinner {
  width: 40px; height: 40px;
  border: 3px solid rgba(255,255,255,0.1);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: mm-spin 1s cubic-bezier(0.5, 0, 0.5, 1) infinite;
}
@keyframes mm-spin { to { transform: rotate(360deg); } }

</style>

<div class="mm-page-wrapper">
  <div id="sigma-container"></div>

  <div id="mm-loading">
    <div class="mm-spinner"></div>
    <span>Rendering Graph...</span>
  </div>

  <div class="mm-floating-toolbar">
    <div class="mm-header">
      <h1>Memory Map</h1>
      <span class="mm-status-badge" id="mm-status">● live</span>
    </div>

    <div class="mm-search-wrap">
      <input id="mm-search" type="search" class="input" placeholder="Search memories..." aria-label="Search">
    </div>

    <div class="mm-layer-toggles">
      <label class="mm-layer-toggle">
        <input type="checkbox" id="mm-layer-episode" checked>
        <span class="mm-layer-dot" style="background:#3b82f6;box-shadow:0 0 8px rgba(59,130,246,0.6);"></span>
        Episodes
      </label>
      <label class="mm-layer-toggle">
        <input type="checkbox" id="mm-layer-fact" checked>
        <span class="mm-layer-dot" style="background:#10b981;box-shadow:0 0 8px rgba(16,185,129,0.6);"></span>
        Facts
      </label>
      <label class="mm-layer-toggle">
        <input type="checkbox" id="mm-layer-skill" checked>
        <span class="mm-layer-dot" style="background:#f59e0b;box-shadow:0 0 8px rgba(245,158,11,0.6);"></span>
        Skills
      </label>
    </div>

    <div class="mm-actions">
      <button id="mm-fit" class="btn btn--sm" type="button" style="flex:1">Recenter</button>
      <button id="mm-reload" class="btn btn--sm" type="button" style="flex:1">Refresh</button>
    </div>

    <div class="mm-counts" id="mm-counts">Loading data...</div>
  </div>

  <div class="mm-floating-detail" id="mm-detail-panel">
    <div id="mm-detail"></div>
  </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/graphology/0.25.4/graphology.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/sigma@2.4.0/build/sigma.min.js"></script>
<script src="/assets/memory_map.js?v=9" defer></script>
"""


def _safe_list(obj: Any, attr: str, *, limit: int) -> list[Any]:
    """Best-effort: get ``obj.<attr>.all()`` slice; ``[]`` on any failure.

    Necessario perché l'agent può esporre differenti store (SkillLibrary,
    EpisodicMemory, SemanticMemory) e i test sostituiscono il singleton
    con un MagicMock minimale.
    """
    try:
        store = getattr(obj, attr, None)
        if store is None:
            return []
        items = store.all() if callable(getattr(store, "all", None)) else []
        return list(items or [])[:limit]
    except Exception:
        return []


def _direct_load(*, limit: int) -> tuple[list[Any], list[Any], list[Any]]:
    """Fallback: instantiate stores directly from CONFIG.

    Used quando ``get_agent()`` fallisce (es. l'agent build chain dipende
    da un LLM provider non disponibile in dashboard-only mode). I 3
    store di lettura non richiedono LLM e sono safe da costruire al volo.
    """
    skills: list[Any] = []
    episodes: list[Any] = []
    facts: list[Any] = []
    try:
        from ..skill import SkillLibrary
        skills = list(SkillLibrary().all() or [])[:limit]
    except Exception:
        pass
    try:
        from ..memory import EpisodicMemory
        episodes = list(EpisodicMemory().all() or [])[:limit]
    except Exception:
        pass
    try:
        from ..semantic import SemanticMemory
        facts = list(SemanticMemory().all() or [])[:limit]
    except Exception:
        pass
    return skills, episodes, facts


def _build_graph(agent: Any, *, limit: int = 300) -> dict[str, Any]:
    """Construct the multi-layer envelope expected by the UI.

    Riusa ``knowledge_graph_export.export_graph`` per i 3 layer core
    (skill, episode, fact) e arricchisce con il summary ``layers``
    (count per tipo) usato dalla UI per le checkbox.

    Due path di lettura:
      • ``agent != None`` → ``agent.skills/.memory/.semantic`` (preserva
        i monkey-patch dei test).
      • ``agent is None`` → costruttori store CONFIG-based (fallback
        runtime quando l'agent build chain solleva eccezioni).
    """
    if agent is None:
        skills, episodes, facts = _direct_load(limit=limit)
    else:
        skills = _safe_list(agent, "skills", limit=limit)
        episodes = _safe_list(agent, "memory", limit=limit)
        facts = _safe_list(agent, "semantic", limit=limit)

    g = export_graph(skills=skills, episodes=episodes, facts=facts)

    # ``knowledge_graph_export.export_graph`` emette edges parent_of anche
    # quando il parent_skill è fuori dal limit di nodi truncati (es. uno
    # skill cita parent_skills che non includiamo nel JSON envelope).
    # Cytoscape solleva ``Can not create edge with nonexistant target``,
    # quindi droppiamo gli edge orphan qui invece di farlo client-side.
    node_ids = {n["id"] for n in g["nodes"]}
    g["edges"] = [
        e for e in g["edges"]
        if e.get("from") in node_ids and e.get("to") in node_ids
    ]
    g["n_edges"] = len(g["edges"])

    layers_count = Counter(n.get("type", "?") for n in g["nodes"])
    # Force-include i 3 layer core anche con count 0, così la UI può
    # mostrare le checkbox in modo stabile (no key-missing flicker).
    layers = {
        "skill": int(layers_count.get("skill", 0)),
        "episode": int(layers_count.get("episode", 0)),
        "fact": int(layers_count.get("fact", 0)),
    }
    g["layers"] = layers
    g["limits"] = {"per_layer": limit}
    g["generated_at"] = time.time()
    return g


def register(app: FastAPI, templates: Jinja2Templates) -> None:  # noqa: ARG001
    @app.get("/memory-map", response_class=HTMLResponse)
    def memory_map_page() -> HTMLResponse:
        return page("Memory map", _PAGE_BODY, full_width=True)

    @app.get("/api/memory-map/graph")
    def memory_map_graph(limit: int = 300) -> JSONResponse:
        # Clamp per evitare query enormi che svuotano la RAM del browser.
        limit_clamped = max(10, min(2000, int(limit)))
        try:
            agent = get_agent()
        except Exception:
            agent = None
        envelope = _build_graph(agent, limit=limit_clamped)
        return JSONResponse(envelope)

    @app.get("/api/memory-map/events")
    def memory_map_events(
        request: Request,
        since: float = 0.0,
        max_seconds: float = 3600.0,
    ) -> StreamingResponse:
        """SSE feed: BUS in-process + JSONL tail cross-process.

        Il client (memory_map.js) ricorda l'ultimo ``ts`` visto e lo
        passa via ``?since=<ts>`` al reconnect per evitare duplicati.

        ``max_seconds`` (default 1h) è un hard-cap server-side: il
        generator si chiude da solo dopo quel tempo, costringendo il
        browser a fare reconnect. Necessario perché ``TestClient`` /
        ``ASGITransport`` non sempre propagano ASGI ``http.disconnect``
        in tempi utili, e senza cap il test SSE blocca.
        """
        q: _q.Queue = _q.Queue(maxsize=2048)

        def listener(evt) -> None:
            try:
                q.put_nowait(evt)
            except _q.Full:
                pass

        BUS.subscribe("*", listener)

        async def gen():
            # try/finally attorno all'INTERO body: il subscriber wildcard va
            # rimosso SEMPRE — alla fine naturale (timeout ``max_seconds``), su
            # CancelledError/GeneratorExit (client disconnect) e su qualunque
            # altra eccezione. Senza il cleanup ogni connessione (e ogni
            # reconnect forzato dal cap ``max_seconds``) accumulava una closure
            # in ``BUS._wildcards``; ``emit()`` itera quella lista process-wide,
            # quindi l'emissione rallentava linearmente e le Queue catturate
            # non venivano mai liberate.
            try:
                # Primo yield → finalizza gli header SSE per il client subito.
                yield ": connected\n\n"
                # Replay JSONL iniziale (catch-up cross-process) dopo gli header.
                try:
                    for rec in tail_events(since_ts=float(since), limit=200):
                        yield f"data: {json.dumps(rec, default=str)}\n\n"
                except Exception:
                    pass

                start_ts = time.time()
                last_jsonl_check = start_ts
                ping_counter = 0
                while time.time() - start_ts < max(0.1, float(max_seconds)):
                    # Drain BUS in-process (non-blocking, bounded burst).
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

                    # Poll JSONL cross-process ~ 1 Hz.
                    now = time.time()
                    if now - last_jsonl_check >= 1.0:
                        try:
                            new_recs = tail_events(
                                since_ts=last_jsonl_check, limit=50
                            )
                            for rec in new_recs:
                                yield f"data: {json.dumps(rec, default=str)}\n\n"
                        except Exception:
                            pass
                        last_jsonl_check = now

                    # Keep-alive ping ~ ogni 15s (150 iter × 0.1s).
                    ping_counter += 1
                    if ping_counter >= 150:
                        yield ": ping\n\n"
                        ping_counter = 0

                    # Cancellation check-point: starlette propaga CancelledError
                    # qui appena il client httpx chiude la connessione.
                    await _a.sleep(0.1)
            except _a.CancelledError:
                # Client disconnesso: uscita pulita, cleanup garantito nel finally.
                return
            finally:
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


__all__ = ["register"]
