"""P2.c — RED test OpenIE LLM-based entity & triple extraction.

Spec: docs/specs/p2c-openie-extraction.md.

Pattern HippoRAG 2-step (NER → triple) MA con json.loads strict e
zero parser code-execution sull'output LLM. Fake LLM produced via
MockLLM (engram.llm.MockLLM) scripted con stringhe JSON realistiche.

Anti-pattern test fake-friendly (lezione cycle #70 P1): il MockLLM
ritorna stringhe come farebbero LLM reali, incluso JSON malformato
nei test di robustezza. NO scorciatoie type-checked: il parser
deve davvero fare json.loads strict.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

# ---------- Unit: parser helpers ----------------------------------


def test_parse_ner_response_valid_json() -> None:
    """RED: input JSON valido con campo entities → lista."""
    from engram.openie import _parse_ner_response

    payload = json.dumps({
        "entities": [
            {"name": "Tonegawa", "type": "person",
             "aliases": ["S. Tonegawa"]},
            {"name": "MIT", "type": "org"},
        ],
    })
    out = _parse_ner_response(payload)
    assert isinstance(out, list)
    assert len(out) == 2
    assert out[0]["name"] == "Tonegawa"
    assert out[0]["type"] == "person"
    assert out[0]["aliases"] == ["S. Tonegawa"]
    assert out[1]["name"] == "MIT"


def test_parse_ner_response_malformed_json_returns_empty() -> None:
    """RED: input non-JSON o JSON malformato → lista vuota,
    NO eccezione, NO parser code-execution."""
    from engram.openie import _parse_ner_response

    # JSON malformato: virgola mancante
    assert _parse_ner_response('{"entities": [{"name": "X"}') == []
    # Non JSON puro: code injection attempt
    assert _parse_ner_response("__import__('os').system('rm')") == []
    # JSON valido ma struttura sbagliata (no "entities" key)
    assert _parse_ner_response('{"foo": "bar"}') == []
    # Stringa vuota
    assert _parse_ner_response("") == []
    # JSON con entities non lista
    assert _parse_ner_response('{"entities": "not a list"}') == []


def test_parse_triple_response_drops_unknown_entities() -> None:
    """RED: triple con subject/object NON nelle known_entities
    devono essere droppate. Solo triple con entrambe conosciute
    passano. Anti-confabulation LLM: l'LLM non può inventare
    entità nuove nella fase triple."""
    from engram.openie import _parse_triple_response

    payload = json.dumps({
        "triples": [
            {"subject": "Tonegawa", "predicate": "works_at",
             "object": "MIT", "confidence": 0.95},
            {"subject": "Tonegawa", "predicate": "discovered",
             "object": "UNKNOWN_ENTITY", "confidence": 0.85},
            {"subject": "MARGHERITA", "predicate": "is_a",
             "object": "MIT", "confidence": 0.7},
        ],
    })
    known = {"Tonegawa", "MIT"}
    out = _parse_triple_response(payload, known)
    assert len(out) == 1
    assert out[0]["subject"] == "Tonegawa"
    assert out[0]["object"] == "MIT"
    assert out[0]["predicate"] == "works_at"
    assert out[0]["confidence"] == 0.95


def test_parse_triple_response_malformed_returns_empty() -> None:
    """RED: triple parsing robust su JSON malformed."""
    from engram.openie import _parse_triple_response

    assert _parse_triple_response("not json", {"X"}) == []
    assert _parse_triple_response('{"triples": "no"}', {"X"}) == []
    assert _parse_triple_response("", {"X"}) == []


# ---------- extract_entities end-to-end ---------------------------


def test_extract_entities_ner_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """RED: mode='ner_only' invoca SOLO step 1 (1 LLM call).
    Ritorna entities, triples=[]. MockLLM scripted con NER JSON."""
    from engram.llm import MockLLM
    from engram.openie import extract_entities

    ner_json = json.dumps({
        "entities": [
            {"name": "Tonegawa", "type": "person"},
            {"name": "MIT", "type": "org"},
        ],
    })
    mock = MockLLM(scripted=[ner_json])
    out = extract_entities(
        text="Tonegawa works at MIT.", llm=mock, mode="ner_only",
    )
    assert len(out["entities"]) == 2
    assert {e["name"] for e in out["entities"]} == {"Tonegawa", "MIT"}
    assert out["triples"] == []
    # 1 sola LLM call (NER)
    assert len(mock.calls) == 1


def test_extract_entities_ner_plus_triple(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RED: mode='ner+triple' invoca 2 LLM call (NER poi triple).
    Triple validate contro entità step 1."""
    from engram.llm import MockLLM
    from engram.openie import extract_entities

    ner_json = json.dumps({
        "entities": [
            {"name": "Tonegawa", "type": "person"},
            {"name": "MIT", "type": "org"},
        ],
    })
    triple_json = json.dumps({
        "triples": [
            {"subject": "Tonegawa", "predicate": "works_at",
             "object": "MIT", "confidence": 0.95},
        ],
    })
    mock = MockLLM(scripted=[ner_json, triple_json])
    out = extract_entities(
        text="Tonegawa works at MIT.", llm=mock, mode="ner+triple",
    )
    assert len(out["entities"]) == 2
    assert len(out["triples"]) == 1
    assert out["triples"][0]["subject"] == "Tonegawa"
    assert out["triples"][0]["object"] == "MIT"
    assert out["triples"][0]["predicate"] == "works_at"
    # 2 LLM call (NER + triple)
    assert len(mock.calls) == 2


