"""P1 — RED test per `hippo_validate_claim` (anti-confabulazione).

Spec: docs/specs/p1-hippo-validate-claim.md (commit ce67839).

Tool MCP che, data una claim verificabile, restituisce verdict +
evidenza cercata in memoria (facts). Pensato per essere chiamato PRIMA
che Claude affermi un fatto, riducendo confabulazione.

API:
    hippo_validate_claim(claim: str,
                         topic_hint: str | None = None,
                         threshold: float = 0.6)
        → {verdict, confidence, evidence_facts, evidence_episodes, advice}

verdict ∈ {"supported", "contradicted", "unknown"}.

Meccanica deterministic (zero LLM call):
  1. Semantic search su facts (riusa `semantic.search_facts`).
  2. NER super-light: estrai nomi Capitalized + anni dalla claim.
  3. Contradiction = stesso soggetto+predicato (token-set match
     robusto) MA oggetto diverso (anno/numero/entità diverso).
     Match positivo robust ⇒ supported. Altrimenti unknown.

Origin: pattern di confabulazione pescati LIVE in sessione 2026-05-14
(Tonegawa Nobel 1987→2014, Anthropic Skills 2025→2026, LightRAG
HKUDS→HKUST). Test usa Tonegawa come canary case.
"""
from __future__ import annotations

import json
import time
from typing import Any

import pytest

from engram import mcp_server

# ---------- Fakes --------------------------------------------------------


class _FakeFact:
    """Mirror della shape `engram.semantic.Fact` per i test."""

    def __init__(
        self,
        fid: str,
        *,
        proposition: str,
        topic: str = "",
        confidence: float = 0.9,
        source_episodes: list[str] | None = None,
        created_at: float | None = None,
    ) -> None:
        self.id = fid
        self.proposition = proposition
        self.topic = topic
        self.confidence = confidence
        self.source_episodes = list(source_episodes or [])
        self.created_at = created_at if created_at is not None else time.time()


class _FakeSemantic:
    """Stub minimale del SemanticMemory con search_facts."""

    def __init__(self, facts: list[_FakeFact]) -> None:
        self._facts = {f.id: f for f in facts}

    def search_facts(
        self,
        query: str,
        *,
        limit: int = 20,
        topic: str | None = None,
    ) -> list[_FakeFact]:
        """Production-faithful: SQL LIKE su intera query (case-insensitive).

        Replica esattamente ``engram.semantic.SemanticMemory.search_facts``
        (engram/semantic.py:225-252):
            LOWER(proposition) LIKE '%<query.lower()>%'

        NON token-overlap. Il critic-orchestrator counterexample worker
        ha mostrato che un fake "token-overlap" è troppo generoso e
        nasconde il bug reale: in produzione la claim INTERA non è
        sottostringa di un fact corretto (es. "...Nobel Prize in 2014."
        non appare nel fact "...Nobel Prize in...1987..."). Questo fake
        è strict per forzare ``validate_claim`` a tokenizzare la claim
        prima di interrogare il backend.
        """
        ql = (query or "").strip().lower()
        out: list[_FakeFact] = []
        for f in self._facts.values():
            if topic and f.topic != topic:
                continue
            if ql and ql not in f.proposition.lower():
                continue
            out.append(f)
        out.sort(key=lambda f: f.created_at, reverse=True)
        return out[:limit]


class _FakeAgent:
    def __init__(self, facts: list[_FakeFact]) -> None:
        self.semantic = _FakeSemantic(facts)


# ---------- Fixtures -----------------------------------------------------


def _tonegawa_corpus() -> list[_FakeFact]:
    """Corpus canary: fatto VERO su Tonegawa Nobel 1987 immunologia."""
    return [
        _FakeFact(
            "f_tonegawa_1987",
            proposition=(
                "Susumu Tonegawa won the Nobel Prize in Physiology or "
                "Medicine in 1987 for his work on antibody diversity "
                "(V(D)J recombination, immunology)."
            ),
            topic="science/biology/nobel",
            confidence=0.95,
            source_episodes=["ep_research_2026_05_14"],
            created_at=1000.0,
        ),
        _FakeFact(
            "f_newton_1687",
            proposition=(
                "Isaac Newton published Principia Mathematica in 1687."
            ),
            topic="science/physics",
            confidence=0.99,
            created_at=900.0,
        ),
    ]


