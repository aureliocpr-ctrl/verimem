"""LIVE wiring — buco #2: il gate evidence-existence e' attivo sul PATH REALE
(handler MCP hippo_remember), non solo opt-in nei test del gate.

Prima del wiring: mcp_server passava il gate SENZA repo_root -> format-only ->
un commit:deadbeef fabbricato faceva persistere (model_claim) anche end-to-end.
Dopo: mcp_server passa repo_root=a.semantic.repo_root (= CONFIG.project_root via
agent.build) -> il gate verifica l'ESISTENZA -> commit fabbricato -> quarantined.

HERMETIC per lo storage: SemanticMemory su tmp_path. REALE per la verifica git:
repo_root = la repo HippoAgent (git), dove HEAD esiste e 'deadbeef' no.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from verimem import mcp_server
from verimem.semantic import SemanticMemory


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


class _FakeAgent:
    def __init__(self, sm: SemanticMemory) -> None:
        self.semantic = sm


async def _invoke(name: str, arguments: dict[str, Any]):
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    return json.loads(
        [c.text for c in payload.content if hasattr(c, "text")][0]
    )


def _sm(tmp_path) -> SemanticMemory:
    # repo_root = repo git reale -> il gate puo' fare git rev-parse.
    return SemanticMemory(db_path=tmp_path / "sm.db", repo_root=_repo_root())


async def test_fabricated_commit_quarantined_via_mcp(tmp_path, monkeypatch):
    sm = _sm(tmp_path)
    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent(sm))

    out = await _invoke("hippo_remember", {
        "proposition": "SHIPPED il modulo di auth",
        "topic": "project/x",
        "verified_by": ["commit:deadbeef", "pytest:test_auth_PASS"],
        "validate": "fast",
    })
    assert out.get("status") == "quarantined", (
        f"commit fabbricato deve essere quarantined sul path reale: {out}"
    )
    assert any(
        w.get("evidence_existence") for w in out.get("anti_confab_warnings", [])
    ), f"deve emettere il warning evidence-existence: {out}"


async def test_real_commit_persists_via_mcp(tmp_path, monkeypatch):
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(_repo_root()),
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    sm = _sm(tmp_path)
    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent(sm))

    out = await _invoke("hippo_remember", {
        "proposition": "SHIPPED il modulo di auth",
        "topic": "project/x",
        "verified_by": [f"commit:{head}"],
        "validate": "fast",
    })
    assert out.get("status") != "quarantined", (
        f"un commit reale ({head[:12]}) non deve essere quarantined: {out}"
    )
