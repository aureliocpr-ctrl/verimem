"""/lineage, /api/lineage — skill genealogy graph (vis-network)."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from .layout import get_agent, page


def register(app: FastAPI, templates: Jinja2Templates) -> None:  # noqa: ARG001
    @app.get("/lineage", response_class=HTMLResponse)
    def lineage_page() -> HTMLResponse:
        body = """
        <h1>Skill lineage graph</h1>
        <div class="card">
          <p>Nodes are skills (color = status). Edges = "derived from" (REM hybrid or merge).</p>
          <div id="net" style="height: 600px; background: #0a0d12; border-radius: 4px;"></div>
        </div>
        <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <script>
        fetch('/api/lineage').then(r => r.json()).then(data => {
          const colors = { promoted: '#3fb950', candidate: '#d29922', retired: '#8b949e' };
          const nodes = new vis.DataSet(data.nodes.map(n => ({
            id: n.id, label: n.name + '\\n[' + n.stage + '|' + n.status + ']\\nf=' + n.fitness.toFixed(2),
            color: { background: colors[n.status] || '#58a6ff', border: '#30363d' },
            shape: 'box', font: { color: '#0e1116', size: 12 }
          })));
          const edges = new vis.DataSet(data.edges.map(e => ({
            from: e.source, to: e.target, arrows: 'to', color: '#58a6ff',
          })));
          const net = new vis.Network(document.getElementById('net'),
            { nodes, edges },
            { layout: { hierarchical: { direction: 'UD', sortMethod: 'directed' } },
              edges: { smooth: false } });
          net.on('click', p => { if (p.nodes.length) location.href = '/skills/' + p.nodes[0]; });
        });
        </script>
        """
        return page("Lineage", body)

    @app.get("/api/lineage")
    def lineage_data() -> Any:
        a = get_agent()
        g = a.skills.lineage_graph()
        nodes = [{"id": n, **g.nodes[n]} for n in g.nodes()]
        edges = [{"source": u, "target": v, **g.edges[u, v]} for u, v in g.edges()]
        return JSONResponse({"nodes": nodes, "edges": edges})
