"""Cycle 178 (2026-05-22) — LongMemEval adapter SKELETON tests.

Closes task #59 partially: adapter scaffolding + contract tests.
Real-dataset fetch + LLM-evaluation harness deferred to cycle 178.1.

LongMemEval paper: arxiv 2410.10813. 5 core abilities measured:
  * information extraction
  * multi-session reasoning
  * temporal reasoning
  * knowledge updates
  * abstention

Memory units in the spec: session / round / compressive-summary / fact.
HippoAgent natural mapping: session -> episode; round -> message turn
inside episode metadata; fact -> fact.

Adapter contract (skeleton)
---------------------------
``LongMemEvalAdapter`` has two methods:

  * ``adapt_sessions(sessions, ingester) -> dict``: ingest a list of
    LongMemEval-shaped session dicts (``{"session_id", "turns": [...]}``)
    into HippoAgent via an *injected* ingester callable (so tests can
    pass a stub; production wires it to ``hippo_record_episode``).
    Returns ``{"ingested": int, "skipped": int, "errors": int}``.

  * ``evaluate_query(query, recall_callable) -> dict``: given one
    LongMemEval query (``{"q": str, "expected_answer": str}``), call
    the *injected* recall callable, compute a basic match metric,
    return ``{"match": bool, "recalled": list[str]}``. Lexical match
    only (skeleton); LLM-judge deferred to 178.1.

Subscription-only (CLAUDE.md O4): all LLM-dependent work goes through
injected callables, never an ``anthropic.Anthropic`` client.

RED marker: import must fail on master.
"""
from __future__ import annotations

from unittest.mock import MagicMock

# RED MARKER
from engram.lab_longmemeval_adapter import LongMemEvalAdapter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_SAMPLE_SESSIONS = [
    {
        "session_id": "sess-001",
        "turns": [
            {"role": "user", "content": "My birthday is March 5th."},
            {"role": "assistant", "content": "Got it, March 5."},
        ],
    },
    {
        "session_id": "sess-002",
        "turns": [
            {"role": "user", "content": "Move my birthday to March 7th."},
            {"role": "assistant", "content": "Updated to March 7."},
        ],
    },
]


_SAMPLE_QUERY = {
    "q": "When is my birthday?",
    "expected_answer": "March 7",
}


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------


class TestLongMemEvalAdapter:
    def test_adapter_instantiable(self) -> None:
        a = LongMemEvalAdapter()
        assert a is not None

    def test_adapt_sessions_returns_summary(self) -> None:
        a = LongMemEvalAdapter()
        ingester = MagicMock(return_value=None)
        out = a.adapt_sessions(_SAMPLE_SESSIONS, ingester=ingester)
        assert isinstance(out, dict)
        for k in ("ingested", "skipped", "errors"):
            assert k in out

    def test_adapt_sessions_calls_ingester_per_session(self) -> None:
        """One ingester call per session in the input list."""
        a = LongMemEvalAdapter()
        ingester = MagicMock(return_value=None)
        a.adapt_sessions(_SAMPLE_SESSIONS, ingester=ingester)
        assert ingester.call_count == 2

    def test_adapt_sessions_ingester_failure_counted(self) -> None:
        """Ingester raising on one session must NOT abort the batch."""
        a = LongMemEvalAdapter()
        call_count = [0]

        def flaky(session: dict) -> None:
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("transient")

        out = a.adapt_sessions(_SAMPLE_SESSIONS, ingester=flaky)
        assert out["errors"] == 1
        assert out["ingested"] == 1
        assert call_count[0] == 2

    def test_adapt_sessions_empty_list_is_noop(self) -> None:
        a = LongMemEvalAdapter()
        ingester = MagicMock(return_value=None)
        out = a.adapt_sessions([], ingester=ingester)
        assert out == {"ingested": 0, "skipped": 0, "errors": 0}
        assert ingester.call_count == 0

    def test_evaluate_query_lexical_match_true(self) -> None:
        """Lexical match: recalled text contains expected_answer
        substring → match True."""
        a = LongMemEvalAdapter()
        recall = MagicMock(return_value=[
            "User's birthday was updated to March 7 in session sess-002.",
        ])
        out = a.evaluate_query(_SAMPLE_QUERY, recall_callable=recall)
        assert isinstance(out, dict)
        assert out["match"] is True

    def test_evaluate_query_lexical_match_false(self) -> None:
        """Lexical match: recalled text does NOT contain expected_answer
        → match False."""
        a = LongMemEvalAdapter()
        recall = MagicMock(return_value=[
            "Unrelated content about something else entirely.",
        ])
        out = a.evaluate_query(_SAMPLE_QUERY, recall_callable=recall)
        assert out["match"] is False

    def test_evaluate_query_case_insensitive_match(self) -> None:
        """``MARCH 7`` should still match ``March 7`` (lexical
        case-insensitive)."""
        a = LongMemEvalAdapter()
        recall = MagicMock(return_value=[
            "Updated to MARCH 7 according to session sess-002.",
        ])
        out = a.evaluate_query(_SAMPLE_QUERY, recall_callable=recall)
        assert out["match"] is True

    def test_evaluate_query_recall_failure_returns_no_match(self) -> None:
        """Recall callable raises → match False, exception swallowed."""
        a = LongMemEvalAdapter()
        recall = MagicMock(side_effect=RuntimeError("recall down"))
        out = a.evaluate_query(_SAMPLE_QUERY, recall_callable=recall)
        assert out["match"] is False
        assert out["recalled"] == []