def test_extract_entities_existing_dedup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RED: existing_entities passato come hint nel prompt. Anche se
    l'LLM ritorna nomi simili agli existing, l'output deve essere
    deduplicato — restituisce solo nomi NON già in existing.

    Contract minimal P2.c: il deduplica è basato su match
    case-insensitive con _norm() (riusa logica P2.a Unicode-safe)
    sul nome canonical.
    """
    from engram.llm import MockLLM
    from engram.openie import extract_entities

    # LLM ritorna 3 entity: 1 nuova, 2 già esistenti (case-mixed)
    ner_json = json.dumps({
        "entities": [
            {"name": "Tonegawa", "type": "person"},  # già esistente
            {"name": "MIT", "type": "org"},           # già esistente
            {"name": "Hippocampus", "type": "concept"},  # nuova
        ],
    })
    mock = MockLLM(scripted=[ner_json])
    out = extract_entities(
        text="Tonegawa studies Hippocampus at MIT.",
        llm=mock,
        mode="ner_only",
        existing_entities=["tonegawa", "MIT"],  # case-insensitive
    )
    # Solo "Hippocampus" è nuova (le altre 2 deduplicate)
    new_names = {e["name"] for e in out["entities"]}
    assert "Hippocampus" in new_names
    assert "Tonegawa" not in new_names
    assert "MIT" not in new_names
    assert len(out["entities"]) == 1


def test_extract_entities_llm_failure_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RED: se LLM ritorna garbage non-JSON, extract_entities ritorna
    {entities: [], triples: []} senza crashare."""
    from engram.llm import MockLLM
    from engram.openie import extract_entities

    # 2 chiamate falliscono (retry incluso)
    mock = MockLLM(scripted=["garbage 1", "garbage 2"])
    out = extract_entities(
        text="X works at Y.", llm=mock, mode="ner_only",
    )
    assert out["entities"] == []
    assert out["triples"] == []


def test_extract_entities_llm_raises_exception_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RED round 2 — counterexample 0.78 P2.c: extract_entities deve
    catturare anche eccezioni da llm.complete() (timeout, HTTP error,
    rate limit, connection reset) e ritornare empty, non propagarle.

    Caso reale produzione: AnthropicLLM/OpenAICompatLLM possono
    sollevare RuntimeError/httpx errors. MockLLM non solleva, il
    bug è invisibile nei test originari.
    """
    from engram.openie import extract_entities

    class _NetFailLLM:
        def complete(self, system, messages, **kw):
            raise RuntimeError("connection reset")

    out = extract_entities(
        text="Tonegawa joined MIT.",
        llm=_NetFailLLM(),
        mode="ner_only",
    )
    assert out["entities"] == [], (
        "LLM exception must NOT propagate — extract_entities "
        "should return empty"
    )
    assert out["triples"] == []

    # Stesso per mode ner+triple
    out2 = extract_entities(
        text="Tonegawa joined MIT.",
        llm=_NetFailLLM(),
        mode="ner+triple",
    )
    assert out2["entities"] == []
    assert out2["triples"] == []


# ---------- MCP tool integration ----------------------------------


class _FakeAgent:
    def __init__(self, llm) -> None:
        self.openie_llm = llm  # convention: agent espone llm via attr
        # stub semantic per compat
        self.semantic = _NoopSemantic()
        self.entity_kg = None


class _NoopSemantic:
    def search_facts(self, *args, **kwargs):
        return []


@pytest.fixture
def fake_agent_with_mock_llm(
    monkeypatch: pytest.MonkeyPatch,
):
    from engram import mcp_server
    from engram.llm import MockLLM

    ner_json = json.dumps({
        "entities": [{"name": "X", "type": "t"}],
    })
    mock = MockLLM(scripted=[ner_json])
    a = _FakeAgent(llm=mock)
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a, mock


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


@pytest.mark.asyncio
async def test_hippo_extract_entities_tool_listed(
    fake_agent_with_mock_llm,
) -> None:
    """RED: tool hippo_extract_entities appare in tools/list."""
    from mcp.types import ListToolsRequest, PaginatedRequestParams

    from engram import mcp_server

    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(
        method="tools/list", params=PaginatedRequestParams(),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    assert "hippo_extract_entities" in names


@pytest.mark.asyncio
async def test_hippo_extract_entities_tool_dispatch(
    fake_agent_with_mock_llm,
) -> None:
    """RED: dispatch tool MCP ritorna {entities, triples}."""
    blocks = await _invoke_tool(
        "hippo_extract_entities",
        {"text": "Some text mentioning X.", "mode": "ner_only"},
    )
    payload = json.loads(blocks[0])
    assert "entities" in payload
    assert "triples" in payload
    # Mock scripted ritorna 1 entity "X"
    assert len(payload["entities"]) == 1
    assert payload["entities"][0]["name"] == "X"
