"""Multi-word keyword search (2026-06-13, Aurelio hit it live).

`hippo_facts_search "recall rerank circuit breaker"` returned [] even
though facts containing all those words exist: the direct search did a
single LIKE on the WHOLE phrase as a contiguous substring, which only
matches if that exact string appears verbatim. A user expects the words
ANDed, not the phrase matched literally.

Fix: search_facts gains require_all_tokens (AND across tokens); the
hippo_facts_search dispatcher uses AND-first then falls back to OR so a
multi-word query never returns [] when relevant facts exist.

RED marker: require_all_tokens kwarg must exist and AND the tokens.
"""
from __future__ import annotations

from verimem.semantic import Fact, SemanticMemory


def _seed(sm: SemanticMemory) -> None:
    props = [
        "the recall rerank uses a circuit breaker budget",   # all 4 tokens
        "the rerank stage scores candidate pairs",            # rerank only
        "a circuit breaker bounds the cold load",             # circuit+breaker
        "carbonara needs guanciale and pecorino",             # none
    ]
    for i, p in enumerate(props):
        sm.store(Fact(proposition=p, topic=f"t/{i}", source_episodes=["e"]),
                 embed="defer")


def _props(hits: list[Fact]) -> list[str]:
    return [f.proposition for f in hits]


# ── search_facts AND semantics ──────────────────────────────────────────────

def test_require_all_tokens_ands(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm)
    hits = sm.search_facts("recall rerank circuit breaker",
                           require_all_tokens=True)
    assert _props(hits) == ["the recall rerank uses a circuit breaker budget"], (
        "AND must return only the fact containing ALL four tokens"
    )


def test_phrase_substring_default_returns_empty(tmp_path):
    """The pre-fix default: the contiguous phrase is absent -> []."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm)
    hits = sm.search_facts("recall rerank circuit breaker")  # tokenize=False
    assert hits == [], "exact-phrase substring must not match (documents the bug)"


def test_require_all_single_token_is_substring(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm)
    hits = sm.search_facts("rerank", require_all_tokens=True)
    assert len(hits) == 2, "single token keeps substring behaviour"


def test_single_char_token_matches_usable_token(tmp_path):
    """Critic counterexample: a multi-word query with a 1-char token
    ("5 model", "c api") must match the surviving token, not the whole
    phrase substring (which would return [] — the original bug)."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="Opus 5 model wired into the api layer",
                  topic="t/x", source_episodes=["e"]), embed="defer")
    # phrase substring "%5 model%" is absent -> the pre-fix path returned [].
    assert sm.search_facts("5 model", require_all_tokens=True), (
        "AND with a dropped 1-char token must match the usable token 'model'"
    )
    assert sm.search_facts("5 model", tokenize=True), (
        "OR fallback must also match via the usable token"
    )
    assert sm.search_facts("c api", require_all_tokens=True), (
        "another 1-char-token query must match 'api'"
    )


def test_require_all_partial_match_excluded(tmp_path):
    """A fact with SOME but not all tokens must NOT match under AND."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm)
    hits = sm.search_facts("circuit breaker carbonara", require_all_tokens=True)
    assert hits == [], "no fact has all three tokens -> AND yields []"


# ── dispatcher: AND-first, OR-fallback (never spurious []) ───────────────────

import pytest  # noqa: E402


@pytest.mark.asyncio
async def test_tool_and_first_or_fallback(tmp_path, monkeypatch):
    """hippo_facts_search must return relevant hits for a multi-word query
    even when no single fact has ALL tokens (OR fallback), instead of []."""
    import verimem.mcp_server as ms

    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm)

    class _Ag:
        def __init__(self, semantic):
            self.semantic = semantic

    monkeypatch.setattr(ms, "_ag", lambda: _Ag(sm))

    from mcp.types import CallToolRequest, CallToolRequestParams
    # "recall carbonara" — no fact has BOTH; AND yields [], OR must rescue.
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(
            name="hippo_facts_search",
            arguments={"query": "recall carbonara", "limit": 5},
        ),
    )
    handlers = ms.server.request_handlers
    result = await handlers[CallToolRequest](req)
    payload = result.root if hasattr(result, "root") else result
    import json
    parsed = json.loads(payload.content[0].text)
    props = " ".join(f["proposition"] for f in parsed["items"])
    assert parsed["items"], "multi-word query must not return [] when ANY token matches"
    assert "recall" in props or "carbonara" in props
