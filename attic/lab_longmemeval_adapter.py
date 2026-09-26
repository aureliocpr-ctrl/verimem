"""Cycle 178 (2026-05-22) — LongMemEval adapter SKELETON.

Closes task #59 partially: scaffolding + contract. Real dataset fetch
+ LLM-judge harness deferred to cycle 178.1.

Reference: ``LongMemEval: Benchmarking Chat Assistants on Long-Term
Interactive Memory`` -- arXiv 2410.10813. Five core abilities measured:
information extraction, multi-session reasoning, temporal reasoning,
knowledge updates, abstention. Memory units in spec: session / round
/ compressive-summary / fact.

HippoAgent natural mapping (this adapter assumes it):
  * LongMemEval session -> HippoAgent episode
  * LongMemEval round   -> message turn inside episode metadata
  * LongMemEval fact    -> HippoAgent fact (semantic memory)

Subscription-only (CLAUDE.md O4): the adapter is intentionally thin
and *injection-only*. ``ingester`` and ``recall_callable`` are passed
in by the caller. In production wire them to
``hippo_record_episode`` / ``hippo_recall`` (host subscription).
Tests inject mocks. NO ``anthropic.Anthropic`` / ``openai.OpenAI``
clients here -- not the adapter's job.

Failure-mode contract
---------------------
Both methods are *defensive*: any per-row failure is counted but
never aborts the loop or raises out.

  * ``adapt_sessions``: ingester raise -> errors+=1, loop continues.
    Malformed (non-dict) session -> skipped+=1.
  * ``evaluate_query``: recall_callable raise -> ``{"match": False,
    "recalled": []}``; non-list recall output coerced to ``[]``.

Lexical-only match (skeleton)
-----------------------------
The default match is a *substring*, case-insensitive comparison
between ``expected_answer`` and the concatenated recall list. This
is intentionally cheap so the skeleton runs without any LLM at all
-- the LLM-judge variant is the cycle 178.1 follow-up.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

_EMPTY_SUMMARY: dict[str, int] = {"ingested": 0, "skipped": 0, "errors": 0}


class LongMemEvalAdapter:
    """Skeleton adapter from LongMemEval format to HippoAgent.

    See module docstring for the contract + mapping rationale.
    """

    def adapt_sessions(
        self,
        sessions: list[dict[str, Any]],
        *,
        ingester: Callable[[dict[str, Any]], Any],
    ) -> dict[str, int]:
        """Walk LongMemEval session dicts and dispatch to ``ingester``.

        Args:
            sessions: list of ``{"session_id": str, "turns": [...]}``
                dicts (LongMemEval shape).
            ingester: ``(session_dict) -> Any`` injected callable. Any
                exception is caught and bucketed in ``errors``; the
                loop continues to the next session.

        Returns:
            Summary dict with keys ``ingested``, ``skipped``,
            ``errors`` -- all integer counts.
        """
        summary = dict(_EMPTY_SUMMARY)
        for session in sessions:
            if not isinstance(session, dict):
                summary["skipped"] += 1
                continue
            try:
                ingester(session)
                summary["ingested"] += 1
            except Exception:
                summary["errors"] += 1
        return summary

    def evaluate_query(
        self,
        query: dict[str, Any],
        *,
        recall_callable: Callable[[str], list[str]],
    ) -> dict[str, Any]:
        """Run one LongMemEval query through ``recall_callable`` and
        compute a lexical match against ``expected_answer``.

        Args:
            query: ``{"q": str, "expected_answer": str}`` shape.
            recall_callable: ``(q: str) -> list[str]`` injected. Any
                exception caught and converted to ``match=False``.

        Returns:
            ``{"match": bool, "recalled": list[str]}``. Lexical
            (substring, case-insensitive) match between
            ``expected_answer`` and the joined recall corpus.
        """
        q = (query or {}).get("q", "") if isinstance(query, dict) else ""
        expected = (
            (query or {}).get("expected_answer", "")
            if isinstance(query, dict)
            else ""
        )
        try:
            recalled = recall_callable(q)
            if not isinstance(recalled, list):
                recalled = []
        except Exception:
            return {"match": False, "recalled": []}
        expected_lower = (expected or "").strip().lower()
        if not expected_lower:
            return {"match": False, "recalled": recalled}
        match = any(
            isinstance(r, str) and expected_lower in r.lower()
            for r in recalled
        )
        return {"match": match, "recalled": recalled}


__all__ = ["LongMemEvalAdapter"]
