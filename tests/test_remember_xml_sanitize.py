"""Defensive sanitize per hippo_remember (cycle #70 turno 5 hardening).

Bug reale osservato 2026-05-15 durante loop autonomous: tool invoke
XML malformato (closing tag senza prefix antml:) causa proposition
contaminata da letterali tipo `</parameter>\\n<parameter name="topic">`.
Effetto: fact salvato con proposition spazzata + topic vuoto.

Root cause: client-side format (mio). MA: il server deve essere
RESILIENTE — sanitize la proposition prima del store. Detection
pattern: presenza letterale di `</parameter` o `<parameter name=`
o `</invoke>` nella proposition.
"""
from __future__ import annotations

import json
from typing import Any

import pytest


class _FakeAgent:
    def __init__(self) -> None:
        self.semantic = _FakeSemantic()


class _FakeSemantic:
    def __init__(self) -> None:
        self.stored: list[Any] = []

    def store(self, fact: Any, *, return_replaced: bool = False,
               coherence_hook=None) -> Any:
        # Cycle #125: accept return_replaced + coherence_hook (cycle 119)
        # for back-compat. Original return type was fact.id; keep that
        # only when the caller does NOT request return_replaced.
        _ = coherence_hook
        self.stored.append(fact)
        if return_replaced:
            return False
        return fact.id

    def search_facts(self, *args, **kwargs):
        return []


@pytest.fixture
def fake_agent(monkeypatch: pytest.MonkeyPatch):
    from engram import mcp_server
    a = _FakeAgent()
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a


async def _invoke_tool(
    name: str, arguments: dict[str, Any] | None = None,
) -> list[str]:
    from mcp.types import CallToolRequest, CallToolRequestParams

    from engram import mcp_server

    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    return [c.text for c in payload.content if hasattr(c, "text")]


# ---------- Sanitize tests ------------------------------------------


@pytest.mark.asyncio
async def test_proposition_strips_invoke_closing_xml(
    fake_agent,
) -> None:
    """RED: proposition contaminata con `</invoke>` letterale deve
    essere sanitizzata (tagliata prima del marker)."""
    contaminated = (
        "REGOLA valida fino al marker."
        "\n</invoke>\n<parameter name=\"confidence\">1"
    )
    blocks = await _invoke_tool(
        "hippo_remember", {"proposition": contaminated},
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    # Proposition salvata deve NON contenere XML markers
    stored = payload["proposition"]
    assert "<parameter" not in stored
    assert "</invoke>" not in stored
    assert "</parameter>" not in stored
    # Ma il contenuto utile prima del marker deve essere preservato
    assert "REGOLA valida fino al marker." in stored


@pytest.mark.asyncio
async def test_proposition_strips_parameter_closing_xml(
    fake_agent,
) -> None:
    """RED: proposition contaminata con `</parameter>` letterale +
    tag successivi deve essere sanitizzata."""
    contaminated = (
        "Testo significativo."
        "\n</parameter>\n<parameter name=\"topic\">foo</parameter>"
    )
    blocks = await _invoke_tool(
        "hippo_remember", {"proposition": contaminated},
    )
    payload = json.loads(blocks[0])
    stored = payload["proposition"]
    assert stored == "Testo significativo."


@pytest.mark.asyncio
async def test_proposition_clean_unchanged(fake_agent) -> None:
    """RED: proposition pulita (senza markers XML) deve passare
    invariata. No regressione false-positive sanitize."""
    clean = (
        "REGOLA NON NEGOZIABILE 2026-05-15 con caratteri normali "
        "incluso \"virgolette\" e <symbol> non-XML, percentuali 3%, "
        "parentesi (esempio)."
    )
    blocks = await _invoke_tool(
        "hippo_remember", {"proposition": clean},
    )
    payload = json.loads(blocks[0])
    assert payload["proposition"] == clean


@pytest.mark.asyncio
async def test_proposition_topic_default_recovered_from_prefix(
    fake_agent,
) -> None:
    """RED: se proposition inizia con `[namespace/path]` E topic
    arrivava vuoto (caso tipico del bug originale), il dispatch
    deve estrarre il namespace come topic effettivo, non leave
    topic=''."""
    blocks = await _invoke_tool(
        "hippo_remember",
        {
            "proposition": "[preferences/aurelio/communication] Regola X",
            # topic omesso intenzionalmente
        },
    )
    payload = json.loads(blocks[0])
    assert payload["topic"] == "preferences/aurelio/communication"
    # La proposition è preservata per backward-compat (mostra il prefix)
    assert "Regola X" in payload["proposition"]