@pytest.fixture
def fake_agent_tonegawa(monkeypatch: pytest.MonkeyPatch) -> _FakeAgent:
    a = _FakeAgent(_tonegawa_corpus())
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a


@pytest.fixture
def fake_agent_empty(monkeypatch: pytest.MonkeyPatch) -> _FakeAgent:
    a = _FakeAgent([])
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a


# ---------- Helpers ------------------------------------------------------


async def _invoke_tool(
    name: str, arguments: dict[str, Any] | None = None,
) -> list[str]:
    from mcp.types import CallToolRequest, CallToolRequestParams

    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    return [c.text for c in payload.content if hasattr(c, "text")]


# ---------- Listing -----------------------------------------------------


@pytest.mark.asyncio
async def test_validate_claim_tool_listed(
    fake_agent_tonegawa: _FakeAgent,
) -> None:
    """RED: il tool deve apparire nella lista MCP."""
    from mcp.types import ListToolsRequest, PaginatedRequestParams

    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(
        method="tools/list", params=PaginatedRequestParams(),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    assert "hippo_validate_claim" in names, (
        "tool hippo_validate_claim non registrato in mcp_server"
    )


# ---------- Verdict: CONTRADICTED ---------------------------------------


@pytest.mark.asyncio
async def test_contradicted_tonegawa_year(
    fake_agent_tonegawa: _FakeAgent,
) -> None:
    """RED canary: claim Tonegawa Nobel 2014 contraddetta da fact 1987.

    Stesso soggetto (Tonegawa) + stesso predicato (won Nobel Prize) +
    oggetto-anno diverso (1987 vs 2014) ⇒ verdict=contradicted.
    Evidence deve includere il fact che contraddice.
    """
    blocks = await _invoke_tool(
        "hippo_validate_claim",
        {"claim": "Susumu Tonegawa won the Nobel Prize in 2014."},
    )
    assert blocks, "tool ha restituito payload vuoto"
    payload = json.loads(blocks[0])
    assert payload["verdict"] == "contradicted", (
        f"atteso 'contradicted', ottenuto {payload.get('verdict')!r}"
    )
    assert "f_tonegawa_1987" in payload["evidence_facts"], (
        "il fact 1987 deve apparire come evidenza"
    )
    assert payload["advice"], "advice non deve essere stringa vuota"


# ---------- Verdict: SUPPORTED ------------------------------------------


@pytest.mark.asyncio
async def test_supported_tonegawa_year(
    fake_agent_tonegawa: _FakeAgent,
) -> None:
    """RED: claim Tonegawa Nobel 1987 è supportata dal fact in memoria."""
    blocks = await _invoke_tool(
        "hippo_validate_claim",
        {"claim": "Susumu Tonegawa won the Nobel Prize in 1987."},
    )
    payload = json.loads(blocks[0])
    assert payload["verdict"] == "supported"
    assert "f_tonegawa_1987" in payload["evidence_facts"]
    assert payload["confidence"] >= 0.6


# ---------- Verdict: UNKNOWN --------------------------------------------


@pytest.mark.asyncio
async def test_unknown_when_corpus_empty(
    fake_agent_empty: _FakeAgent,
) -> None:
    """RED: corpus vuoto ⇒ verdict='unknown', evidence vuota."""
    blocks = await _invoke_tool(
        "hippo_validate_claim",
        {"claim": "Susumu Tonegawa won the Nobel Prize in 1987."},
    )
    payload = json.loads(blocks[0])
    assert payload["verdict"] == "unknown"
    assert payload["evidence_facts"] == []


@pytest.mark.asyncio
async def test_unknown_when_offtopic(
    fake_agent_tonegawa: _FakeAgent,
) -> None:
    """RED: claim su entità non presente in corpus ⇒ unknown.

    Corpus parla di Tonegawa+Newton. Claim su Marie Curie → nessuna
    evidenza significativa → unknown.
    """
    blocks = await _invoke_tool(
        "hippo_validate_claim",
        {"claim": "Marie Curie discovered polonium in 1898."},
    )
    payload = json.loads(blocks[0])
    assert payload["verdict"] == "unknown"


# ---------- Threshold parameter -----------------------------------------


@pytest.mark.asyncio
async def test_threshold_respected(
    fake_agent_tonegawa: _FakeAgent,
) -> None:
    """RED: threshold molto alto su claim borderline ⇒ unknown
    (anche se c'è evidenza debole), per evitare falsi positivi."""
    blocks = await _invoke_tool(
        "hippo_validate_claim",
        {
            "claim": "Tonegawa is a researcher.",  # vero ma molto generico
            "threshold": 0.99,
        },
    )
    payload = json.loads(blocks[0])
    # Sopra threshold 0.99, una claim così generica non deve essere
    # promossa a 'supported' — meglio unknown che falso supported.
    assert payload["verdict"] in ("unknown", "contradicted")


# ---------- Output schema -----------------------------------------------


@pytest.mark.asyncio
async def test_output_schema_keys(fake_agent_tonegawa: _FakeAgent) -> None:
    """RED: payload deve avere le 5 chiavi promesse dalla spec."""
    blocks = await _invoke_tool(
        "hippo_validate_claim",
        {"claim": "Susumu Tonegawa won the Nobel Prize in 1987."},
    )
    payload = json.loads(blocks[0])
    for key in (
        "verdict", "confidence", "evidence_facts",
        "evidence_episodes", "advice",
    ):
        assert key in payload, f"chiave '{key}' mancante nel payload"
    assert isinstance(payload["evidence_facts"], list)
    assert isinstance(payload["evidence_episodes"], list)
    assert isinstance(payload["advice"], str)


# ---------- Topic hint --------------------------------------------------


@pytest.mark.asyncio
async def test_topic_hint_narrows_search(
    fake_agent_tonegawa: _FakeAgent,
) -> None:
    """RED: topic_hint deve filtrare i fact su quel topic."""
    blocks = await _invoke_tool(
        "hippo_validate_claim",
        {
            "claim": "Susumu Tonegawa won the Nobel Prize in 1987.",
            "topic_hint": "science/biology/nobel",
        },
    )
    payload = json.loads(blocks[0])
    assert payload["verdict"] == "supported"
    # Il fact deve essere quello del topic giusto.
    assert "f_tonegawa_1987" in payload["evidence_facts"]


# ---------- NUMERIC-QUANTITY contradiction (subtle confab USP gap) -------
#
# The original spec (docstring riga 20) promised contradiction on
# "oggetto diverso (anno/NUMERO/entità)" but the implementation only
# shipped the YEAR branch. These RED tests cover the NUMBER branch:
# a new claim that states a DIFFERENT quantity (same unit) for the same
# subject as an existing fact must be `contradicted`, NOT silently
# persisted. This is the subtle-confab the keyword L1 detectors miss
# (no hype trigger words). Falsified empirically 0/5 before this fix.
# Hermetic: direct sync call, fake semantic (SQL-LIKE) — no embedding.

from engram.validate_claim import validate_claim as _vc  # noqa: E402


def _numeric_corpus() -> list[_FakeFact]:
    """True facts with quantities a subtle confab could silently override."""
    return [
        _FakeFact(
            "f_sess_ttl",
            proposition=(
                "Sessions are keyed by a UUID stored in the session "
                "table with a TTL of 30 minutes."
            ),
            topic="eng/session",
            created_at=1000.0,
        ),
        _FakeFact(
            "f_cache_lru",
            proposition=(
                "The cache evicts entries with an LRU policy bounded "
                "at 1024 entries."
            ),
            topic="eng/cache",
            created_at=1001.0,
        ),
        _FakeFact(
            "f_retry_backoff",
            proposition=(
                "Network calls retry up to 3 times with exponential "
                "backoff starting at 200ms."
            ),
            topic="eng/net",
            created_at=1002.0,
        ),
        _FakeFact(
            "f_backup_rotation",
            proposition=(
                "Backups run nightly via sqlite VACUUM INTO with a "
                "7-snapshot rotation."
            ),
            topic="eng/backup",
            created_at=1003.0,
        ),
    ]


def test_numeric_contradicted_minutes() -> None:
    """RED: 'sessions expire after 45 minutes' contradicts stored 30 minutes."""
    agent = _FakeAgent(_numeric_corpus())
    r = _vc(agent, "Sessions expire after 45 minutes of inactivity by default.")
    assert r["verdict"] == "contradicted", r
    assert "f_sess_ttl" in r["evidence_facts"], r
    assert r["advice"]


def test_numeric_contradicted_entries() -> None:
    """RED: '4096 entry ceiling' contradicts stored '1024 entries'."""
    agent = _FakeAgent(_numeric_corpus())
    r = _vc(agent, "The cache uses a least-recently-used policy with a 4096 entry ceiling.")
    assert r["verdict"] == "contradicted", r
    assert "f_cache_lru" in r["evidence_facts"], r


def test_numeric_contradicted_milliseconds() -> None:
    """RED: '500 milliseconds' contradicts stored '200ms' (unit normalize)."""
    agent = _FakeAgent(_numeric_corpus())
    r = _vc(agent, "The retry backoff doubles starting from 500 milliseconds.")
    assert r["verdict"] == "contradicted", r
    assert "f_retry_backoff" in r["evidence_facts"], r


def test_numeric_agreement_not_contradicted() -> None:
    """No false positive: SAME quantity must NOT be flagged contradicted."""
    agent = _FakeAgent(_numeric_corpus())
    r = _vc(agent, "Sessions expire after 30 minutes of inactivity.")
    assert r["verdict"] != "contradicted", r


def test_numeric_no_fp_same_unit_different_subject() -> None:
    """Precision guard: same unit + different value but UNRELATED subject
    (no shared distinctive content token) must NOT contradict.

    'buffer 256 entries' vs corpus 'cache 1024 entries': both use the unit
    'entry', values differ, and the cache fact IS retrieved by the shared
    word 'entries' — but the only overlap is the unit word itself, so the
    numeric detector must hold (else it would block legitimate new facts)."""
    agent = _FakeAgent(_numeric_corpus())
    r = _vc(agent, "The ring buffer holds at most 256 entries.")
    assert r["verdict"] != "contradicted", r


def test_numeric_no_fp_contrasting_qualifier() -> None:
    """Precision guard: same measured noun + same unit + different value but a
    CONTRASTING qualifier ('read' vs 'write') = DIFFERENT attribute → must NOT
    contradict. A false contradiction here would downgrade a legitimate fact."""
    agent = _FakeAgent([
        _FakeFact("f_write_to", proposition="The write timeout is 10 seconds."),
    ])
    r = _vc(agent, "The read timeout is 30 seconds.")
    assert r["verdict"] != "contradicted", r


def test_numeric_unconfirmed_quantity_not_falsely_supported() -> None:
    """Honest boundary: when a unit can't be aligned (here '14 daily
    snapshots' vs stored '7-snapshot rotation'), the claim must NOT be
    promoted to 'supported' on the shared subject 'Backups' alone — that
    would be false reassurance for an unverified number. Expect 'unknown'."""
    agent = _FakeAgent(_numeric_corpus())
    r = _vc(agent, "Backups are kept for 14 daily snapshots before rotation.")
    assert r["verdict"] == "unknown", r
    # The related subject IS surfaced as (weak) evidence for the human.
    assert "f_backup_rotation" in r["evidence_facts"], r


def test_numeric_year_not_treated_as_quantity() -> None:
    """A 4-digit year must stay in the YEAR path, not the numeric path —
    so a claim with only a year + one name keeps its existing behaviour."""
    agent = _FakeAgent(_numeric_corpus())
    # No quantity, no related fact -> unknown (unchanged behaviour).
    r = _vc(agent, "The release shipped in 2024.")
    assert r["verdict"] == "unknown", r
